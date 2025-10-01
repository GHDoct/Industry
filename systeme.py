import ressource as ress
import numpy as np
import pandas as pd
import random
import Allocation
from extracteur import extracteur
import matplotlib.pyplot as plt

class systeme():
    def __init__(self, dic:dict, columns:list=[]) -> None:
        '''
            dic (dict) : dictionnaire contenant id et liste de cellules
        '''
        self.cellules = []
        self.dic = dic
        self.id = dic["id"]
        self.saving = False
        self.labels_encoded = False
        self.count_decision_times = False
        self.nb_familles = len(dic["cells"][0]['resources'][0]["process_times"])
        #self.time = -1
        self.save_history = True
        for cell in dic["cells"]:
            c = ress.Cellule(self, cell)
            self.cellules.append(c)
        for c in self.cellules:
            c.prepare_header()
        #self.extracteur = extracteur(self, columns, self.cellules)

    def prod_arrival(self, produit):
        self.cellules[0].queue(produit)

    def desc(self, imbrique = 0):
        print("\t"*imbrique + f"systeme :")
        for cell in self.cellules:
            cell.desc(imbrique+1)
            
    def tick(self, time):
        for cell in self.cellules :
            cell.proceed_queue()
            cell.tick(time)

    def assign_allocators(self, allocators):
        for i in range(len(self.cellules)):
            if not isinstance(allocators[i], Allocation.StaticAllocator) and not isinstance(allocators[i], Allocation.RandomAllocator) and not isinstance(allocators[i], Allocation.PriorityRuleAllocator):
                if type(allocators[i].model) is list :
                    self.cellules[i].model_per_family = True
                else : 
                    self.cellules[i].model_per_family = False
                    self.cellules[i].prepare_header()
                    self.cellules[i].feature_extractor.model_per_family = False
            else :
                self.cellules[i].model_per_family = False
                self.cellules[i].prepare_header()
                self.cellules[i].feature_extractor.model_per_family = False
            allocators[i].system = self
            self.cellules[i].allocator = allocators[i]

    def get_logs(self):
        return [pd.DataFrame(np.hstack([c.logs_features, c.logs_choices.reshape(-1, 1)]), columns=c.header) for c in self.cellules]

def generate_exact_dictionary(resource_numbers:list, num_families:int, process_times:list, setup_times:list):
    # genere un json d'un systeme avec les entrées exactes
    cells = []
    for cell_id in range(len(resource_numbers)):
        cell = {
            "id": cell_id +1,
            "ressources": []
        }

        for resource_id in range(1, resource_numbers[cell_id]+1):
            resource = {
                "id": resource_id,
                "process_times": process_times[cell_id],
                "setup_times": setup_times[cell_id]
            }
            cell["resources"].append(resource)
        
        cells.append(cell)
    
    result = {
        "id": 1,
        "cells": cells
    }
    
    return result

def generate_dictionary(num_cells, total_resources, num_families, process_time_bounds, setup_time_bounds):
    # genere un json d'un systeme avec une part d'aleatoire
    def random_times(bounds, size):
        return np.random.randint(bounds[0], bounds[1] + 1, size).tolist()
    
    def distribute_resources(num_cells, total_resources):
        """
            init tableau de 0 pour chaque cellule
            tire une cllule au hasard et lui donne une ressource en plus, 
            repete pour chaque ressource du nombre total
        """
        resources = [1] * num_cells
        for _ in range(total_resources-num_cells):
            resources[random.randint(0, num_cells - 1)] += 1
        return resources
    
    resources_per_cell = distribute_resources(num_cells, total_resources)
    
    cells = []
    for cell_id in range(1, num_cells + 1):
        cell = {
            "id": cell_id,
            "resources": []
        }
        
        for resource_id in range(1, resources_per_cell[cell_id - 1] + 1):
            resource = {
                "id": resource_id,
                "process_times": random_times(process_time_bounds, num_families),
                "setup_times": random_times(setup_time_bounds, num_families)
            }
            cell["resources"].append(resource)
        
        cells.append(cell)
    
    result = {
        "id": 1,
        "cells": cells
    }
    
    return result

UNIFORM = 1
RANDOM = 2
CLOCHE = 3
MULTIPLE_CLOCHES = 4

def generate_product_data(num_products, num_families, max_arrival_time, distribution=UNIFORM, nb_cloches=2):
    families = [i % num_families + 1 for i in range(num_products)]
    random.shuffle(families)

    if distribution == UNIFORM:
        arrival_dates = [i * max_arrival_time // num_products for i in range(num_products)]
    elif distribution == CLOCHE:
        mean_arrival = max_arrival_time // 2
        std_dev = max_arrival_time // 5
        arrival_dates = np.clip(np.random.normal(mean_arrival, std_dev, size=num_products), 0, max_arrival_time).astype(int)
    elif distribution == RANDOM:
        arrival_dates = [random.randint(0, max_arrival_time) for _ in range(num_products)]
    elif distribution == MULTIPLE_CLOCHES:
        bells_params = []
        for _ in range(nb_cloches):
            mean_arrival = np.random.randint(0, max_arrival_time + 1)
            std_dev = max_arrival_time // 10  # Écart type pour contrôler la dispersion
            bells_params.append((mean_arrival, std_dev))

        arrival_dates = []
        for _ in range(num_products):
            bell = np.random.choice(nb_cloches)  # Choix aléatoire d'une cloche
            mean, std = bells_params[bell]
            arrival_date = np.clip(np.random.normal(mean, std), 0, max_arrival_time).astype(int)
            arrival_dates.append(arrival_date)

    data = {
        "id": list(range(1, num_products + 1)),
        "arrival_date": arrival_dates,
        "family": families
    }

    df = pd.DataFrame(data)
    return df

def draw_arrival_times_plot(df, ylim=-1):
    arrival_counts = df['arrival_date'].value_counts().sort_index()
    if ylim == -1:
        ylim = np.max(arrival_counts)
        ylim = ylim//10 + ylim
    plt.figure(figsize=(10, 6))
    plt.plot(arrival_counts.index, arrival_counts.values, marker='o')
    plt.title('Nombre d\'arrivées de produits dans le temps')
    plt.xlabel('Temps')
    plt.ylabel('Nombre d\'arrivées')
    plt.grid(True)
    plt.ylim(0,ylim)
    plt.show()