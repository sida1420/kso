

import heapq
import init
import selection
import classes
import evaluate
import random
import numpy as np
import mutation
import heapq




def run():
    paras=init.Parameters()

    objectives=list(paras.target_metrics.keys())

    #hyper parameters
    min_T=0.015
    max_T=0.7
    n_swaps=11 #Always odd

    #Initilize
    layout=classes.Layout()

    if paras.population_size<1:
        return

    temperatures=init.init_temperature(paras.population_size, min_T, max_T)

    replicas=init.init(paras.population_size, layout)

    weight_vectors=init.init_weight_vectors(paras.target_metrics,paras.population_size, 15)


    evaluations=evaluate.vector_evas(replicas, layout)


    dynamic_min = [min(e[i] for e in evaluations) for i in range(len(objectives))]
    dynamic_max = [max(e[i] for e in evaluations) for i in range(len(objectives))]

    scaled_evals = [evaluate.apply_scale(e, dynamic_min, dynamic_max) for e in evaluations]

    scores=[evaluate.weighted_sum_scaled(scaled_evals[i], weight_vectors[i]) for i in range(paras.population_size)]

    elites=[(scores[0],evaluations[0],replicas[0]),]
    num_elites=5

    # Static ranges from initial population (never change again)



    total_jump_accept=np.zeros(paras.population_size)
    total_swap_accept=np.zeros(paras.population_size-1)
    total_better_jumps=np.zeros(paras.population_size)

    range_changed=False

    generation_count=0
    log_range=1
    while generation_count<paras.generation_limit:
        generation_count+=1
        if generation_count%log_range==0 or paras.dev_mode==True:
            if generation_count>=log_range*10:
                log_range*=10
            print(f"\tGENERATION {generation_count}")
        

        #Canditates for new replicas generation
        candidates=[]
        for i in range(paras.population_size):
            if i<paras.population_size-1 and random.random()<0.05:
                candidates.append(mutation.cycle_crossover(replicas[i], replicas[i+1]))
            else:
                candidates.append(mutation.mutate(replicas[i],layout))

        candidate_evaluations=evaluate.vector_evas(candidates, layout)


        range_changed=evaluate.update_global(dynamic_min, candidate_evaluations, 'min')
        range_changed=evaluate.update_global(dynamic_max, candidate_evaluations, 'max') or range_changed


        scaled_candidate_evals = [evaluate.apply_scale(e, dynamic_min, dynamic_max) for e in candidate_evaluations]
        candidate_scores=[evaluate.weighted_sum_scaled(scaled_candidate_evals[i], weight_vectors[i]) for i in range(paras.population_size)]
        if range_changed:
            scaled_evals = [evaluate.apply_scale(e, dynamic_min, dynamic_max) for e in evaluations]
            scores=[evaluate.weighted_sum_scaled(scaled_evals[i], weight_vectors[i]) for i in range(paras.population_size)]
            scaled_elite_evals = [evaluate.apply_scale(e, dynamic_min, dynamic_max) for _,e,_ in elites]
            elites=[(evaluate.weighted_sum_scaled(scaled_elite_evals[i],weight_vectors[0]),elites[i][1], elites[i][2]) for i in range(len(elites))]

        range_changed=False

        replicas, evaluations, scores, elites, jump_accept, better_jumps = selection.selection(temperatures, replicas, evaluations, scores, candidates, candidate_evaluations, candidate_scores, elites, num_elites, paras.population_size,generation_count)

        if generation_count % n_swaps == 0:
            replicas, evaluations, scores, swap_accept = mutation.swap_replicas(temperatures, replicas, evaluations, scores, generation_count)
            total_swap_accept += swap_accept
            if paras.dev_mode==True:
                print(f"SWAP ACCEPTED: {swap_accept}")

        total_jump_accept += jump_accept
        total_better_jumps += better_jumps

        if paras.dev_mode==True:
            print(f"JUMP ACCEPTED: {jump_accept}")
            print(f"IDEA POINT: {[round(float(v),2) for v in dynamic_min]}")
        if generation_count%log_range==0    or paras.dev_mode==True:
            print(f"BEST SCORE: {round(min(elites, key=lambda e: e[0])[0],3)}")

    print('-\t'*10)
    print("\tFINISHED!")

    if paras.dev_mode==True:
        for i, replica in enumerate(replicas):
            layout.display(replica, zip(objectives,evaluations[i]), name=f'replica_{i}')
    
    objective_str=""
    for obj in objectives:
        objective_str+=f"{obj}\t"
    print(f"\tSCORE\t{objective_str}")
    for i,elite in enumerate(sorted(elites,key=lambda e: e[0])):
        score_str=""
        for v in elite[1]:
            score_str+=f"{round(v,3)}\t\t"
        print(f"RANK {i+1}:\t{round(elite[0],3)}\t{score_str}\n")
        layout.display(elite[2], zip(objectives,elite[1]), name=f'top_{i+1}')

    if paras.dev_mode==True:
        print(f"SWAP ACCEPTANCE RATE:  {total_swap_accept/paras.generation_limit*n_swaps/2}")
        print(f"JUMP ACCEPTANCE RATE:  {total_jump_accept/(paras.generation_limit-total_better_jumps)}")
        print(f"BETTER JUMPS RATE:  {total_better_jumps/paras.generation_limit}")


if __name__ == '__main__':
    run()
