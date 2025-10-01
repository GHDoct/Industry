from produits import produit
import numpy as np
import pandas as pd
import Allocation
import time

INACTIVE = 0
ACTIVE_SETUP = 1
ACTIVE_PROCESS = 2

R = 0
TO_P = 1
TO_I = 2
N = 3

#cond = printing and self.cell.systeme.time == 10 and self.cell.systeme.cellules.index(self.cell) == 0 and self.cell.ressources.index(self) == 0
        

class Ressource():

    def __init__(self, cell, dic) -> None:
        """
        cell (Cellule) : reference a la cellule a laquelle appartient la ressource
        dic (dict) : contient id et les process et setup times de la ressource
        """
        self.q = []
        self.current_state = INACTIVE
        self.current_setup = -1 # current setup of the resource (family) 
        self.current_job = produit(0,0, None) # current job produit, None ==> no job
        self.current_operation_time_left = 0 # current operation time left, either setup or process, not sum
        self._indicator = R
        self.cell = cell
        self.id = dic["id"]
        self.processTimes = dic["process_times"]
        self.setupTimes = dic["setup_times"]
        if self.cell.systeme.save_history :
            self.activity = np.array([], dtype=int)
            self.history = np.array([], dtype=int)

    def get_state(self):
        if self.current_state == INACTIVE:
            return "FREE"
        if self.current_state == ACTIVE_SETUP:
            if  self.current_operation_time_left > 0 :
                return "SETUP"
            else :
                return "WORKING"
        if self.current_state == ACTIVE_PROCESS and self.current_operation_time_left == 0:
            if len(self.q) > 0 and self.q[0].famille == self.current_job.famille:
                return "WORKING"
            elif len(self.q) > 0:
                return "SETUP"
            else :
                return "FREE"
        return "WORKING"
    
    def get_curn_fam(self):
        return self.current_setup
    
    def Qsize_R(self):
        if self.current_state != ACTIVE_SETUP or (self.current_operation_time_left ==0):
            if len(self.q) > 0:
                if self.q[0].famille == self.current_setup and self.current_state == ACTIVE_PROCESS and self.current_operation_time_left ==0 :
                    return len(self.q)-1
            return len(self.q)
        return len(self.q)+1

    def proceed(self, time): #ressource starts processing a job
        self.current_state = ACTIVE_PROCESS
        self.current_operation_time_left = self.processTimes[self.current_job.famille-1]
    
    def free(self, time): #resource finishes processing a job, either feeds it forward to the next cell or lets it complete and exit the system
        self.current_state = INACTIVE
        if self.cell.in_system_position < len(self.cell.systeme.cellules)-1:
            # feed job forward
            self.cell.systeme.cellules[self.cell.in_system_position+1].queue(self.current_job)
        else :
            # finish job
            self.current_job.completion(time)
            #print(f"terminus produit{self.current_job}")
        self.current_job = produit(0,0, None)

    def start_next(self, time): #resource setups for a job, could be 0
        self.current_state = ACTIVE_SETUP
        self.current_job = self.q.pop(0)
        if self.current_setup == self.current_job.famille :
            self.current_operation_time_left = 0
        else :
            self.current_setup = self.current_job.famille
            self.current_operation_time_left = self.setupTimes[self.current_job.famille-1]

    def update_q(self, time): # updates state of resource, does everything that does not consume time : decisions of setup or process, changes in ress state
        indicator = self._indicator
        past_indicator = -1
        while(indicator != past_indicator):
            past_indicator = indicator
            if self.current_operation_time_left > 0:
                indicator = R
            elif self.current_state == ACTIVE_SETUP :
                self.proceed(time)
                indicator = TO_P
            elif self.current_state == ACTIVE_PROCESS :
                self.free(time)
                indicator = TO_I
            elif len(self.q) > 0 :
                self.start_next(time)
                indicator = N
            else :
                indicator = R
        self._indicator = indicator
    
    def tick(self, time): # updates resource state, then passes 1 time unit and reupdates resource state
        self.update_q(time)
        if self.current_operation_time_left > 0 :
            self.current_operation_time_left -= 1 

        if self.cell.systeme.save_history :
            self.activity = np.append(self.activity,self.current_state)
            if self.current_state != INACTIVE : 
                self.history = np.append(self.history, self.current_job.id)
            else : 
                self.history = np.append(self.history, 0)
        #if self.cell.systeme.cellules.index(self.cell) == 0 and self.cell.ressources.index(self) == 0:
            #print(f"tick {time} : len q = {self.Qsize_R()} {[p.id for p in self.q]}")
        #self.update_q(time) 

    def desc(self, imbrique = 0) -> None:
        print("\t"*imbrique + f"ressource {self.id} :")
        if self.processTimes is not None:
            print("\t"*(imbrique+1) + f"tps de traitement : {self.processTimes}")
            print("\t"*(imbrique+1) + f"tps de preparation : {self.setupTimes}")
        else:
            print("\t"*(imbrique+1) + "pas encore assigné")

    #informative functions
    def predFamily(self):
        if len(self.q) == 0 :
            return self.current_setup if self.current_setup >= 0 else 0
        return self.q[-1].famille
    def queued_elements(self):
        return len(self.q)
    def current_charge(self):
        s = self.current_operation_time_left if self.current_operation_time_left > 0 else 0
        if self.current_state == ACTIVE_SETUP :
            s += self.processTimes[self.current_job.famille-1]
        crnt_fam = self.current_job.famille
        for prod in self.q:
            if crnt_fam != prod.famille:
                s += self.setupTimes[crnt_fam-1]
                crnt_fam = prod.famille
            s += self.processTimes[crnt_fam-1]
        return s
    def sum_setups(self):
        s = self.current_operation_time_left if self.current_state == ACTIVE_SETUP else 0
        crnt_fam = self.current_setup
        for prod in self.q:
            if crnt_fam != prod.famille:
                s += self.setupTimes[crnt_fam-1]
                crnt_fam = prod.famille
        return s 
    def sum_process(self):
        return self.current_charge() - self.sum_setups()
    def exp_charge(self, job:produit):
        return self.current_charge() + self.exp_gross(job)
    def exp_gross(self, job:produit):
        if len(self.q) > 0:
            fam = self.q[-1].famille
        else :
            fam = self.current_setup 
        if fam != job.famille:
            return self.processTimes[job.famille-1] + self.setupTimes[job.famille-1]
        return self.processTimes[job.famille-1]  
    def pt(self, job:produit):
        return self.processTimes[job.famille-1]  
    def st(self, job:produit):
        if len(self.q) > 0:
            fam = self.q[-1].famille
        else :
            fam = self.current_setup 
        if fam == job.famille:
            return 0
        return self.setupTimes[job.famille-1]


