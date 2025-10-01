import numpy as np
import pandas as pd
from json import dump


def set_seed(seed: int):
    np.random.seed(seed)


def generate_scenario(nb_familles: int,
                      nb_produits_range: tuple,
                      dates_arriv_range: tuple,
                      families_distribution: str,
                      arrival_dates_distribution: str) -> pd.DataFrame:
    """
    Generates a scenario DataFrame with specified distributions and ranges.

    Parameters:
    - nb_familles: Number of different families (int).
    - nb_produits_range: Tuple (min_produits, max_produits) for number of rows.
    - dates_arriv_range: Tuple (min_date, max_date) for arrival date values.
    - families_distribution: "poisson", "uniform", "normal" or "linear" distribution for families.
    - arrival_dates_distribution: "poisson", "uniform", "normal" or "linear" for arrival dates.

    Returns:
    - pandas DataFrame with columns: arrival_date, index, family, 0
    """
    
    min_produits, max_produits = nb_produits_range
    min_date, max_date = dates_arriv_range
    nb_produits = np.random.randint(min_produits, max_produits + 1)

    # === ARRIVAL DATES ===
    if arrival_dates_distribution == "uniform":
        arrival_dates = np.random.randint(min_date, max_date + 1, size=nb_produits)

    elif arrival_dates_distribution == "poisson":
        lam = (min_date + max_date) / 2
        arrival_dates = np.random.poisson(lam, nb_produits)
        arrival_dates = np.clip(arrival_dates, min_date, max_date)

    elif arrival_dates_distribution == "normal":
        mean = (min_date + max_date) / 2
        std_dev = (max_date - min_date) / 6  # 99.7% within range
        arrival_dates = np.random.normal(loc=mean, scale=std_dev, size=nb_produits)
        arrival_dates = np.clip(arrival_dates, min_date, max_date).astype(int)

    elif arrival_dates_distribution == "linear":
        weights = np.linspace(1, nb_produits, num=(max_date - min_date + 1))
        probabilities = weights / weights.sum()
        possible_dates = np.arange(min_date, max_date + 1)
        arrival_dates = np.random.choice(possible_dates, size=nb_produits, p=probabilities)

    else:
        raise ValueError("Invalid arrival_dates_distribution: choose from 'uniform', 'poisson', 'normal', or 'linear'")

    # Sort and shift to make first date zero
    arrival_dates.sort()
    arrival_dates -= arrival_dates[0]

    # === INDEX COLUMN ===
    indices = np.arange(1, nb_produits + 1)

    # === FAMILY COLUMN ===
    if families_distribution == "uniform":
        families = np.random.randint(1, nb_familles + 1, size=nb_produits)

    elif families_distribution == "poisson":
        lam = nb_familles / 2
        families = np.random.poisson(lam, nb_produits)
        families = np.clip(families, 1, nb_familles)

    elif families_distribution == "normal":
        mean = nb_familles / 2
        std_dev = nb_familles / 6
        families = np.random.normal(loc=mean, scale=std_dev, size=nb_produits)
        families = np.clip(families, 1, nb_familles).astype(int)

    elif families_distribution == "linear":
        weights = np.linspace(1, nb_familles, nb_familles)
        probabilities = weights / weights.sum()
        families = np.random.choice(np.arange(1, nb_familles + 1), size=nb_produits, p=probabilities)

    else:
        raise ValueError("Invalid families_distribution: choose from 'uniform', 'poisson', 'normal', or 'linear'")

    # === COLUMN 0 (parcequ'elle existe oui, initialement pour les priorités dans les codes de wassim mais comme je ne le prend pas en compte je met des 0) ===
    zeros = np.zeros(nb_produits, dtype=int)

    # === CREATE DATAFRAME ===
    df = pd.DataFrame({
        "arrival_date": arrival_dates,
        "identifier": indices,
        "family": families,
        "priority": zeros
    })

    return df


def generate_multiple_scenarios(nb_scenarios: int,
                                 nb_familles: int,
                                 nb_produits_range: tuple,
                                 dates_arriv_range: tuple,
                                 families_distribution: str,
                                 arrival_dates_distribution: str,
                                 vary_nb_produits: bool = True,
                                 nb_produits_distribution: str = "uniform",
                                 path: str = None) -> list:
    """
    Generate multiple scenario DataFrames.

    Returns a list of DataFrames, one per scenario.
    """
    scenarios = []

    min_prods, max_prods = nb_produits_range

    def sample_nb_produits():
        if nb_produits_distribution == "uniform":
            return np.random.randint(min_prods, max_prods + 1)
        elif nb_produits_distribution == "normal":
            mean = (min_prods + max_prods) / 2
            std = (max_prods - min_prods) / 6
            return int(np.clip(np.random.normal(loc=mean, scale=std), min_prods, max_prods))
        elif nb_produits_distribution == "poisson":
            lam = (min_prods + max_prods) / 2
            return int(np.clip(np.random.poisson(lam), min_prods, max_prods))
        elif nb_produits_distribution == "fixed":
            return (min_prods + max_prods) // 2
        else:
            raise ValueError("Invalid nb_produits_distribution")

    # Pre-sample fixed nb_produits if needed
    fixed_nb_produits = sample_nb_produits() if not vary_nb_produits else None

    i = 0
    for _ in range(nb_scenarios):
        nb_produits = sample_nb_produits() if vary_nb_produits else fixed_nb_produits
        df = generate_scenario(
            nb_familles=nb_familles,
            nb_produits_range=(nb_produits, nb_produits),  # fixed for this scenario
            dates_arriv_range=dates_arriv_range,
            families_distribution=families_distribution,
            arrival_dates_distribution=arrival_dates_distribution
        )
        i+=1
        if path:
            df.to_csv(path+f"/s{i}.csv", sep=";", index=False)
        scenarios.append(df)

    return scenarios


