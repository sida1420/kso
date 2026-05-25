import random
import math
from classes import Layout
import bisect



max_attempts=10
def CASH_pick(layout: Layout):
    r=random.random()*layout.cum_avai_strain_heapmap[-1]
    return layout.available_keys[bisect.bisect_left(layout.cum_avai_strain_heapmap,r)]

def binary_swap(ind, layout: Layout,threshold, max_attempts=10):
    n = len(ind)
    new_ind = ind[:]

    fixed_keys = layout.fixed_keys
    special_set = layout.avilable_skb_set
    base_end = layout.sizes[0]

    # Only permanently invalid positions are fixed keys.
    valid_indices = layout.available_keys

    if len(valid_indices) < 2:
        return new_ind

    # Build once: (special_position, counterpart_position) for current individual.
    special_cps ={}
    special_cps_inverse={}
    for kbi in range(base_end):
        if new_ind[kbi] in special_set:
            cp = layout.counterparts[kbi]
            if cp is not None:
                special_cps[kbi]= cp
                special_cps_inverse[cp]=kbi

    for i in valid_indices:
        if random.random() > threshold:
            continue
        kbi=new_ind[i]
        for _ in range(max_attempts):
            j = CASH_pick(layout)
            # j = random.choice(valid_indices)
            if i == j:
                continue

            kbj = new_ind[j]
            if kbi==kbj==None:
                continue
            

            ok = True
            si=False #i turns to special
            sj=False #j turns to special
            #bad slot
            if i in special_cps_inverse or j in special_cps_inverse:
                ok=False
            
                #special changes
            cpj=layout.counterparts[j]
            cpi=layout.counterparts[i]

            if i<base_end and kbi in special_set:
                if j>=base_end or (j<base_end and cpj is not None and new_ind[cpj] is not None):
                    ok=False
                elif i in special_cps:
                    special_cps_inverse.pop(special_cps[i])
                    special_cps.pop(i)
                sj=True
            if j<base_end and kbj in special_set:
                if i>=base_end or (i<base_end and cpi is not None and new_ind[cpi] is not None):
                    ok=False
                elif j in special_cps:
                    special_cps_inverse.pop(special_cps[j])
                    special_cps.pop(j)
                si=True
                    
            if not ok: continue
            
            new_ind[i], new_ind[j] = kbj, kbi
            if si and cpi is not None:
                special_cps[i]=cpi
                special_cps_inverse[cpi]=i
            if sj and cpj is not None:
                special_cps[j]=cpj
                special_cps_inverse[cpj]=j
            
            break

    return new_ind

def layer_swap(ind: list, layout: Layout,threshold: float):
    new_ind=ind[:]
    special_s=layout.avilable_skb_set
    for i in range(layout.sizes[0]):
        cp=layout.counterparts[i]
        if random.random()>threshold or i in layout.fixed_keys or cp is None or cp in layout.fixed_keys or new_ind[i] in special_s:
            continue
        
        new_ind[i], new_ind[cp]=new_ind[cp], new_ind[i]
    return new_ind

def physical_key_swap(ind: list, layout: Layout, threshold: float):
    new_ind=ind[:]

    special_s=layout.special_kb_set

        
def keystroke_swap(ind,layout): #I don't think this is possible
    pass


def mutate(ind,layout,T):
    
    # r=random.random()
    threshold = max(0.1*0.3+T*0.7, 1.0 / len(ind))

    if random.random()<0.9:
        ind=binary_swap(ind,layout,threshold) 
    else:
        ind=layer_swap(ind,layout,threshold)


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





if __name__ == "__main__":
    import init
    from evaluate import correct
    layout=Layout()
    init_layout=init.distributed_init(layout)
    while correct(init_layout, layout):
        print("hello")
        init_layout=binary_swap(init_layout,layout)
    print(init_layout)
    layout.display(init_layout)