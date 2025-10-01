import numpy as np
import pandas as pd
from enum import Enum
import ressource as ress
import tensorflow as tf
import pickle
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
import random

RULES = Enum("RULES", ["LQE", "MQE", "STPT", "LTPT", "STST", "LTST", "STG", "LTG", "QPT", "LPT", "QST", "LST", "QG", "LG"])
DNN,RF,GBC,BG = 0,1,2,3
PREFIX_MODELS_DIR = "models/models_cell"
PREFIX_SCALERS_DIR = "scalers/scaler_cell"



def dispatching_rule(cell, rule): #redo after adding params, has to be uniform with other allocation methods
    """
    supported rules : 
        LQE : Less Queued Elements
        MQE : Most Queued Elements
        STPT : shortest total process time
        LTPT : longuest total process time
        STST : shortest total setup time
        LTST : longuest total setup time
        STG : shortest total gross
        LTG : longuest total gross
        QPT : quickest process time
        LPT : longuest process time 
        QST : quickest setup time
        LST : longuest setup time
        QG : quickest gross
        LG : longuest gross 
    """
    if   rule == RULES.LQE :
        return np.argmin([len(cell.ressources[i].q) for i in range(len(cell.ressources))])
    elif rule == RULES.MQE :
        return np.argmax([len(cell.ressources[i].q) for i in range(len(cell.ressources))])
    elif rule == RULES.STPT :
        return np.argmin(np.array([sum([cell.ressources[i].processTimes[prod.famille-1] for prod in cell.ressources[i].q]) for i in range(len(cell.ressources))])+\
                         [r.current_operation_time_left if r.current_state==ress.ACTIVE_PROCESS else\
                          r.processTimes[r.current_job.famille-1] if r.current_state==ress.ACTIVE_SETUP else 0 for r in cell.ressources])
    elif rule == RULES.LTPT :
        return np.argmax(np.array([sum([cell.ressources[i].processTimes[prod.famille-1] for prod in cell.ressources[i].q]) for i in range(len(cell.ressources))])+\
                         [r.current_operation_time_left if r.current_state==ress.ACTIVE_PROCESS else\
                          r.processTimes[r.current_job.famille-1] if r.current_state==ress.ACTIVE_SETUP else 0 for r in cell.ressources])
    elif rule == RULES.STST :   
        for i in range(len(cell.ressources)):
            cell.ressources[i].q

def random_full(scenario, system):
    #returns a full solution for all the problem not only the current product's allocation
    # form of a solution, actually dict[prod_id][cell_number] = allocation of the product prod_id in the cell cell_number 
    solution = {}
    for line in scenario.sort_values(by=scenario.columns[0]).to_numpy():
        solution[line[0]] = {}
        c = 0
        for cell in system.cellules:
            solution[line[0]][c] = np.random.randint(len(cell.ressources))
            c+=1
    return solution

def set_prefix_models(prefix_models_path):
    global PREFIX_MODELS_DIR 
    PREFIX_MODELS_DIR = prefix_models_path

def set_prefix_scalers(prefix_scalers_path):
    global PREFIX_SCALERS_DIR
    PREFIX_SCALERS_DIR = prefix_scalers_path

def load_model(cell:int, model:int):
    """
        cell : int {1,2,3}
        model : int {DNN,RF,GBC,BG = 0,1,2,3}
        loads a model of type model corresponding to the cell cell and returns it
    """
    prefix = PREFIX_MODELS_DIR+f"{cell}/"
    if model == DNN:
        return tf.keras.models.load_model(prefix+"Dense_with_gauss.keras")
    elif model == RF:
        with open(prefix+'RandomForest.pkl', 'rb') as f:
            return pickle.load(f)
    elif model == BG:
        with open(prefix+'BaggingClassifier.pkl', 'rb') as f:
            return pickle.load(f)
    elif model == GBC:
        with open(prefix+'GradientBoostingClassifier.pkl', 'rb') as f:
            return pickle.load(f)
    else:
        print("error, no model specified")

