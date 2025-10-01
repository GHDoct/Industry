import random
import pandas as pd
import numpy as np
import systeme as sys
import hashlib
from simulation import simulation
import Allocation
from typing import List, Callable, Any, Tuple, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed
from matplotlib import pyplot as plt
import matplotlib.cm as cm

class TabuSearch:
    def __init__(
        self,
        systeme: sys.systeme,
        scenario: pd.DataFrame,
        objective_function: Callable[[Any], float],
        neighborhood_functions: List [Callable[[Any], List[pd.DataFrame]]],
        scenario_name: str= "",
        tabu_tenure: int = 5,
        max_stagnation: int = 1000, 
        ag_mct = None,
        iterations_max = None
    ):
        """recherche taboue, instancier la classe puis l'appeler avec run(solution_initiale)

        Args:
            objective_function (Callable[[Any], float]): fonction objectif, on cherche à le minimiser
            neighborhood_function (Callable[[Any], List[Any]]): fonction de voisinage
            tabu_tenure (int, optional): longueur de la liste taboue. Defaults to 5.
            max_iterations (int, optional): nombre max d'itérations avant d'arreter l'algo. Defaults to 100.
        """
        self.scenario = scenario
        self.systeme = systeme
        self.objective_function = objective_function
        self.neighborhood_functions = neighborhood_functions
        self.neighborhood_functions_names = ["swap" if fnc is voisinage_swap else "insert" for fnc in neighborhood_functions]
        self.tabu_tenure = tabu_tenure
        self.max_stagnation = max_stagnation
        self.tabu_list = []
        self.tabu_list_hash = set()
        self.evaluation_cache = {}
        self.historique_scores = []
        self.historique_best_scores = []
        self.neighborhood_types = []
        self.ag_mct = ag_mct
        self.scenario_name = scenario_name
        self.iterations_max = iterations_max

    def is_tabu(self, current_solution:pd.DataFrame, solution:pd.DataFrame) -> bool:
        return self.codify_solution(current_solution, solution) in self.tabu_list
    
    def codify_solution(self, current_solution:pd.DataFrame, solution: pd.DataFrame) -> str:
        mask = current_solution != solution
        diff_indices = np.argwhere(mask.to_numpy())
        differences = [f"{job},{cell}" for job, cell in diff_indices]
        return differences
        #flat_bytes = solution.to_numpy().tobytes()
        #return hashlib.sha256(flat_bytes).hexdigest()

    def codify_solution_one(self, solution:pd.DataFrame) -> str:
        flat_bytes = solution.to_numpy().tobytes()
        return hashlib.sha256(flat_bytes).hexdigest()

    def add_to_tabu_list(self,current_solution:pd.DataFrame, solution:pd.DataFrame):
        self.tabu_list.append(self.codify_solution(current_solution, solution))
        #self.tabu_list_hash.add(self.codify_solution(solution))
        if len(self.tabu_list) > self.tabu_tenure:
            self.tabu_list.pop(0)
            #self.tabu_list_hash.pop()

    def generate_random_solution(self):
        # random
        nb_lignes = self.scenario.shape[0]
        nb_colonnes = len(self.systeme.cellules)
        bornes = [np.arange(sum([len(x.ressources) for x in self.systeme.cellules[:col]])+1,
                            sum([len(x.ressources) for x in self.systeme.cellules[:col+1]])+1) 
                            for col in range(len(self.systeme.cellules))]
        
        data = np.column_stack([
            np.random.choice(bornes[col], size=nb_lignes)
            for col in range(nb_colonnes)
        ])
        return pd.DataFrame(data)
    
    def generate_initial_solution(self) -> pd.DataFrame:
        #shortest process and setup time PR

        nb_lignes = self.scenario.shape[0]
        nb_colonnes = len(self.systeme.cellules)

        # Pré-calcul : meilleure ressource pour chaque (famille, cellule)
        meilleur_choix = {}

        # Liste des familles distinctes
        familles_uniques = self.scenario.iloc[:, 2].unique()  # 3e colonne = famille

        for famille in familles_uniques:
            meilleur_choix[famille] = {}
            for col in range(nb_colonnes):
                cellule = self.systeme.cellules[col]
                ressources = cellule.ressources

                offset = sum(len(c.ressources) for c in self.systeme.cellules[:col]) + 1

                meilleur_score = float('inf')
                meilleure_ressource_index = None

                for idx, ressource in enumerate(ressources):
                    setup_time = ressource.setupTimes[famille-1]
                    process_time = ressource.processTimes[famille-1]
                    score = setup_time + process_time

                    if score < meilleur_score:
                        meilleur_score = score
                        meilleure_ressource_index = idx

                meilleur_choix[famille][col] = offset + meilleure_ressource_index

        # Génération du DataFrame à partir des choix pré-calculés
        data = np.zeros((nb_lignes, nb_colonnes), dtype=int)
        for row in range(nb_lignes):
            famille_produit = self.scenario.iloc[row, 2]
            for col in range(nb_colonnes):
                data[row, col] = meilleur_choix[famille_produit][col]

        return pd.DataFrame(data)

    def evaluate(self, solution: pd.DataFrame) -> float:
        key = self.codify_solution_one(solution)
        if key not in self.evaluation_cache:
            self.evaluation_cache[key] = self.objective_function(solution, self.systeme, self.scenario)
        return self.evaluation_cache[key]
        
    def generate_initial_solution_PR(self):
        return simulation(system=self.systeme, scenario=self.scenario, allocators=[Allocation.PriorityRuleAllocator(self.systeme, "SEC", saving=True) for _ in range(len(self.systeme.cellules))]).generate_solution()

    
    def evaluate_parallel(self, solutions: List[pd.DataFrame], max_workers=40) -> List[Tuple[pd.DataFrame, float]]:
        results = []
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.evaluate, sol): sol for sol in solutions}
            for future in as_completed(futures):
                sol = futures[future]
                cost = future.result()
                results.append((sol, cost))
        return results


    def calcul_gap(self):
        return (self.best_cost-self.ag_mct)*100/self.ag_mct
        

    def run(self, initial_solution=None):
        if initial_solution is None:
            initial_solution = self.generate_initial_solution_PR()

        current_solution = initial_solution
        best_solution = current_solution
        best_cost = self.objective_function(current_solution, self.systeme, self.scenario)
        self.historique_scores.append(best_cost)
        self.historique_best_scores.append(best_cost)

        print(f"evaluation of initial solution : {best_cost}")

        iteration = 0
        stagnation = 0
        while stagnation < self.max_stagnation and (self.iterations_max is None or iteration < self.iterations_max):
            #neighbors = self.neighborhood_function(current_solution, self)
            #neighbors = [n for n in neighbors if not self.is_tabu(n)]

            neighbors = []
            neighborhood_type_limits = []
            # Try each neighborhood function in order until we find a non tabu neighbor
            for neighborhood_fn in self.neighborhood_functions:
                candidate_neighbors = neighborhood_fn(current_solution, self)
                candidate_neighbors = [n for n in candidate_neighbors if not self.is_tabu(current_solution, n)]

                if candidate_neighbors:
                    [neighbors.append(x) for x in candidate_neighbors]
                    [neighborhood_type_limits.append("swap" if neighborhood_fn is voisinage_swap else "insert") for _ in candidate_neighbors]
                    #break  # Stop at first usable neighborhood, just switch this off if you want the best neighbor future me

            if not neighbors:
                print("\naucun voisin pas tabou trouvé. Arret de la recherche.")
                break

            # Select the best neighbor
            values = [self.evaluate(n) for n in neighbors]
            best_index = np.argmin(values)
            best_neighbor = neighbors[best_index]
            
            self.neighborhood_types.append(neighborhood_type_limits[best_index])

            best_neighbor_cost = values[best_index]

            #evaluated_neighbors = self.evaluate_parallel(neighbors, max_workers=2)
            #best_neighbor, best_neighbor_cost = min(evaluated_neighbors, key=lambda x: x[1])

            if best_neighbor_cost < best_cost:
                stagnation = 0
                self.add_to_tabu_list(current_solution, best_neighbor)
                best_solution = best_neighbor
                best_cost = best_neighbor_cost
                current_solution = best_neighbor
            else : 
                stagnation += 1
                self.add_to_tabu_list(current_solution, best_neighbor) # c t add best_neighbor et pas de ligne apres juste pour continuer avec l'actuelle meilleure solution mais je trouve qu'on coince dans un opti local
                current_solution = best_neighbor
            
            self.historique_best_scores.append(best_cost)
            self.historique_scores.append(best_neighbor_cost)



            print(f"Scénario {self.scenario_name} Iteration {iteration+1}: meilleur coût = {best_cost}, patience : {stagnation}/{self.max_stagnation}")#,end="\r")
            iteration += 1

        self.best_solution = best_solution
        self.best_cost = best_cost

        return best_solution, best_cost
    
    def convergeance_graphic(self, ag_mct=None, foldername="convergeance_tabou"):
        fig, ax = plt.subplots()

        if ag_mct is not None:
            ax.axhline(y=ag_mct, color='red', linestyle='--', label='AG')

        X = range(len(self.historique_scores))
        Y1 = self.historique_scores              # meilleur voisin courant
        Y2 = self.historique_best_scores         # meilleur voisin depuis le début
        types = self.neighborhood_types          # liste de chaînes (2 types max)


        for i in range(len(X)):
            if Y1[i] == Y2[i]:
                ax.plot(X[i], Y1[i], marker="o", color="green", markersize=1, label="identiques" if i == 0 else "")
            else:
                ax.plot(X[i], Y1[i], marker="o", color="red", markersize=1, label="meilleur courant" if i == 0 else "")
                ax.plot(X[i], Y2[i], marker="o", color="blue", markersize=1, label="meilleur global" if i == 0 else "")

        unique_types = list(set(types))
        symbols = ['x', 'o']
        type_to_marker = {t: symbols[i % len(symbols)] for i, t in enumerate(unique_types)}

        for i in range(len(X)):
            ax.plot(X[i], Y1[i],
                    marker=type_to_marker[types[i]],
                    color="black", markersize=2,
                    linestyle="None",
                    label=types[i] if i == 0 else "")

        ax.set_title(f"Courbe d'evolution de la recherche tabou {self.scenario_name}")
        ax.set_xlabel("iteration")
        ax.set_ylabel("MCT")
        ax.grid(True)

        ax.legend()

        plt.savefig(foldername+f"/scenario_{self.scenario_name[1:]}.png", dpi=300, bbox_inches="tight")
        plt.close(fig) 


    def save_to_csv(self, file_name=None, folder_path="logs_recherche_tabou", comment=None):
        if file_name is None:
            file_name = "log.csv"

        df = pd.DataFrame({
            "iteration": range(len(self.historique_scores)),
            "meilleur_voisin_courant": self.historique_scores,
            "meilleur_voisin_global": self.historique_best_scores
        })

        with open(folder_path + "/" + file_name, "w", encoding="utf-8") as f:
            if comment:
                f.write(f"# {comment}\n")  # écrit le commentaire en première ligne
            df.to_csv(f, index=False)
        


