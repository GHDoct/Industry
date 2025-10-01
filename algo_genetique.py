import numpy as np
import pandas as pd
import systeme as sys
import Allocation
from simulation import simulation
from concurrent.futures import ProcessPoolExecutor, as_completed
import os


def generer_population(taille, systeme:sys, scenario:pd.DataFrame):
    """Genere une population de taille taille, une solution est un choix d'allocation pour un scenario et un systeme."""
    nb_prods = scenario.shape[0]
    nb_ress = [1] + [len(cell.ressources) for cell in systeme.cellules]
    nb_cells = len(nb_ress) - 1

    bounds = np.array([sum(nb_ress[:i+2]) for i in range(nb_cells)])
    lower_bounds = np.array([sum(nb_ress[:i+1]) for i in range(nb_cells)])

    sols_cells = np.random.randint(
        low=lower_bounds[:, np.newaxis, np.newaxis],
        high=bounds[:, np.newaxis, np.newaxis],
        size=(nb_cells, taille, nb_prods)
    )

    return sols_cells.transpose(1, 2, 0)

def create_allocators(sol, system):
    """cree les objets StaticAllocator pour une seule allocation."""
    return [Allocation.StaticAllocator(system, sol) for _ in range(len(system.cellules))]

def precompute_allocators(population: np.ndarray, system):
    """precalcul des des staticAllocators pour toutes les solutions de la population."""
    return [create_allocators(pd.DataFrame(sol), system) for sol in population]

def evaluate_solution(allocators, system:dict, scenario):
    """fonction d'aide pour evaluer une seule solution"""
    try:
        return simulation(system=sys.systeme(system), scenario=scenario, allocators=allocators).mean_completion_time()
    except Exception as e:
        print(f"Error in evaluate_solution: {e}")
        raise

def evaluation(population: np.ndarray, system: dict, scenario: pd.DataFrame, verbose: int = 0):
    """evaluation d'une population de solutions"""
    
    # nombre de coeurs CPU
    num_cores = os.cpu_count()
    
    if verbose >= 2:
        print(f"Préparation de l'évaluation en utilisant {num_cores} cœurs.")
    
    precomputed_allocators = precompute_allocators(population, sys.systeme(system))
    if verbose >= 2:
        print("Début de l'évaluation en parallèle.")

    # debut de l'évaluation en parallèle
    evals = []
    with ProcessPoolExecutor(max_workers=num_cores) as executor:
        # submit les taches en parralele et enregistrement de leurs resultats
        futures = [executor.submit(evaluate_solution, allocators, system, scenario) for allocators in precomputed_allocators]
        
        # Iterate through completed tasks
        for i, future in enumerate(as_completed(futures), start=1):
            eval_result = future.result()
            evals.append(eval_result)
            
            if verbose >= 1:
                # Display progress percentage
                progress = (i / len(population)) * 100
                print(f"Évaluation : {progress:.2f}% complétée", end="\r")

    if verbose >= 2:
        print("\nÉvaluation terminée.")
    
    return np.array(evals)

def mutation(population: np.ndarray, mutation_rate: float, lower_bounds: np.ndarray, upper_bounds: np.ndarray):
    """
    Applique une mutation à la population en modifiant certains éléments aléatoirement, en respectant les bornes spécifiques par colonne.
    
    Args:
        population (np.ndarray): Population de solutions.
        mutation_rate (float): Taux de mutation (probabilité qu'un élément soit muté).
        lower_bounds (np.ndarray): Bornes inférieures spécifiques à chaque colonne.
        upper_bounds (np.ndarray): Bornes supérieures spécifiques à chaque colonne.

    Returns:
        np.ndarray: Population après mutation.
    """
    # Initialiser un masque de mutation
    nb_mutations = np.random.rand(*population.shape) < mutation_rate
    
    # Créer les mutations (valeurs aléatoires respectant les bornes)
    mutation_values = np.random.randint(
        lower_bounds[np.newaxis, np.newaxis, :], 
        upper_bounds[np.newaxis, np.newaxis, :], 
        size=population.shape
    )

    # Appliquer la mutation directement à la population
    return np.where(nb_mutations, mutation_values, population)
    """
    # Tableau pour stocker les nouvelles valeurs après mutation
    population_mutated = np.copy(population)
    
    # Appliquer la mutation en tenant compte des bornes spécifiques par colonne
    for col in range(population.shape[2]):
        # Générer les nouvelles valeurs aléatoires pour cette colonne (dans ses bornes)
        mutation_values = np.random.randint(lower_bounds[col], upper_bounds[col], size=population.shape[:2])
        
        # Remplacer les valeurs mutées dans la population
        population_mutated[:, :, col] = np.where(nb_mutations[:, :, col], mutation_values, population[:, :, col])
    
    return population_mutated"""