def load_scaler(cell:int, path:str = None) -> StandardScaler : 
    """
        returns the inputs scaler for the specified cell
    """
    if path is None :
        p = PREFIX_SCALERS_DIR+f'{cell}.pkl'
    else :
        p = path
    with open(p, 'rb') as f:
        return pickle.load(f)

def chunk_data(data:pd.DataFrame, ordre_cellule:int, cols_to_keep:list) -> pd.DataFrame:
    """
        data : a vector of features concerning all the cells
        cell : an integer corresponding to a specific cell

        returns the vector of features in data that corresponds to the specified cell
    """
    
    cols = [col for col in data.columns if col.startswith(x) for x in cols_to_keep]    
    return data[cols]

def predict(cell:int, model_type:int, data:pd.DataFrame):
    """
        cell : int {1,2,3}
        model : int {DNN,RF,GBC,BG = 0,1,2,3}
        data : a vector of features concerning all the cells
    """
    scaler = load_scaler(cell)
    df = scaler.transform(chunk_data(data, cell))
    mdl = load_model(cell, model_type)
    if model_type == GBC and np.isnan(df).any() : # GBC does not accept Nan values, replace them with 0
        df = np.nan_to_num(df, nan=0)
    return mdl.predict(df)



class Allocator:
    def __init__(self, system):
        self.system = system

    def allocate(self, produit, ordre_cellule):
        raise NotImplementedError("This method should be overridden by subclasses")

class RandomAllocator(Allocator):
    def __init__(self, system):
        """
        :param solution: Dictionnaire ou DataFrame représentant la solution statique
                         clé: ID du produit
                         valeur: Dictionnaire avec l'ordre des cellules comme clé et l'indice de la ressource comme valeur
        """
        super().__init__(system)

    def allocate(self, produit, ordre_cellule, _):
        """
        Alloue la ressource en fonction de la solution statique.
        id produit commence a 1
        ordre cellule commence a 0
        soustraction du surplus des ressources en trop dans les cell precedentes et - 1 car commence par 0
        """
        nb_ress = len(self.system.cellules[ordre_cellule].ressources)
        return [random.randint(0, nb_ress-1)]

class StaticAllocator(Allocator):
    def __init__(self, system, solution, use_scaler=True):
        """
        :param solution: Dictionnaire ou DataFrame représentant la solution statique
                         clé: ID du produit
                         valeur: Dictionnaire avec l'ordre des cellules comme clé et l'indice de la ressource comme valeur
        """
        super().__init__(system)
        self.solution = solution

    def allocate(self, produit, ordre_cellule, _):
        """
        Alloue la ressource en fonction de la solution statique.
        id produit commence a 1
        ordre cellule commence a 0
        soustraction du surplus des ressources en trop dans les cell precedentes et - 1 car commence par 0
        """
        resource_index = self.solution.iloc[produit.id-1,ordre_cellule]
        offset = sum([len(self.system.cellules[c].ressources) for c in range(ordre_cellule)]) +1
        return [resource_index - offset]