def generate_instance_config(nb_familles: int,
                             nb_cells: int = None,
                             resources_per_cell: dict = None,
                             nb_cells_range: tuple = (1, 5),
                             resources_range: tuple = (1, 3),
                             process_time_range: tuple = (1, 5),
                             setup_time_range: tuple = (0, 3),
                             distribution_process: str = "uniform",
                             distribution_setup: str = "uniform",
                            process_time_ranges_per_resource: dict = None,
                            setup_time_ranges_per_resource: dict = None,
                            process_time_ranges_per_cell: dict = None,
                            setup_time_ranges_per_cell: dict = None) -> dict:
    """
    Generates a config dict representing an instance's internal structure.
    """

    # Step 1: Determine number of cells
    if nb_cells is None:
        nb_cells = np.random.randint(nb_cells_range[0], nb_cells_range[1] + 1)

    config = {
        "nb_familles": nb_familles,
        "cells": []
    }

    # Step 2: Create each cell
    for cell_id in range(1, nb_cells + 1):
        cell = {"id": cell_id, "resources": []}

        # Determine number of resources for this cell
        if resources_per_cell and cell_id in resources_per_cell:
            nb_resources = resources_per_cell[cell_id]
        else:
            nb_resources = np.random.randint(resources_range[0], resources_range[1] + 1)

        # Add placeholder for this cell
        for _ in range(nb_resources):
            cell["resources"].append(None)

        config["cells"].append(cell)

    # Step 3: Fill in each resource
    def draw_values(distribution, value_range, size):
        min_val, max_val = value_range
        if distribution == "uniform":
            return np.random.randint(min_val, max_val + 1, size)
        elif distribution == "poisson":
            lam = (min_val + max_val) / 2
            return np.clip(np.random.poisson(lam, size), min_val, max_val)
        elif distribution == "normal":
            mean = (min_val + max_val) / 2
            std = (max_val - min_val) / 6
            return np.clip(np.random.normal(mean, std, size).astype(int), min_val, max_val)
        elif distribution == "linear":
            return np.linspace(min_val, max_val, size, dtype=int)
        else:
            raise ValueError(f"Unsupported distribution: {distribution}")

    for cell in config["cells"]:
        cell_id = cell["id"]
        for res_idx in range(len(cell["resources"])):
            key = (cell_id, res_idx + 1)

            # Process time range hierarchy
            if process_time_ranges_per_resource and key in process_time_ranges_per_resource:
                proc_range = process_time_ranges_per_resource[key]
            elif process_time_ranges_per_cell and cell_id in process_time_ranges_per_cell:
                proc_range = process_time_ranges_per_cell[cell_id]
            else:
                proc_range = process_time_range

            # Setup time range hierarchy
            if setup_time_ranges_per_resource and key in setup_time_ranges_per_resource:
                setup_range = setup_time_ranges_per_resource[key]
            elif setup_time_ranges_per_cell and cell_id in setup_time_ranges_per_cell:
                setup_range = setup_time_ranges_per_cell[cell_id]
            else:
                setup_range = setup_time_range

            proc = draw_values(distribution_process, proc_range, nb_familles)
            setup = draw_values(distribution_setup, setup_range, nb_familles)

            cell["resources"][res_idx] = {
                "process_times": proc.tolist(),
                "setup_times": setup.tolist()
            }

    return config


def build_instance_json(config: dict, path:str = None) -> dict:
    """
    Converts a config dict into the proper JSON structure.
    """
    output = {"cells": []}

    for cell in config["cells"]:
        cell_json = {
            "id": cell["id"],
            "resources": []
        }

        for idx, res in enumerate(cell["resources"], 1):
            cell_json["resources"].append({
                "id": idx,
                "process_times": res["process_times"],
                "setup_times": res["setup_times"]
            })

        output["cells"].append(cell_json)

    if path is not None:
        with open(path, "w") as f:
            dump(output, f, indent=4)

    return output