"""def croisement(systeme:sys, scenario:pd.DataFrame, population: np.ndarray, evaluations: np.ndarray, prcent_garde: float = 5, prcent_best: float = 10, prcent_fusion: float = 80, mutation_rate: float = 0.05):
    taille_population = population.shape[0]
    nb_best = int(taille_population * prcent_best/100)
    indices_triees = np.argsort(evaluations)
    best_solutions_indices = indices_triees[:nb_best]
    
    # Garder un pourcentage de solutions parmi les meilleures
    nb_garde = int(prcent_garde * nb_best/100)
    indices_garde = np.random.choice(best_solutions_indices, size=nb_garde, replace=False)
    solutions_gardees = population[indices_garde]
    
    # Générer des solutions par croisement
    
    ################################################################################
    nb_fusion = int(taille_population * prcent_fusion)
    parents_indices = np.random.choice(best_solutions_indices, size=nb_fusion * 2, replace=True)
    parents = population[parents_indices].reshape(nb_fusion, 2, population.shape[1], population.shape[2])
    
    # Croisement entre les parents en prenant chaque cellule de manière aléatoire tout en respectant les bornes par colonne
    enfants = np.empty_like(parents[:, 0])  # Initialise les enfants avec la même forme que les parents individuels

    # Pour chaque colonne, on croise en prenant en compte les bornes spécifiques
    for col in range(population.shape[2]):
        enfants[:, :, col] = np.where(np.random.rand(nb_fusion, population.shape[1]) < 0.5, 
                                    parents[:, 0, :, col], 
                                    parents[:, 1, :, col])
    ################################################################################
    taille_population = population.shape[0]
    n_lignes = population.shape[1]
    n_colonnes = population.shape[2]

    # --- Calcul du nombre d'enfants à générer ---
    nb_naissances = int(prcent_fusion * taille_population/100)
    if nb_naissances % 2 != 0:
        nb_naissances -= 1  # on veut un nombre pair d'enfants

    nb_fusion = nb_naissances // 2  # un couple = 2 enfants

    # --- Tirage aléatoire de couples de parents ---
    indices_parents = np.random.choice(taille_population, size=(nb_fusion, 2), replace=False)
    parents = population[indices_parents]  # shape: (nb_fusion, 2, n_lignes, n_colonnes)

    # --- Croisement ligne par ligne (sans mélange intra-ligne) ---
    # masque booléen indiquant si une ligne vient du parent 0 ou 1
    mask = np.random.rand(nb_fusion, n_lignes) < 0.5  # shape: (nb_fusion, n_lignes)
    mask = np.expand_dims(mask, axis=-1)  # pour broadcast sur les colonnes → (nb_fusion, n_lignes, 1)

    # initialisation du tableau des enfants
    enfants = np.empty((nb_naissances, n_lignes, n_colonnes))

    # enfant 1 de chaque couple : prend les lignes selon mask
    enfants[0::2] = np.where(mask, parents[:, 0], parents[:, 1])

    # enfant 2 de chaque couple : prend les lignes complémentaires
    enfants[1::2] = np.where(mask, parents[:, 1], parents[:, 0])
    
    ##########################################################
    # Fusionner les solutions gardées et les enfants générés
    taille_restante = taille_population - solutions_gardees.shape[0] - enfants.shape[0]
    nouvelle_population = np.vstack((solutions_gardees, enfants)).astype(int)
    
    # Générer des solutions aléatoires pour compléter la population
    if taille_restante > 0:
        solutions_random = generer_population(taille_restante, systeme=systeme, scenario=scenario)
        nouvelle_population = np.vstack((nouvelle_population, solutions_random))
    
    # Appliquer la mutation sur la nouvelle population
    nouvelle_population = mutation(nouvelle_population, mutation_rate, np.array([sum([len(systeme.cellules[j].ressources) for j in range(i)])+1 for i in range(len(systeme.cellules))]), np.array([sum([len(systeme.cellules[j].ressources) for j in range(i+1)])+1 for i in range(len(systeme.cellules))]))
    
    return nouvelle_population
"""

def soft_weights(length, temp=3):
    """Retourne des poids décroissants normalisés (softmax-like)"""
    ranks = np.arange(length)
    weights = np.exp(-ranks / temp)
    return weights / weights.sum()