class DynamicAllocator(Allocator):
    def __init__(self, system, model=None, scaler=None, keep_cols=None, replace_nan_with_0=True, to_categorical=False, singlelabel=False):
        """
        :param system: objet systeme
        :param model: Modèle TensorFlow ou autre méthode d'allocation dynamique
        :param scaler: Scaler tensorflow
        :param replace_nan_with_0: pour certains modeles il faut remplacer les nan par 0 sinon il y aura des erreurs d'execution comme le GBC
        """
        super().__init__(system)
        if type(model) is list:
            self.per_family = True
        else :
            self.per_family = False
        self.model = model
        self.cols_to_keep = keep_cols
        self.scaler = scaler
        self.to_categorical = to_categorical
        self.replace_nan = replace_nan_with_0
        self.ordered_by_cc = system.labels_encoded
        self.singlelabel = singlelabel
        
        self.preprocessor = Preprocessor(self.chunk_data, self.scaler, self.replace_nan)

    def allocate(self, produit, ordre_cellule, features):
        #if type(self.model) is PerFamilySingleLabel or type(self.model) is PerFamilyMultiLabel or type(self.model) is GlobalMultiLabel or type(self.model) is GlobalSingleLabel:
            return self.new_allocate(produit, ordre_cellule, features)
        #else :
        #    return self.old_allocate(produit, ordre_cellule, features)

    def old_allocate(self, produit, ordre_cellule, features):
        """
        Alloue la ressource de manière dynamique en utilisant un modèle, en cas d'echec retourne -1
        """
        if self.model:
            data = self.chunk_data(features,ordre_cellule)
            if self.scaler is not None:
                data = pd.DataFrame(self.scaler.transform(data), columns=data.columns, index=data.index)
            if self.replace_nan :
                data.fillna(0, inplace=True)
            # prediction
            if isinstance(self.model, tf.keras.Model):
                resource_index = self.model.predict(data, verbose=0)
            elif (type(self.model) == RandomForestClassifier):
                if self.singlelabel:
                    # singlelabel
                    probas = self.model.predict_proba(data)[0]
                else : # multilaabel
                    probas = [proba[0][1] for proba in self.model.predict_proba(data)]
                ordered_choices = np.argsort(probas)[::-1]
                if self.ordered_by_cc : # si oui alors le retour des modeles est ordonné par current charge
                    ordered_ressources = self.system.cellules[ordre_cellule].ordered_ressources_cc()
                    return [ordered_ressources[i] for i in ordered_choices] # on doit donc les mapper avec les noms des ressources
                return ordered_choices # sinon on retourne directement les choix du modele
            elif self.per_family :
                # on doit choisir le modele qui fait la prediction
                model =self.model[produit.famille-1]
                if self.singlelabel:
                    # singlelabel
                    probas = model.predict_proba(data)[0]
                else : # multilaabel
                    probas = [proba[0][1] for proba in model.predict_proba(data)]
                ordered_choices = np.argsort(probas)[::-1]
                if self.ordered_by_cc : # si oui alors le retour des modeles est ordonné par current charge
                    ordered_ressources = self.system.cellules[ordre_cellule].ordered_ressources_cc()
                    return [ordered_ressources[i] for i in ordered_choices] # on doit donc les mapper avec les noms des ressources
                return ordered_choices
            else :
                resource_index = self.model.predict(data)
            
            if len(resource_index.shape)>1:
                return np.argmax(resource_index, axis=1)[0]
            else :
                return resource_index[0]
        else:
            print("fail, modele introuvable : self.model = ",self.model)
            return -1
        
    def new_allocate(self, produit, ordre_cellule, features):
        """
        Alloue la ressource de manière dynamique en utilisant un modèle, en cas d'echec retourne -1
        """
        data = self.preprocessor.transform(features, ordre_cellule)
        return self.model.allocate(produit, ordre_cellule, data)

        
    def chunk_data(self, data:pd.DataFrame, ordre_cellule:int) -> pd.DataFrame:
        """
            data : a vector of features concerning all the cells
            ordre_cellule : int order of cell in system

            returns the vector of trunked features in data
        """
        cols = self.cols_to_keep if self.cols_to_keep else data.columns   

        if self.to_categorical:
            categorical_cols = [col for col in data.columns if col.startswith("Family")] 

            # Process `Curn_Fam` columns
            curn_fam_cols = [col for col in categorical_cols if col.startswith("Family")]
            for col in curn_fam_cols:
                # Create columns from `1` to `self.nb_familles` (no `0`)
                for i in range(1, self.system.nb_familles + 1):
                    dummy_column_name = f"{col}_{i}"
                    data[dummy_column_name] = 0
                # Set the relevant dummy column to 1 based on the value in the data
                unique_category = int(data[col].values[0])  # Ensure it's numeric
                dummy_column_name = f"{col}_{unique_category}"
                data[dummy_column_name] = 1

            data = data.drop(columns=curn_fam_cols)
            
            # Reorder columns: non-categorical first, then OHT categorical in the specified order
            #reordered_cols = non_categorical_cols + \
            #                [col for col in final_row.columns if col.startswith("predFamilies")] + \
            #                [col for col in final_row.columns if col.startswith("State")] + \
            #                [col for col in final_row.columns if col.startswith("Curn_Fam")]
            
            

            # Return the processed data with the specified column order
            return data.astype(float)
        return data.astype(float)