class Cellule():
    def __init__(self, systeme, dic:dict) -> None:
        self.logs_features = np.array([])
        self.logs_choices = np.array([])
        self.systeme = systeme
        self.id = dic["id"]
        self.ressources = []
        self.q = []
        self.total_decision_time = 0
        self.allocator = None
        self.model_per_family = True
        self.in_system_position = len(systeme.cellules)
        for ress in dic["resources"]:
            r = Ressource(self, ress)
            self.ressources.append(r)
        self.feature_extractor = Feature_extractor(
            ressources=self.ressources,
            systeme=self.systeme,
            cellule_index=self.in_system_position,
            header=None, # on ne l'a pas encore construit
            model_per_family=self.model_per_family
        )
        

    def ordered_ressources_cc(self):
        charges = np.array([r.current_charge() for r in self.ressources])
        return np.argsort(charges).tolist()

    def prepare_header(self):        
        offset = sum([len(c.ressources) for c in self.systeme.cellules][:self.in_system_position]) # number of ressources on the cells before
        if self.model_per_family :
            self.header = []
        else :
            self.header = ["Family"]
        self.header = self.header + \
            [f"Qsize_R{size}" for size in range(offset+1,offset+len(self.ressources)+1)] + \
            [f"Cur_Charge_comparable_R{size}" for size in range(offset+1,offset+len(self.ressources)+1)] + \
            [f"Exp_Charge__R{size}" for size in range(offset+1,offset+len(self.ressources)+1)] + \
            [f"Exp_ChargeRates_R{size}" for size in range(offset+1,offset+len(self.ressources)+1)] + \
            [f"Exp_Charge__comparable_R{size}" for size in range(offset+1,offset+len(self.ressources)+1)] + \
            [f"Eff_Gross_R{size}" for size in range(offset+1,offset+len(self.ressources)+1)] + \
            [f"predFamilies_R{size}" for size in range(offset+1,+offset+len(self.ressources)+1)] + \
            [f"Cell%__c{size}" for size in range(1,len(self.systeme.cellules)+1)] + \
            \
            ['Selected Resource']
            #[f"QPT_R{size}" for size in range(offset+1,offset+len(self.ressources)+1)] + \
            #[f"LPT_R{size}" for size in range(offset+1,offset+len(self.ressources)+1)] + \
            #[f"QST_R{size}" for size in range(offset+1,offset+len(self.ressources)+1)] + \
            #[f"LST_R{size}" for size in range(offset+1,offset+len(self.ressources)+1)] + \
            #[f"StotalPT_R{size}" for size in range(offset+1,offset+len(self.ressources)+1)] + \
            #[f"LtotalPT_R{size}" for size in range(offset+1,offset+len(self.ressources)+1)] + \
            #[f"StotalST_R{size}" for size in range(offset+1,offset+len(self.ressources)+1)] + \
            #[f"LtotalST_R{size}" for size in range(offset+1,offset+len(self.ressources)+1)] + \
            #[f"StotalG_R{size}" for size in range(offset+1,offset+len(self.ressources)+1)] + \
            #[f"LtotalG_R{size}" for size in range(offset+1,offset+len(self.ressources)+1)] + \
            #[f"QG_R{size}" for size in range(offset+1,offset+len(self.ressources)+1)] + \
            #[f"LG_R{size}" for size in range(offset+1,offset+len(self.ressources)+1)] + \
            #[f"LQE_R{size}" for size in range(offset+1,offset+len(self.ressources)+1)] + \
            #[f"MQE_R{size}" for size in range(offset+1,offset+len(self.ressources)+1)] + \
            #\
            #['Selected Resource']
        
        self.feature_extractor.header = self.header
        
        """
        offset = sum([len(c.ressources) for c in self.systeme.cellules][:self.systeme.cellules.index(self)]) # number of ressources on the cells before
        self.header = ["Time", "Family"] + \
            [f"predFamilies_R{size}" for size in range(1,sum([len(c.ressources) for c in self.systeme.cellules])+1)] + \
            [f"State_R{size}" for size in range(offset+1,offset+len(self.ressources)+1)] + \
            [f"Curn_Fam_R{size}" for size in range(offset+1,offset+len(self.ressources)+1)] + \
            [f"Qsize_R{size}" for size in range(offset+1,offset+len(self.ressources)+1)] + \
            [f"Cur_Charge_R{size}" for size in range(1,sum([len(c.ressources) for c in self.systeme.cellules])+1)] + \
            [f"Exp_Charge__R{size}" for size in range(offset+1,offset+len(self.ressources)+1)] + \
            [f"Cur_ChargesRates_R{size}" for size in range(offset+1,offset+len(self.ressources)+1)] + \
            [f"Exp_ChargeRates_R{size}" for size in range(offset+1,offset+len(self.ressources)+1)] + \
            [f"Eff_Gross_R{size}" for size in range(offset+1,offset+len(self.ressources)+1)] + \
            [f"Total_Cell_Charge_c{size}" for size in range(1,len(self.systeme.cellules)+1)] + \
            [f"Setup_Rate_R{size}" for size in range(1,sum([len(c.ressources) for c in self.systeme.cellules])+1)] + \
            [f"R{size}_f" for size in range(1,sum([len(c.ressources) for c in self.systeme.cellules])+1)] + \
            [f"Cell%__c{size}" for size in range(1,len(self.systeme.cellules)+1)] + \
            [f"Res%_R{size}" for size in range(1,sum([len(c.ressources) for c in self.systeme.cellules])+1)] + \
            [f"Cur_Charge_comparable_R{size}" for size in range(offset+1,offset+len(self.ressources)+1)] + \
            [f"Exp_Charge__comparable_R{size}" for size in range(offset+1,offset+len(self.ressources)+1)] + \
            ['Selected Resource']
        """

    def desc(self, imbrique = 0) -> None:
        print("\t"*imbrique + f"cellule {self.id} :")
        for ress in self.ressources:
            ress.desc(imbrique+1)
        
    def tick(self, time):
        for ress in self.ressources:
            ress.tick(time)

    def allocator_params(self, job:produit=None):
        if isinstance(self.allocator, Allocation.StaticAllocator) or isinstance(self.allocator, Allocation.RandomAllocator) : #static
            return None
        else : # dynamic
            return self.extract_features(job, False) # true pour ne retourner que data minimal
        
    def save_data(self, job:produit=None):
        df = self.extract_features(job, False) # false pour recuperer toutes les infos dans le df
        self.logs_features = np.vstack([self.logs_features, df.to_numpy()]) if self.logs_features.size else df.to_numpy()   

    def old_extract_features(self, job:produit, minimal=False):
        print("attention utilisation de old_extract_features")
        cc = pd.DataFrame([[r.current_charge() for r in self.ressources]], index=None)
        curCharges = [[r.current_charge() for r in c.ressources] for c in self.systeme.cellules]
        grosses = [r.exp_gross(job) for r in self.ressources]
        Total_Cell_Charge_c = [sum([r.current_charge() for r in c.ressources]) for c in self.systeme.cellules]
        somme_charge_all = sum(Total_Cell_Charge_c)
        

        family = job.famille
        Qsize_R = [r.Qsize_R() for r in self.ressources]    
        cc_mn = list(cc.div(cc.max(axis=1), axis=0).fillna(1).replace(np.inf, 1))
        ec = pd.DataFrame([[r.exp_charge(job) for r in self.ressources]], index=None)
        Exp_ChargeRates_R = [
            (r.exp_charge(job) / denom if denom != 0 else 1)
            for r in self.ressources
            for denom in [(sum(curCharges[self.in_system_position]) + r.exp_gross(job))]
        ]
        #Exp_ChargeRates_R = [r.exp_charge(job) / (sum(curCharges[self.systeme.cellules.index(self)]) + r.exp_gross(job)) for r in self.ressources]
        ec_mn = list(ec.div(ec.min(axis=1), axis=0).fillna(1))
        eff_grosses = [g/(min(grosses)+1) for g in grosses]
        predFamilles = [int(r.predFamily()==family) for r in self.ressources]
        Cell_prcnt__c = list(np.divide(Total_Cell_Charge_c, somme_charge_all) if somme_charge_all != 0 else np.zeros_like(Total_Cell_Charge_c))
        
        # c'est ici que se place ce que je vais ajouter, le colonnes des hyperheuristiques

        \
        pts = [r.pt(job) for r in self.ressources]
        sts = [r.st(job) for r in self.ressources]
        spts = [r.sum_process() for r in self.ressources]
        ssts = [r.sum_setups() for r in self.ressources]
        sgs = [r.current_charge() for r in self.ressources]
        gs = [r.exp_gross(job) for r in self.ressources]
        lqs = [r.queued_elements() for r in self.ressources]

        qpt = [int(pt==min(pts)) for pt in pts]
        lpt = [int(pt==max(pts)) for pt in pts]
        qst = [int(st==min(sts)) for st in sts]
        lst = [int(st==max(sts)) for st in sts]
        stotalpt = [int(spt==min(spts)) for spt in spts]
        ltotalpt = [int(spt==max(spts)) for spt in spts]
        stotalst = [int(sst==min(ssts)) for sst in ssts]
        ltotalst = [int(sst==max(ssts)) for sst in ssts]
        stotalg = [int(sg==min(sgs)) for sg in sgs]
        ltotalg = [int(sg==max(sgs)) for sg in sgs]
        qg = [int(g==min(gs)) for g in gs]
        lg = [int(g==max(gs)) for g in gs]
        lqe = [int(lq==min(lqs)) for lq in lqs]
        mqe = [int(lq==max(lqs)) for lq in lqs]


        if self.model_per_family :
            list_concatenated = Qsize_R+cc_mn+list(ec)+Exp_ChargeRates_R+ec_mn+eff_grosses+predFamilles+Cell_prcnt__c+\
                            qpt+lpt+qst+lst+stotalpt+ltotalpt+stotalst+ltotalst+stotalg+ltotalg+qg+lg+lqe+mqe
        else :    
            list_concatenated = [family]+Qsize_R+cc_mn+list(ec)+Exp_ChargeRates_R+ec_mn+eff_grosses+predFamilles+Cell_prcnt__c+\
                            qpt+lpt+qst+lst+stotalpt+ltotalpt+stotalst+ltotalst+stotalg+ltotalg+qg+lg+lqe+mqe
        
        return pd.DataFrame([list_concatenated], columns = self.header[:-1])

    def extract_features(self, job:produit, minimal=False):
        return self.feature_extractor.extract(job)
    


    def queue(self, job:produit):
        self.q.append(job)

    def proceed_queue(self):
        for job in sorted(self.q, key=lambda k : k.id) :
            features = self.allocator_params(job)
            if self.systeme.saving:
                self.save_data(job)
            if self.systeme.count_decision_times:
                start = time.time()
            ress_choice = None
            ress_choices = self.allocator.allocate(job, self.in_system_position, features)
            for choice in ress_choices:
                if self.ressources[int(choice)].processTimes[job.famille-1] > 0:
                    ress_choice = choice
                    break
            if ress_choice is None:
                raise(Exception("unaccepted allocation"))
            if self.systeme.saving:
                if self.systeme.labels_encoded:
                    ress_choice_encoded = self.ordered_ressources_cc().index(ress_choice)
                    self.logs_choices = np.append(self.logs_choices, ress_choice_encoded)
                else :
                    self.logs_choices = np.append(self.logs_choices, ress_choice)
            if self.systeme.count_decision_times:
                self.total_decision_time += (time.time() - start)
            #job.sequences.append(ress_choice) #gain vitesse
            self.ressources[int(ress_choice)].q.append(job)
        self.q = []