# croisement comme java code, top 50% avec bottom 50%
def croisement(systeme: sys, scenario: pd.DataFrame, population: np.ndarray, evaluations: np.ndarray, mutation_rate: float = 0.1, top_percent: float = 50, bottom_percent: float = 50, verbose=2):
    taille_population = population.shape[0]
    n_lignes = population.shape[1]
    n_colonnes = population.shape[2]

    nb_naissances = taille_population // 2  # On remplace 50% de la population

    # Sélection des indices des meilleurs et des pires
    nb_best = int(top_percent / 100 * taille_population)
    nb_worst = int(bottom_percent / 100 * taille_population)
    best_indices = np.arange(nb_best)
    worst_indices = np.arange(taille_population - nb_worst, taille_population)

    # Calcul des poids pour les meilleurs et les pires
    weights_best = soft_weights(len(best_indices), temp=1.5)
    weights_worst = soft_weights(len(worst_indices), temp=1.5)
    # Tirage pondéré de parents
    parents_best = population[np.random.choice(best_indices, size=nb_naissances, replace=True, p=weights_best)]
    parents_worst = population[np.random.choice(worst_indices, size=nb_naissances, replace=True, p=weights_worst)]

    # Masque aléatoire pour sélectionner quelle ligne vient de quel parent
    mask = np.random.rand(nb_naissances, n_lignes, 1) < 0.5  

    enfants = np.where(mask, parents_best, parents_worst).astype(int)

    # mutation l'insertion
    lower_bounds = np.array([sum([len(systeme.cellules[j].ressources) for j in range(i)]) + 1 for i in range(len(systeme.cellules))])
    upper_bounds = np.array([sum([len(systeme.cellules[j].ressources) for j in range(i + 1)]) + 1 for i in range(len(systeme.cellules))])

    
    if verbose >= 2:
        print("mutation des nouveaux individus ... ")
    population_mutée = mutation(population, mutation_rate, lower_bounds, upper_bounds)

    if verbose >= 2:
        print("Evaluation des nouveaux individus ... ")
    # evaluation des enfants
    evaluations_enfants = evaluation(enfants, systeme.dic, scenario, verbose=verbose)
    if verbose >= 2:
        print()

    # Insertion des enfants dans la population triée et leurs evals
    population_combined = np.vstack((population_mutée, enfants))
    evaluations_combined = np.concatenate((evaluations, evaluations_enfants))

    # Trier la population et les evals (déja triés à moitié donc tri rapide)
    sorted_indices = np.argsort(evaluations_combined)
    nouvelle_population = population_combined[sorted_indices]
    nouvelle_evaluations = evaluations_combined[sorted_indices]

    # Retourner la nouvelle population et les évaluations triées
    return nouvelle_population[:population.shape[0]], nouvelle_evaluations[:population.shape[0]]


def elitism(population: np.ndarray, evaluations: np.ndarray, elite_size: int):
    """Conserve les meilleures solutions pour la prochaine génération."""
    elite_indices = np.argsort(evaluations)[:elite_size]
    return population[elite_indices]




"""
def algorithme_genetique(taille_population: int, system: sys, scenario: pd.DataFrame, 
                         nb_generations: int = 100, prcent_garde: float = 0.05, 
                         prcent_best: float = 0.1, prcent_fusion: float = 0.3, 
                         mutation_rate: float = 0.05, elite_size: int = 5, 
                         max_stagnation: int = 10, verbose: int = 0):
    
    if verbose >= 1:
        print(f"Initialisation de la population avec {taille_population} individus...")
    
    # 1. Générer la population initiale
    population = generer_population(taille_population, system, scenario)
    
    if verbose >= 1:
        print(f"Population initiale générée.")
    
    # 2. Initialiser la meilleure solution et son évaluation
    best_solution = None
    best_evaluation = np.inf
    stagnation_counter = 0  # Compteur de stagnation pour critère d'arrêt
    #last_best_evaluation = np.inf

    # 3. Boucle sur les générations
    for generation in range(nb_generations):
        if verbose >= 1:
            print(f"== Génération {generation+1}/{nb_generations} ==")
        
        # 4. Évaluation de la population
        if verbose >= 2:
            print("Évaluation de la population en cours...", end="")
        evaluations = evaluation(population, system.dic, scenario, verbose)
        if verbose >= 2:
            print("terminée.")
            print(evaluations)
            print("\n")
        # 5. Élites : Conserver les meilleures solutions
        if verbose >= 2:
            print(f"Conservation des {elite_size} meilleures solutions (élites)...", end="")
        elites = elitism(population, evaluations, elite_size)
        #elites_evaluations = evaluation(elites, system.dic, scenario)

        if verbose >= 2:
            print("terminée.")

        # 6. Mise à jour de la meilleure solution
        min_eval = np.min(evaluations)
        if min_eval < best_evaluation:
            best_solution = population[np.argmin(evaluations)]
            best_evaluation = min_eval
            stagnation_counter = 0  # Réinitialiser le compteur de stagnation
            if verbose >= 1:
                print(f"Nouvelle meilleure solution trouvée avec évaluation : {best_evaluation}")
        else:
            stagnation_counter += 1
            if verbose >= 1:
                print(f"Pas d'amélioration dans cette génération. Stagnation : {stagnation_counter}/{max_stagnation}")
        
        #last_best_evaluation = best_evaluation
        
        # Critère d'arrêt basé sur la stagnation (pas d'amélioration)
        if stagnation_counter >= max_stagnation:
            if verbose >= 1:
                print(f"Arrêt anticipé après {generation+1} générations à cause de la stagnation.")
            break
        
        # 7. Croisement et mutation pour générer la nouvelle population
        if verbose >= 2:
            print(f"Croisement et mutation en cours pour générer une nouvelle population...")
        population = croisement(
            systeme=system,
            scenario=scenario,
            population=population,
            evaluations=evaluations,
            prcent_garde=prcent_garde,
            prcent_best=prcent_best,
            prcent_fusion=prcent_fusion,
            mutation_rate=mutation_rate
        )
        if verbose >= 2:
            print(f"Nouvelle population générée.")
        
        # 8. Réintégration des élites dans la nouvelle population
        if verbose >= 2:
            print(f"Réintégration des élites dans la population.")
        population[-elite_size:] = elites
    
    if verbose >= 1:
        print(f"Meilleure solution trouvée : {best_solution}")
        print(f"Évaluation de la meilleure solution : {best_evaluation}")
    
    return best_solution, best_evaluation
"""