class PriorityRuleAllocator(Allocator):
    def __init__(self, system, rule="SEC", saving=False):
        """Priority Rules based allocation
        Args:
            system (systeme.systeme): systeme
            rule (str, optional): regle de priorité. Defaults to "SEC". 
            
            "SEC" : shortest expected charge, 
            "LEC" : Longuest expected charge, - 
            "SCC" : shortest current charge, -
            "LCC" : longuest current charge, -
            "SST" : shortest setup time, -
            "LST" : longuest setup time, -
            "SPT" : shortest process time,
            "LPT" : longuest process time, -
            "SQ"  : shortest queue,
            "LQ"  : longuest queue, -
        """
        super().__init__(system)
        self.rule = rule
        self.saving = saving
        self.history = []


    def allocate(self, produit, ordre_cellule, _):
        """
        Alloue la ressource en fonction de la solution statique.
        id produit commence a 1
        famille produit commence à 1 (il faut faire -1)
        ordre cellule commence a 0
        soustraction du surplus des ressources en trop dans les cell precedentes et - 1 car commence par 0
        """
        if self.rule == "SEC" : 
            # shortest expected charge
            operator = np.argmin
            l = [r.exp_charge(produit) for r in self.system.cellules[ordre_cellule].ressources]
        elif self.rule == "LEC" :
            # longuest expected charge
            operator = np.argmax
            l = [r.exp_charge(produit) for r in self.system.cellules[ordre_cellule].ressources]
        elif self.rule == "SCC" :
            # shortest current charge
            operator = np.argmin
            l = [r.current_charge() for r in self.system.cellules[ordre_cellule].ressources]
        elif self.rule == "LCC" :
            # longuest current charge
            operator = np.argmax
            l = [r.current_charge() for r in self.system.cellules[ordre_cellule].ressources]
        elif self.rule == "SST" : 
            # shortest setup time
            operator = np.argmin
            l = [r.setupTimes[produit.famille-1] for r in self.system.cellules[ordre_cellule].ressources]
        elif self.rule == "LST" :
            # longuest setup time
            operator = np.argmax
            l = [r.setupTimes[produit.famille-1] for r in self.system.cellules[ordre_cellule].ressources]
        elif self.rule == "SPT" : 
            # shortest process time
            operator = np.argmin
            l = [r.processTimes[produit.famille-1] for r in self.system.cellules[ordre_cellule].ressources]
        elif self.rule == "LPT" :
            # longuest process time
            operator = np.argmax
            l = [r.processTimes[produit.famille-1] for r in self.system.cellules[ordre_cellule].ressources]
        elif self.rule == "SQ":
            # shortest queue
            operator = np.argmin
            l = [r.queued_elements() for r in self.system.cellules[ordre_cellule].ressources]
        elif self.rule == "LQ":
            # longuest queue
            operator = np.argmax
            l = [r.queued_elements() for r in self.system.cellules[ordre_cellule].ressources]

        value = int(operator(l))
        
        values = np.argsort(l)
        if operator is np.argmax:
            values = values[::-1]
        if self.saving :
            self.history.append([produit.id, value])
        
        return values


class PredictionModel:
    def __init__(self, system, cell):
        self.system = system
        self.cell = cell

    def get_model(self, produit):
        raise NotImplementedError("Subclasses must implement get_model()")

    def allocate(self, produit, ordre_cellule, data):
        raise NotImplementedError("Subclasses must implement allocate()")

