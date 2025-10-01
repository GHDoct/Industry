import ressource as ress
from produits import produit
import numpy as np
import pandas as pd
from systeme import systeme
from Allocation import RDM
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import cv2
import os
import re


class simulation():
    # behaviour functions
    def __init__(self, system, scenario, allocators, saving=False, columns = [], labels_encoded = False, gant_calculations=False, count_decision_times=False) -> None:
        self.produits = {}
        self.scenario = scenario
        self.time = -1
        self.system = systeme(system.dic)
        self.system.saving = saving
        self.system.labels_encoded = labels_encoded
        self.system.save_history = gant_calculations
        self.columns = columns
        self.system.assign_allocators(allocators)
        self.gant_calculations = gant_calculations
        self.system.count_decision_times = count_decision_times

        self.scenario_inverse = {}        #creer scenario inverse, clé = unité de temps, valeurs = np array de produits arrivant cette date
        for line in scenario.sort_values(by=scenario.columns[0]).to_numpy():
            self.scenario_inverse[line[0]] = np.append(self.scenario_inverse.get(line[0], np.array([])), produit(line[1], line[2], self))
        for key in self.scenario_inverse:
            self.scenario_inverse[key] = sorted(self.scenario_inverse[key], key=lambda k : k.id)

        self.run()
    def deploy(self):
        for prod in self.scenario_inverse.get(self.time, []):
            prod.arrival(self.system, self.time)
            #print(f"deploiement de produit {prod.id}")
    def check_end(self):
        self.time += 1
        #self.system.time = self.system.time + 1
        for l in self.scenario_inverse.values() :
            for prod in l:
                if prod.completion_time is None :
                    #print(f"{self.time}: waiting prod {prod.id}")
                    return False
        return True
    def run(self):
        while not self.check_end():
            self.deploy()
            self.system.tick(self.time)
    #----------------------------------

    # graphics functions
    def gantt(self, title=None, use_colors=True, path="gants/gant_chart.png"):
        if not self.gant_calculations:
            return "impossible de tracer le gant, essayez de reexecuter la simulation avec le parametre gant_calculations True"
        
        plt.clf()

        arr = np.array([self.system.cellules[i].ressources[j].history for i in range(len(self.system.cellules)) for j in range(len(self.system.cellules[i].ressources))])
        arr_act = np.array([self.system.cellules[i].ressources[j].activity for i in range(len(self.system.cellules)) for j in range(len(self.system.cellules[i].ressources))])
        _, num_time_steps = arr.shape
        ar = [np.arange(len(c.ressources)) for c in self.system.cellules]
        num_resources = np.concatenate([a.flatten() for a in ar])

        if use_colors:
            colors =   ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
                    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
                    '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
                    '#c49c94', '#f7b6d2', '#c7c7c7', '#dbdb8d', '#9edae5',
                    '#393b79', '#637939', '#8c6d31', '#843c39', '#7b4173',
                    '#5254a3', '#63707a', '#8ca252', '#b5cf6b', '#cedb9c',
                    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
                    '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
                    '#c49c94', '#f7b6d2', '#c7c7c7', '#dbdb8d', '#9edae5']
        else :
            colors = ["#6495ed"]

        plt.clf()
        fig, ax = plt.subplots(figsize=(min((2**16-1)//150, self.system.cellules[0].ressources[0].history.shape[0]*4//5), len(num_resources)))
        plt.xlim(0, num_time_steps)
        ax.set_xlim(0, num_time_steps)

        for i in range(len(num_resources)):
            start = 0
            while start < num_time_steps:
                job_id = arr[i, start]
                state = arr_act[i, start]
                if job_id != 0:
                    end = start + 1
                    while end < num_time_steps and arr[i, end] == job_id and arr_act[i, end] == state:
                        end += 1
                    width = end - start
                    if state == ress.ACTIVE_PROCESS:
                        ax.barh(i, width, left=start, color=colors[(self.produits[job_id].famille-1) % len(colors)], edgecolor="black", linewidth=2)
                        ax.text(start + width / 2, i, str(job_id), ha='center', va='center', color='black', fontsize=20)
                    else:
                        if use_colors:
                            ax.barh(i, width, left=start, color=colors[(self.produits[job_id].famille-1) % len(colors)], edgecolor="black", linewidth=2, hatch="/")
                        else :
                            ax.barh(i, width, left=start, color="white", edgecolor="black", linewidth=2, hatch="/")
                    start = end
                else:
                    start += 1

            if i< len(num_resources)-1 :
                if num_resources[i]>=num_resources[i+1] :
                    ax.axhline(i + 0.5, color='black', linewidth=1)

        handles = []
        if use_colors :
            for i in range(len(self.system.cellules[0].ressources[0].setupTimes)):
                patch = mpatches.Patch(facecolor= colors[i % len(colors)], edgecolor="black", label=f"Family process {i+1}")
                patch_s = mpatches.Patch(facecolor= colors[i % len(colors)], edgecolor="black", label=f"Family setup {i+1}", hatch="/")
                handles.append(patch)
                handles.append(patch_s)
                ax.legend(handles=handles, loc='center left', bbox_to_anchor=(1.0, 0.5))
        
        # Customize the chart
        ax.set_yticks(np.arange(num_resources.shape[0]))
        ax.set_xticks(np.arange(stop=num_time_steps, step=num_time_steps//300+1))
        ax.set_yticklabels([f'Resource {num_resources[i]+1}' for i in range(len(num_resources))])
        ax.set_xticklabels(np.arange(stop=num_time_steps, step=num_time_steps//300+1))
        ax.set_xlabel('Time')
        ax.set_ylabel('Resources')
        if title is None :
            title = ""
        ax.set_title(title)

        plt.grid(True, which='both', linestyle='--', linewidth=0.5)
        plt.tight_layout()
        plt.savefig(path)
        plt.show()


    def gantt_multi(self, path=""):
        if not self.gant_calculations:
            return "impossible de tracer le gant, essayez de reexecuter la simulation avec le parametre gant_calculations True"
       

        arr = np.array([self.system.cellules[i].ressources[j].history for i in range(len(self.system.cellules)) for j in range(len(self.system.cellules[i].ressources))])
        arr_act = np.array([self.system.cellules[i].ressources[j].activity for i in range(len(self.system.cellules)) for j in range(len(self.system.cellules[i].ressources))])
        _, num_time_steps = arr.shape
        ar = [np.arange(len(c.ressources)) for c in self.system.cellules]
        num_resources = np.concatenate([a.flatten() for a in ar])

        colors =   ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
            '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
            '#c49c94', '#f7b6d2', '#c7c7c7', '#dbdb8d', '#9edae5',
            '#393b79', '#637939', '#8c6d31', '#843c39', '#7b4173',
            '#5254a3', '#63707a', '#8ca252', '#b5cf6b', '#cedb9c',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
            '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
            '#c49c94', '#f7b6d2', '#c7c7c7', '#dbdb8d', '#9edae5']

        max_timesteps_fig = 250
        offset_fig = 5
        num_time_steps = min(max_timesteps_fig, arr.shape[1])
        nb_figs = arr.shape[1]//num_time_steps + 1

        for figure in range(nb_figs):
            plt.clf()
            if figure == nb_figs-1:
                left_border, right_border, fig_width = figure*num_time_steps, arr.shape[1], arr.shape[1]-(figure*num_time_steps)
            else :
                left_border, right_border, fig_width = figure*num_time_steps, (figure+1)*num_time_steps+offset_fig, num_time_steps

            if fig_width==0:
                break
            print(f"figure : {figure+1}/{nb_figs}, \tleftbord : {left_border}, \trightbord : {right_border}, \twidth : {fig_width}", end="\r")
                

            _, ax = plt.subplots(figsize=(fig_width, len(num_resources)))
            for i in range(len(num_resources)):
                start = left_border
                while start < right_border and start < arr.shape[1]:
                    job_id = arr[i, start]
                    state = arr_act[i, start]
                    if job_id != 0:
                        end = start + 1
                        while end < right_border and arr[i, end] == job_id and arr_act[i, end] == state:
                            end += 1
                        width = end - start
                        if state == ress.ACTIVE_PROCESS:
                            ax.barh(i, width, left=start, color=colors[self.produits[job_id].famille-1 % len(colors)], edgecolor="black", linewidth=2)
                            ax.text(start + width / 2, i, str(job_id), ha='center', va='center', color='black', fontsize=20)
                        else:
                            ax.barh(i, width, left=start, color=colors[self.produits[job_id].famille-1 % len(colors)], edgecolor="black", linewidth=2, hatch="/")
                        start = end
                    else:
                        start += 1

                if i< len(num_resources)-1 :
                    if num_resources[i]>=num_resources[i+1] :
                        ax.axhline(i + 0.5, color='black', linewidth=3)

            ax.set_yticks(np.arange(num_resources.shape[0]))
            ax.set_yticklabels([f'Resource {num_resources[i]}' for i in range(len(num_resources))])
            ax.set_xticks(np.arange(start=left_border, stop=right_border, step=1))
            ax.set_xticklabels(np.arange(start=left_border, stop=right_border, step=1))
            ax.set_xlabel('Time Steps')
            ax.set_ylabel('Resources')
            ax.set_title('Gantt Chart')
            plt.grid(True, which='both', linestyle='--', linewidth=0.5)
            plt.tight_layout()


            handles = []
            for i in range(len(self.system.cellules[0].ressources[0].setupTimes)):
                patch = mpatches.Patch(facecolor= colors[i % len(colors)], edgecolor="black", label=f"Famille process {i+1}")
                patch_s = mpatches.Patch(facecolor= colors[i % len(colors)], edgecolor="black", label=f"Famille setup {i+1}", hatch="/")
                handles.append(patch)
                handles.append(patch_s)
            ax.legend(handles=handles, loc='lower right')


            plt.savefig(f"gants/gant_chart_{path}{figure+1}.png")
            plt.close()
    #----------------------------------

    # calculating statistics functions
    def get_logs(self):
        return self.system.get_logs()

    def generate_solution(self):
        first_history = sorted(self.system.cellules[0].allocator.history, key=lambda x: x[0])
        ids = [pair[0] for pair in first_history]
        df = pd.DataFrame({"id": ids})

        for idx, c in enumerate(self.system.cellules):
            offset = sum(len(self.system.cellules[k].ressources) for k in range(idx))+1

            h_df = pd.DataFrame(c.allocator.history, columns=["id", f"cellule_{idx}"])
            h_df[f"cellule_{idx}"] = h_df[f"cellule_{idx}"] + offset
            df = df.merge(h_df, on="id")

        if (df["id"] == df.index + 1).all():
            df = df.drop(columns=["id"])
        df.columns = [None] * len(df.columns)
        
        return df

    def decision_times(self):
        return [c.total_decision_time for c in self.system.cellules]

    def total_decision_times(self):
        return sum(self.decision_times())

    def mean_completion_time(self):
        return np.mean([p.completion_time for p in self.produits.values()])
    def average_flowtime(self):
        return np.mean([p.flowtime() for p in self.produits.values()])
    def cmax(self):
        return np.max(self.produits.values())
    #----------------------------------

    # output functions



#----------------------------------
# work in progress gant fusion

def get_image_filenames_from_folder(folder):
    filenames = []
    pattern = re.compile(r'gant_chart_(\d+)\.png')
    
    for filename in os.listdir(folder):
        match = pattern.match(filename)
        if match:
            number = int(match.group(1))
            filenames.append((number, filename))
    
    filenames.sort(key=lambda x: x[0])
    return [filename for _, filename in filenames]

def find_overlap_area(img1, img2):
    height, _, _ = img1.shape
    axis_region_img1 = img1[int(0.9 * height):, :]
    axis_region_img2 = img2[:int(0.1 * height), :]
    result = cv2.matchTemplate(axis_region_img1, axis_region_img2, cv2.TM_CCOEFF_NORMED)
    _, _, _, max_loc = cv2.minMaxLoc(result)
    shift = max_loc[0]
    return shift

def stack_images_incrementally(folder, filenames):
    # Load the first image to start the process
    base_img = cv2.imread(os.path.join(folder, filenames[0]))

    for i in range(1, len(filenames)):
        next_img = cv2.imread(os.path.join(folder, filenames[i]))

        overlap_shift = find_overlap_area(base_img, next_img)
        height = max(base_img.shape[0], next_img.shape[0])
        total_width = base_img.shape[1] + next_img.shape[1] - overlap_shift

        # Create a blank canvas
        stacked_image = np.zeros((height, total_width, 3), dtype=np.uint8)
        # Place the base_img
        stacked_image[:base_img.shape[0], :base_img.shape[1]] = base_img
        # Place the next image, offset by the overlap shift
        stacked_image[:next_img.shape[0], base_img.shape[1] - overlap_shift: base_img.shape[1] - overlap_shift + next_img.shape[1]] = next_img
        # Update base_img to the new stacked image for the next iteration
        base_img = stacked_image
        # Free memory by releasing the previous image
        del next_img

    return base_img

def fusion_gants(folder_path):
    filenames = get_image_filenames_from_folder(folder_path)
    final_image = stack_images_incrementally(folder_path, filenames)
    cv2.imwrite(folder_path+"/stacked_gantt_chart.png", final_image)
    return final_image

#----------------------------------