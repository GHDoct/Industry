import pandas as pd
import time
import json
import systeme as sys
import os
import numpy as np
from simulation import simulation
import Allocation
import recherche_taboue
from concurrent.futures import ThreadPoolExecutor, as_completed

# tache a parraleliser
def ma_tache(scenarios_path_prefixe, solutions_path_prefixe, scenario_path, solution_path, dic, nombre_de_cellules, tabu_tenure, patience, iterations_max):
    system = sys.systeme(dic)
    scenario = pd.DataFrame(np.nan_to_num(pd.read_csv(scenarios_path_prefixe+scenario_path,header=None, index_col=None, sep=";"), nan=0)).astype(int).iloc[:,:-1]
    print(f"[DEBUT] scenario {scenario_path.split("/")[-1].split(".")[0]}")
    ag_solution = pd.read_csv(solutions_path_prefixe+solution_path, sep=";", index_col=None, header=None).iloc[:,1:-1]
    ag_mct = simulation(system=system, scenario=scenario, allocators=[Allocation.StaticAllocator(system, ag_solution) for _ in range(nombre_de_cellules)]).mean_completion_time()
    
    start_time = time.time()
    recherche = recherche_taboue.TabuSearch(system, scenario, recherche_taboue.mean_completion_time, [recherche_taboue.voisinage_insert, recherche_taboue.voisinage_swap
                                                                                                      ], tabu_tenure=tabu_tenure, max_stagnation=patience, ag_mct=ag_mct, 
                                                                                                      scenario_name=scenario_path.split("/")[-1].split(".")[0], iterations_max=iterations_max)
    recherche.run()
    
    duree = time.time()-start_time
    print(f"[FIN] scenario {scenario_path.split("/")[-1].split(".")[0]}, durée : {duree} s")
    
    return recherche




def main():

    ds = "K0"
    scenarios_path_prefixe = f"scenarios/{ds}/"
    solutions_path_prefixe = f"solution/{ds}_best/"

    if ds.startswith("K"):
        fms = "3C7R5F"
        nombre_de_cellules = 3
    elif ds.startswith("G"):
        fms = "5C14R5F"
        nombre_de_cellules = 5
    with open(f'fms/{fms}.json', 'r') as json_file: #5C14R5F #3C7R5F
        dic = json.load(json_file)
    
    tabu_tenure = nombre_de_cellules * 50
    patience = tabu_tenure + tabu_tenure//2
    #patience = 3*tabu_tenure
    iterations_max = None

    print(f"recherche taboue avec parametres [taille liste tabou = {tabu_tenure}, patience = {patience}, iterations_max = {iterations_max}]")

    parametres = [(scenarios_path_prefixe, solutions_path_prefixe, scenario_path, solution_path, dic, nombre_de_cellules, tabu_tenure, patience, iterations_max) for scenario_path, solution_path in zip(sorted(os.listdir(scenarios_path_prefixe), key= lambda k : int(k[1:].split(".csv")[0])), sorted(os.listdir(solutions_path_prefixe), key= lambda k : int(k.split(".csv")[0].split("_s")[-1])))]#[:1]
        

    gaps = []
    with ThreadPoolExecutor(max_workers=40) as executor:
        # soumettre chaque fonction avec ses propres paramètres
        futures = [executor.submit(ma_tache, *params) for params in parametres]

        # récupérer les résultats
        for future in as_completed(futures):
            result = future.result()
            gaps.append(result)
    
            gap = result.calcul_gap()
            print(f"Scénario {result.scenario_name} gap : {gap}")
            result.save_to_csv(file_name=f"logs_{result.scenario_name}_avecSwap.csv", comment=parametres[int(result.scenario_name[1:])-1])

            #result.convergeance_graphic(result.ag_mct)

    print("\nGaps trouvés :")
    for res in gaps:
        print(type(res)," : ", res)

        
    #print(f"en moyenne on a gap {sum(gaps)/len(gaps)} %")





















if __name__ == "__main__":
    main()