def voisinage_swap(solution: pd.DataFrame, search: 'TabuSearch') -> List[pd.DataFrame]:
    def get_premier_echange(df: pd.DataFrame, line: int, col: int):
        arr_solution = df.values
        valeur_courante = arr_solution[line, col]

        # On cherche uniquement les lignes en dessous
        lignes_suivantes = np.arange(line + 1, arr_solution.shape[0])
        valeurs_suivantes = arr_solution[lignes_suivantes, col]

        # Filtrer celles qui ont une valeur différente
        mask_diff = valeurs_suivantes != valeur_courante
        lignes_diff = lignes_suivantes[mask_diff]
        valeurs_diff = valeurs_suivantes[mask_diff]

        for ligne_cible, valeur_cible in zip(lignes_diff, valeurs_diff):
            df_copy = df.copy()
            # Échanger les deux valeurs
            df_copy.iloc[line, col], df_copy.iloc[ligne_cible, col] = valeur_cible, valeur_courante

            # Vérifier si la solution générée est taboue
            if not search.is_tabu(solution, df_copy):
                return df_copy  # ← Retourner le premier échange valide

        return None  # Aucun échange admissible

    # Parcours ligne par ligne, colonne par colonne
    voisins = []
    for col in range(solution.shape[1]):
        for row in range(solution.shape[0]):
            voisin = get_premier_echange(solution, row, col)
            if voisin is not None:
                voisins.append(voisin) # sinon juste return [voisin] pour juste le premier voisin
                #return [voisin]  # mettre en commentaire si on veut tous les voisins

    return voisins  # [] si aucun voisin admissible trouvé


