import random
import heapq
import math
import numpy as np
from evaluate import apply_scale

def selection(temperatures, replicas, evaluations, scores, candidates, candidate_evaluations, candidate_scores, elites, num_elites, population_size, generation_count):
    accept_count= np.zeros(population_size)
    better_count=np.zeros(population_size)
    for i in range(population_size):
        
        accept=False

        if candidate_scores[i]<=scores[i]:
            # print(f"Candidate {i} accepted: {candidate_scores[i]} <= {scores[i]}")
            # print(f"{candidate_evaluations[i]} vs {evaluations[i]}")
            accept=True
            better_count[i]+=1
        else:
            if random.random()<min(1, math.exp(-(candidate_scores[i]-scores[i])/temperatures[i])):
                # print(f"Candidate {i} accepted (probabilistically): {candidate_scores[i]} > {scores[i]}")
                # print(f"{candidate_evaluations[i]} vs {evaluations[i]}")
                accept_count[i]+=1
                accept=True
        
        if accept:
            replicas[i]=candidates[i]
            evaluations[i]=candidate_evaluations[i]
            scores[i]=candidate_scores[i]

            #update elites
            entry=(scores[i], evaluations[i], replicas[i])
            dominated_elites=[]
            dominated=False

            ma=0
            for j in range(len(elites)):
                if elites[j][0]>elites[ma][0]:
                    ma=j
            
            if len(elites)<num_elites:
                elites.append(entry)
            elif scores[i]<elites[ma][0]: elites[ma]=entry
            

    return replicas, evaluations, scores, elites, accept_count, better_count


