import pandas as pd
from matplotlib import pyplot as plt
import os


def tracer_courbe(csv_path:str, prefixe_csv_path:str="logs_recherche_tabou"):
    df = pd.read_csv(prefixe_csv_path+"/"+csv_path, comment="#") 

    plt.figure(figsize=(10, 6)) 
    plt.plot(df[df.columns[0]], df[df.columns[1]], label="Meilleur courant", color="orange")
    plt.plot(df[df.columns[0]], df[df.columns[2]], label="Meilleur global", color="blue")

    plt.title(f"Evolution de la recherche tabou {" ".join(csv_path.split("_")[1:])} ")
    plt.xlabel("Itération")
    plt.ylabel("MCT")
    plt.legend()

    plt.savefig(f"convergeance_tabou/{csv_path.split(".csv")[0]}.png", dpi=300)
    plt.close()


def main():
    for file in os.listdir("logs_recherche_tabou"):
        print(file)
        tracer_courbe(file)





if __name__ == "__main__":
    main()