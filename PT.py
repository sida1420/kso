

import heapq
import init
import selection
from classes import *
import evaluate
import json
import random
import numpy as np

DEFAULT_GENERATION_LIMIT = 500
DEFAULT_ITERATION_LIMIT = 100
DEFAULT_POPULATION_SIZE = 10


def run():
    target_metrics={}
    with open('config/target_metrics.json') as file:
        target_metrics=json.load(file)




    with open('config/parameters.json') as file:
        paras=json.load(file)
    if "generation_limit" in paras:
        generation_limit=paras["generation_limit"]
    else:
        generation_limit=DEFAULT_GENERATION_LIMIT
    if "iteration_limit" in paras:
        iter_limit=paras["iteration_limit"]
    else:
        iter_limit=DEFAULT_ITERATION_LIMIT
    if "population_size" in paras:
        population_size=paras["population_size"]
    else:
        population_size=DEFAULT_POPULATION_SIZE

    objectives=list(target_metrics.keys())
    #hyper parameters
    


    
    #Initilize
    layout=Layout()


    population=[init.init(layout) for _ in range(population_size)]





    bounds = {}
    for obj in objectives:
        vals = [ind[obj] for ind in EP_eva]
        bounds[obj] = {'min': min(vals), 'max': max(vals)}

    def get_normed_val(val, obj_bounds):
        denom = obj_bounds['max'] - obj_bounds['min']
        return (val - obj_bounds['min']) / denom if denom != 0 else 0

    # 2. Calculate a "Preference Score" for each individual
    # User input (e.g., {'cost': 1, 'speed': 5}) acts as the 'weights'
    scores = []
    for ind_eva in EP_eva:
        current_score = 0
        for obj in objectives:
            norm_val = get_normed_val(ind_eva[obj], bounds[obj])

            # Multiply the normalized value by the user's relative importance
            # If the goal is MINIMIZATION, lower score is better.
            current_score += target_metrics[obj] * norm_val

        scores.append(current_score)
    print('-\t'*10)
    # 3. Find the individual with the best (lowest) score
    min_indices = heapq.nsmallest(5, range(len(scores)),key=lambda idx: scores[idx])
    print("\t\tFINISHED!")
    print(f"5 LOWEST DISTANCES: {[round(scores[idx],2) for idx in min_indices]}")
    # print(EP[min_indices[0]])
    # print(EP_eva[min_indices[0]])
    for i,idx in enumerate(min_indices):
        layout.display(EP[idx],EP_eva[idx],name=f'top_{i+1}')




