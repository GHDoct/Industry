import pandas as pd
from matplotlib import pyplot as plt
import os
from simulation import simulation
import json
import systeme as sys
import Allocation
import numpy as np


def tracer_courbe(csv_path:str, prefixe_csv_path:str="logs_recherche_tabou", valeur_ag=None):
    df = pd.read_csv(prefixe_csv_path+"/"+csv_path, comment="#") 

    plt.figure(figsize=(10, 6)) 
    plt.plot(df[df.columns[0]], df[df.columns[1]], label="Meilleur courant", color="orange")
    plt.plot(df[df.columns[0]], df[df.columns[2]], label=f"Meilleur global {df[df.columns[2]].iloc[-1]:.2f}", color="blue")

    if valeur_ag is not None:
        plt.axhline(y=valeur_ag, color='red', linestyle='--', label=f'MCT AG = {valeur_ag:.2f}')

    plt.title(f"Evolution de la recherche tabou {" ".join(csv_path.split("_")[1:])} - Gap : {((df[df.columns[2]].iloc[-1]-valeur_ag)*100/valeur_ag):.2f} %")
    plt.xlabel("Itération")
    plt.ylabel("MCT")
    plt.legend()

    plt.savefig(f"convergeance_tabou/{csv_path.split(".csv")[0]}.png", dpi=300)
    plt.close()


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



    for file in os.listdir("logs_recherche_tabou"):
        print(file)
        system = sys.systeme(dic)
        num_scenario = int(file.split("_")[1][1:])
        scenario = pd.DataFrame(np.nan_to_num(pd.read_csv(scenarios_path_prefixe+f"s{num_scenario}.csv", header=None, index_col=None, sep=";"), nan=0)).astype(int).iloc[:,:-1]
        solution = pd.read_csv(solutions_path_prefixe + [x for x in os.listdir(solutions_path_prefixe) if x.__contains__(f"_s{num_scenario}.csv")][0],
                               sep=";", index_col=None, header=None).iloc[:,1:-1]
        ag_mct = simulation(system=system, scenario=scenario, allocators=[Allocation.StaticAllocator(system, solution) for _ in range(len(system.cellules))]).mean_completion_time()
        tracer_courbe(file, valeur_ag=ag_mct)
        



if __name__ == "__main__":
    main()