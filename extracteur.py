import systeme
import Allocation
import numpy as np
import pandas as pd

class extracteur():
    def __init__(self, system, colonnes, cellules):
        self.system = system
        self.cellules = cellules
        if len(colonnes) != 0: 
            self.colonnes = colonnes
        else: 
            self.colonnes = None       

"""
    def time(self):
        return self.system.time
    
    def Family (self, produit):
        return produit.famille
    
    def all_ressources_local(self, cell, job):
        data,header = [],[]
        for r in self.cellules[cell].ressources:
            r.predFamily()
            r.current_charge()
            r.exp_charge(job)
            r.exp_gross(job)
            r.get_state()
            r.get_curn_fam()
            r.Qsize_R()

        eff_grosses = [g/min(grosses) for g in grosses]


    predFamilles = [[r.predFamily() for r in c.ressources] for c in self.systeme.cellules]
    curCharges = [[r.current_charge() for r in c.ressources] for c in self.systeme.cellules]
    expCharges = [r.exp_charge(job) for r in self.ressources]
    grosses = [r.exp_gross(job) for r in self.ressources]
    eff_grosses = [g/min(grosses) for g in grosses]
    if minimal : # shall delete this
        return pd.DataFrame([[time, Family] + [item for sublist in predFamilles for item in sublist] + [item for sublist in curCharges for item in sublist] + expCharges + eff_grosses])
    #-------------
    state_r = [r.get_state() for r in self.ressources]
    curn_Fam_R = [r.get_curn_fam() for r in self.ressources]
    Qsize_R = [r.Qsize_R() for r in self.ressources]
    
    Total_Cell_Charge_c = [sum([r.current_charge() for r in c.ressources]) for c in self.systeme.cellules]
    Cur_ChargesRates_R = list(np.divide(curCharges[self.systeme.cellules.index(self)], sum(curCharges[self.systeme.cellules.index(self)])) if sum(curCharges[self.systeme.cellules.index(self)]) != 0 else np.zeros_like(curCharges[self.systeme.cellules.index(self)]))
    Exp_ChargeRates_R = [r.exp_charge(job) / (sum(curCharges[self.systeme.cellules.index(self)]) + r.exp_gross(job)) for r in self.ressources]
    somme_charge_all = sum(Total_Cell_Charge_c)
    Res_prcnt_R = [[x / somme_charge_all for x in sublist] if somme_charge_all != 0 else [0] * len(sublist) for sublist in curCharges]
    Setup_Rate_R = [[r.sum_setups()/r.current_charge() if r.current_charge() != 0 else 0 for r in c.ressources] for c in self.systeme.cellules]
    Cell_prcnt__c = list(np.divide(Total_Cell_Charge_c, somme_charge_all) if somme_charge_all != 0 else np.zeros_like(Total_Cell_Charge_c))
    R_f = [[np.count_nonzero(np.array([prod.famille for prod in r.q])==job.famille)/r.Qsize_R() if r.Qsize_R() != 0 else 0 for r in c.ressources] for c in self.systeme.cellules]
    
    # ajouter curr charge / min curr charges des ress de la cellule (respectivement exp charge)

    cc = pd.DataFrame([[r.current_charge() for r in self.ressources]], index=None)
    ec = pd.DataFrame([expCharges], index=None)
    
    cc_mn = list(cc.div(cc.min(axis=1), axis=0).fillna(1).replace(np.inf, 100))
    ec_mn = list(ec.div(ec.min(axis=1), axis=0).fillna(1).replace(np.inf, 100))

    return pd.DataFrame([[time, Family]+[item for sublist in predFamilles for item in sublist]+state_r+curn_Fam_R+Qsize_R+\
                        [item for sublist in curCharges for item in sublist]+expCharges+Cur_ChargesRates_R+Exp_ChargeRates_R+\
                        eff_grosses+Total_Cell_Charge_c+[item for sublist in Setup_Rate_R for item in sublist]+\
                        [item for sublist in R_f for item in sublist]+Cell_prcnt__c+[item for sublist in Res_prcnt_R for item in sublist]+\
                        cc_mn+ec_mn], columns = self.header[:-1])


"""