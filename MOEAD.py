

import heapq
import init
import selection
import crossover
import time
from classes import Point
from classes import Layout
import evaluate
import json


def run():
    target_metrics={}
    with open('config/target_metrics.json') as file:
        target_metrics=json.load(file)


    iter_limit=500

    with open('config/parameters.json') as file:
        paras=json.load(file)
    if "generation_limit" in paras:
        iter_limit=paras["generation_limit"]

    objectives=list(target_metrics.keys())
    #hyper parameters
    
    num_divisions=3
    num_objectives=len(objectives)
    num_neighbours=5
    replace_limit=3
    
    #Initilize
    layout=Layout()
    # print("a")
    weights=init.init_weight_vectors(num_divisions,num_objectives)

    popu_size=len(weights)
    print(popu_size)
    population=[init.init(layout) for i in range(popu_size)]
    # print("c")
    neighbours=[init.who_am_i_neighbour(i,weights,num_neighbours) for i in range(popu_size)]
    # print("d")
    evas=evaluate.evaluate(population,layout)
    # print("e")

    reference=init.init_reference_point(evas,objectives)

    gbips=[evaluate.gbip(weights[i],evas[i],reference, 2, objectives) for i in range(popu_size)]

    offsprings=crossover.crossover(population,neighbours,layout)
    offspring_evas=evaluate.evaluate(offsprings,layout)

    EP=[]
    EP_eva=[]

    iter_count=0
    while(iter_count<iter_limit):
        iter_count+=1
        print(f"\t GEN: {iter_count}")

        reference=evaluate.update_ref(offspring_evas,reference,objectives)
        gbips=[evaluate.gbip(weights[i],evas[i],reference, 2, objectives) for i in range(popu_size)]
        EP, EP_eva=selection.update_EP(offsprings,offspring_evas,EP,EP_eva,objectives)
        population, evas, gbips=selection.selection(weights,population,evas,offsprings,offspring_evas,neighbours,gbips,objectives,reference, replace_limit)

        offsprings=crossover.crossover(population,neighbours,layout)
        offspring_evas=evaluate.evaluate(offsprings,layout)

        # Visual.distribution(EP,target)
        print(f"Idea metrics: {reference}")
        print(population[0])
        print(offsprings[0])
        temp=""
        for key, value in evas[0].items():
            temp+=f"{key}: {round(value,2)} "
        print(temp)

    # Visual.fronts(EP, EP_eva)
    # for i in range(len(EP)):
    #     print(EP[i])
    #     print(EP_eva[i])


    import numpy as np

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