class Feature_extractor:
    def __init__(self, ressources, systeme, cellule_index, header, model_per_family):
        self.ressources = ressources
        self.systeme = systeme
        self.in_system_position = cellule_index  # ordre_cellule
        self.header = header
        self.model_per_family = model_per_family

    def extract(self, job, minimal=False):
        features = []
        features += self._add_family_feature(job)
        features += self._add_qsize_feature()
        features += self._add_normalized_current_charge()
        features += self._add_expected_charge(job)
        features += self._add_expected_charge_rate(job)
        features += self._add_normalized_expected_charge(job)
        features += self._add_eff_grosses(job)
        features += self._add_pred_families(job)
        features += self._add_cell_percentages()
        #features += self._add_hyperheuristics(job)

        return pd.DataFrame([features], columns=self.header[:-1])

    def _add_family_feature(self, job):
        return [] if self.model_per_family else [job.famille]

    def _add_qsize_feature(self):
        return [r.Qsize_R() for r in self.ressources]

    def _add_normalized_current_charge(self):
        cc = pd.DataFrame([[r.current_charge() for r in self.ressources]])
        cc_mn = cc.div(cc.max(axis=1), axis=0).fillna(1).replace(np.inf, 1).values.flatten().tolist()
        return cc_mn

    def _add_expected_charge(self, job):
        ec = [r.exp_charge(job) for r in self.ressources]
        return ec

    def _add_expected_charge_rate(self, job):
        curCharges = [[r.current_charge() for r in c.ressources] for c in self.systeme.cellules]
        return [
            r.exp_charge(job) / (sum(curCharges[self.in_system_position]) + r.exp_gross(job))
            if (sum(curCharges[self.in_system_position]) + r.exp_gross(job)) != 0 else 1
            for r in self.ressources
        ]

    def _add_normalized_expected_charge(self, job):
        ec = pd.DataFrame([[r.exp_charge(job) for r in self.ressources]])
        return ec.div(ec.min(axis=1), axis=0).fillna(1).values.flatten().tolist()

    def _add_eff_grosses(self, job):
        grosses = [r.exp_gross(job) for r in self.ressources]
        min_g = min(grosses) + 1
        return [g / min_g for g in grosses]

    def _add_pred_families(self, job):
        return [int(r.predFamily() == job.famille) for r in self.ressources]

    def _add_cell_percentages(self):
        total_cell_charge = [sum([r.current_charge() for r in c.ressources]) for c in self.systeme.cellules]
        total_charge = sum(total_cell_charge)
        if total_charge == 0:
            return [0] * len(total_cell_charge)
        return list(np.divide(total_cell_charge, total_charge))

    def _add_hyperheuristics(self, job):
        pts = [r.pt(job) for r in self.ressources]
        sts = [r.st(job) for r in self.ressources]
        spts = [r.sum_process() for r in self.ressources]
        ssts = [r.sum_setups() for r in self.ressources]
        sgs = [r.current_charge() for r in self.ressources]
        gs = [r.exp_gross(job) for r in self.ressources]
        lqs = [r.queued_elements() for r in self.ressources]

        # binary flags: 1 if min or max, else 0
        def binary_flags(lst, min_max="min"):
            target = min(lst) if min_max == "min" else max(lst)
            return [int(val == target) for val in lst]

        return (
            binary_flags(pts, "min") + binary_flags(pts, "max") +
            binary_flags(sts, "min") + binary_flags(sts, "max") +
            binary_flags(spts, "min") + binary_flags(spts, "max") +
            binary_flags(ssts, "min") + binary_flags(ssts, "max") +
            binary_flags(sgs, "min") + binary_flags(sgs, "max") +
            binary_flags(gs, "min") + binary_flags(gs, "max") +
            binary_flags(lqs, "min") + binary_flags(lqs, "max")
        )