def algorithme_genetique(taille_population: int, system: sys, scenario: pd.DataFrame, 
                         nb_generations: int = 10000, 
                         prcent_best: float = 50, prcent_fusion: float = 50, 
                         mutation_rate: float = 0.1, 
                         max_stagnation: int = 1000, verbose: int = 2):
    """
    Algorithme génétique principal.

    Args:
        taille_population (int): Taille de la population.
        system (systeme): Système object.
        scenario (pd.DataFrame): Scénario pour l'évaluation.
        nb_generations (int): Nombre maximum de générations.
        prcent_garde (float): Pourcentage de solutions à garder parmi les meilleures.
        prcent_best (float): Pourcentage des meilleures solutions à considérer pour les croisements.
        prcent_fusion (float): Pourcentage des solutions générées par croisement.
        mutation_rate (float): Taux de mutation.
        elite_size (int): Nombre d'élites à conserver dans chaque génération.
        max_stagnation (int): Nombre maximum de générations sans amélioration avant d'arrêter l'algorithme.
        verbose (int): Niveau de verbosité (0 = aucun affichage, 1 = affichage de base, 2 = affichage détaillé).
    
    Returns:
        np.ndarray: Meilleure solution trouvée.
        float: Score (évaluation) de la meilleure solution.
    """

    if verbose >= 0:
        print(f"Initialisation de la population ({taille_population} individus)...")

    historique_population = []
    historique_evaluations = []

    # 1. Générer la population initiale
    population = generer_population(taille_population, system, scenario)
    
    # 2. Évaluation de la population (en dehors de la boucle de croisement)
    evaluations = evaluation(population, system.dic, scenario, verbose)
    print()

    # 3. Tri de la population et des evaluations
    sorted_indices = np.argsort(evaluations)
    population = population[sorted_indices]
    evaluations = evaluations[sorted_indices]
    
    # 4. Initialiser la meilleure solution et son évaluation
    stagnation_counter = 0  # Compteur de stagnation pour critère d'arrêt
    best_solution = population[0]
    best_evaluation = evaluations[0]

    historique_population.append(population)
    historique_evaluations.append(evaluations)
    

    # 5. Boucle sur les générations
    for generation in range(nb_generations):
        if verbose >= 0:
            print(f"== Génération {generation+1}/{nb_generations} ==")

        population, evaluations = croisement(
            systeme=system,
            scenario=scenario,
            population=population,
            evaluations=evaluations,
            mutation_rate=mutation_rate,
            top_percent=prcent_best,
            bottom_percent=prcent_fusion,
            verbose=verbose
        )

        # 5. Suivi du meilleur
        if evaluations[0] < best_evaluation:
            best_solution = population[0]
            best_evaluation = evaluations[0]
            stagnation_counter = 0
            if verbose >= 0:
                print(f"Nouvelle meilleure solution : {best_evaluation:.4f}")
        else:
            stagnation_counter += 1
            if verbose >= 1:
                print(f"Aucune amélioration. Stagnation : {stagnation_counter}/{max_stagnation}")

        historique_population.append(population)
        historique_evaluations.append(evaluations)

        # 6. Critère d'arrêt basé sur la stagnation (pas d'amélioration)
        if stagnation_counter >= max_stagnation:
            if verbose >= 1:
                print("Arrêt anticipé (stagnation).")
            break

        


    # 9. Affichage de la meilleure solution
    if verbose >= 1:
        print(f"Meilleure solution obtenue : {best_evaluation:.4f}")
    
    return best_solution, best_evaluation, historique_population, historique_evaluations