def voisinage_insert_group(solution:pd.DataFrame, search:TabuSearch) -> List[pd.DataFrame]:
    def get_voisins(df:pd.DataFrame, line:int, col:int, search:TabuSearch):
        offset = sum([len(x.ressources) for x in search.system.cellules[:col]])+1
        arr = np.arange(offset,offset+len(search.system.cellules[col].ressources))
        voisins_locaux = np.delete(arr, np.where(arr == df.iloc[line, col])[0])
        voisins = []
        for voisin in voisins_locaux:
            df_copy = df.copy()
            df_copy.iloc[line, col] = voisin
            voisins.append(df_copy)
        return voisins
    
    voisins = []
    for cellule in range(solution.shape[1]):
        for produit in range(solution.shape[0]):
            [voisins.append(v) for v in get_voisins(solution, line=produit, col=cellule, search=search)]

    return voisins


def voisinage_insert(solution: pd.DataFrame, search: 'TabuSearch') -> List[pd.DataFrame]:
    neighbors = []
    for col in range(solution.shape[1]):
        for row in range(solution.shape[0]):
            # Calcul des valeurs possibles pour cette cellule
            offset = sum(len(cell.ressources) for cell in search.systeme.cellules[:col]) + 1
            possibles = np.arange(offset, offset + len(search.systeme.cellules[col].ressources))

            current_value = solution.iloc[row, col]
            for val in possibles:
                if val == current_value:
                    continue  # ne pas proposer la valeur actuelle

                # Créer une copie et modifier une seule case
                neighbor = solution.copy()
                neighbor.iloc[row, col] = val

                # Vérifier si ce voisin est tabou
                if not search.is_tabu(solution, neighbor):
                    neighbors.append(neighbor) # on retourne tous les voisins
                    #return [neighbor]  # on retourne le premier non tabou

    return neighbors  # [] si aucun voisin admissible trouvé


def mean_completion_time(solution:pd.DataFrame, systeme:sys.systeme, scenario:pd.DataFrame) -> float:
    return simulation(system=systeme, scenario=scenario, allocators=[Allocation.StaticAllocator(systeme, solution) for _ in range(len(systeme.cellules))]).mean_completion_time()

