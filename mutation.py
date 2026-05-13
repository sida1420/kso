import random
import math
from classes import Layout
max_attempts=10


def binary_swap(ind,layout):
    new_ind=ind[:]
    threshold=max(0.2, 1/len(ind))
    for i in range(len(ind)):
        if (i in layout.fixed_keys and i!=layout.chat_i) or random.random()>threshold:
            continue
        j=random.randrange(len(ind))
        attempts=0
        while j in layout.fixed_keys  and j!=layout.chat_i:
            if attempts>max_attempts:
                break
            j=random.randrange(len(ind))
            attempts+=1
        if attempts>max_attempts:
            continue

        new_ind[i], new_ind[j] = new_ind[j], new_ind[i]
    return new_ind
def keystroke_swap(ind,layout):
    pass

def mutate(ind,layout):
    
    # r=random.random()

    ind=binary_swap(ind,layout)


    return ind

import numpy as np
def swap_replicas(temperatures, replicas, evaluations, scores, generation_count):
    start_idx=generation_count%2
    accept_count=np.zeros(len(replicas)-1)
    for i in range(start_idx, len(replicas)-1, 2):
        delta_beta=1.0/temperatures[i]-1.0/temperatures[i+1]
        delta_score=scores[i]-scores[i+1]
        arg = max(-700.0, min(700.0, delta_beta*delta_score))
        if random.random()<min(1, math.exp(arg)):
            accept_count[i]+=1
            #swap
            replicas[i], replicas[i+1] = replicas[i+1], replicas[i]
            evaluations[i], evaluations[i+1] = evaluations[i+1], evaluations[i]
            scores[i], scores[i+1] = scores[i+1], scores[i]
    
    return replicas, evaluations, scores, accept_count


from collections import defaultdict
def cycle_crossover(p1,p2):
    size=len(p1)
    child=[-1]*size

    left_most=0
    
    p1_lookup=defaultdict(list)

    for i, j in enumerate(p1):
        p1_lookup[j].append(i)

    val_count=defaultdict(int)

    idx_map = [0]* size
    for i,j in enumerate(p2):
        occurrence=val_count[j]

        idx_map[i]=p1_lookup[j][occurrence]
        val_count[j]+=1

    use_p1=True
    while left_most<size:
        if child[left_most]==-1:
            cur=left_most
            
            while True:
                child[cur]=p1[cur] if use_p1 else p2[cur]
                cur=idx_map[cur]
                if cur==left_most:
                    break
            use_p1=not use_p1


        left_most+=1
    return child