class SingleLabelMixin:
    def allocate(self, produit, ordre_cellule, data):
        model = self.get_model(produit)

        # Dans sklearn, predict_proba retourne une matrice (n_samples, n_classes)
        expected_cols = model.feature_names_in_
        data = data[expected_cols]

        probas = model.predict_proba(data)[0]  
        ordered_choices = np.argsort(probas)[::-1]  # Tri décroissant des classes selon probas
        #ordered_classes = model.classes_[ordered_choices]
        return [int(cls) for cls in ordered_choices]

class MultiLabelMixin:
    def allocate(self, produit, ordre_cellule, data):
        model = self.get_model(produit)

        expected_cols = model.feature_names_in_
        data = data[expected_cols]

        
        probas_raw = model.predict_proba(data)
        probas = []

        for i, cls in enumerate(model.classes_):
            cls = cls.astype(int)
            if 1 in cls:
                idx_1 = np.where(cls == 1)[0][0]
                probas.append(probas_raw[i][0][idx_1])
            else:
                probas.append(0.0)

        ordered_choices = np.argsort(probas)[::-1]
        #print(f"prediction proba : {probas_raw} donc probas : {probas} pour produit {produit.id} de famille {produit.famille} et donc choix :  {ordered_choices}")
        return ordered_choices

    
class GlobalModel(PredictionModel):
    def __init__(self, model, system, cell):
        super().__init__(system, cell)
        self.model = model

    def get_model(self, produit):
        return self.model

    
class PerFamilyModel(PredictionModel):
    def __init__(self, model_dict, system, cell):
        super().__init__(system, cell)
        self.model_dict = model_dict

    def get_model(self, produit):
        return self.model_dict[produit.famille - 1]
    
class OneFamilyOnlyModel(PredictionModel):
    def __init__(self, model, family, system, cell, solution, singlelabel=True):
        super().__init__(system, cell)
        self.singlelabel=singlelabel
        self.model = model
        self.famille = family
        self.staticAllocator = StaticAllocator(system, solution)
        
    def allocate(self, produit, ordre_cellule, data):
        if produit.famille != self.famille: 
            return self.staticAllocator.allocate(produit, ordre_cellule, None)
        
        expected_cols = self.model.feature_names_in_
        data = data[expected_cols]
        if self.singlelabel:
            probas = self.model.predict_proba(data)[0]  
            ordered_choices = np.argsort(probas)[::-1]  # Tri décroissant des classes selon probas
            ordered_choices = [int(cls) for cls in ordered_choices]
        else :
            probas_raw = self.model.predict_proba(data)
            probas = []

            for i, cls in enumerate(self.model.classes_):
                cls = cls.astype(int)
                if 1 in cls:
                    idx_1 = np.where(cls == 1)[0][0]
                    probas.append(probas_raw[i][0][idx_1])
                else:
                    probas.append(0.0)

            ordered_choices = np.argsort(probas)[::-1]

        return ordered_choices
        
    
class GlobalSingleLabel(SingleLabelMixin, GlobalModel):
    pass

class PerFamilySingleLabel(SingleLabelMixin, PerFamilyModel):
    pass

class GlobalMultiLabel(MultiLabelMixin, GlobalModel):
    pass

class PerFamilyMultiLabel(MultiLabelMixin, PerFamilyModel):
    pass



class Preprocessor:
    def __init__(self, chunk_data_fn, scaler=None, replace_nan=True):
        self.chunk_data = chunk_data_fn
        self.scaler = scaler
        self.replace_nan = replace_nan

    def transform(self, features: pd.DataFrame, ordre_cellule: int) -> pd.DataFrame:
        # 1. Appeler chunk_data pour faire le filtrage et le encodage one-hot
        data = self.chunk_data(features, ordre_cellule)

        # 2. Appliquer le scaler si présent
        if self.scaler is not None:
            data = pd.DataFrame(self.scaler.transform(data), columns=data.columns, index=data.index)

        # 3. Remplacer les NaN si demandé
        if self.replace_nan:
            data.fillna(0, inplace=True)

        return data
























RDM = random
DR = dispatching_rule