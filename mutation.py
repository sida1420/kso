import random
import math
from classes import Layout
import bisect

class Mutator:

    def __init__(self, layout: Layout):
        self.layout=layout
        self.max_attempts=10
        self.n=len(layout.idx2key)
        self.fixed_keys=layout.fixed_keys
        self.universal_keybinds_set=layout.universal_keybinds_set
        self.base_keybinds_set=layout.base_keybinds_set
        self.shift_keybinds_set=layout.shift_keybinds_set
        self.base_end=layout.sizes[0]
        self.valid_indices=layout.available_keys
        self.counterparts=layout.counterparts
    
    def CASH_pick(self):
        r=random.random()*self.layout.cum_avai_strain_heapmap[-1]
        return self.layout.available_keys[bisect.bisect_left(self.layout.cum_avai_strain_heapmap,r)]

    def binary_swap(self, ind: list,threshold: float):

        new_ind = ind[:]

        if len(self.valid_indices) < 2:
            return new_ind

        # Build once: (universal_position, counterpart_position) for current individual.
        universal_cps ={}
        universal_cps_inverse={}
        for key_index in range(self.base_end):
            if new_ind[key_index] in self.universal_keybinds_set:
                cp = self.layout.counterparts[key_index]
                if cp is not None:
                    universal_cps[key_index]= cp
                    universal_cps_inverse[cp]=key_index

        for i in self.valid_indices:
            if random.random() > threshold:
                continue
            kbi=new_ind[i]
            for _ in range(self.max_attempts):
                j = self.CASH_pick()
                # j = random.choice(valid_indices)
                if i == j:
                    continue

                kbj = new_ind[j]
                if kbi==kbj==None:
                    continue
                

                si=False #i turns to special
                sj=False #j turns to special
                #bad slot
                if i in universal_cps_inverse or j in universal_cps_inverse:
                    continue

                #special changes
                cpi=self.counterparts[i]
                cpj=self.counterparts[j]

                if (kbi in self.base_keybinds_set and j>=self.base_end) or (kbj in self.base_keybinds_set and i>=self.base_end):
                    continue
                if (kbi in self.shift_keybinds_set and j<self.base_end) or (kbj in self.shift_keybinds_set and i<self.base_end):
                    continue
                if i<self.base_end and kbi in self.universal_keybinds_set:
                    if (j>=self.base_end or (j<self.base_end and cpj is not None and new_ind[cpj] is not None)):
                        continue
                    if i in universal_cps:
                        universal_cps_inverse.pop(universal_cps[i])
                        universal_cps.pop(i)
                    sj=True
                if j<self.base_end and kbj in self.universal_keybinds_set:
                    if i>=self.base_end or (i<self.base_end and cpi is not None and new_ind[cpi] is not None):
                        continue
                    elif j in universal_cps:
                        universal_cps_inverse.pop(universal_cps[j])
                        universal_cps.pop(j)
                    si=True

                new_ind[i], new_ind[j] = kbj, kbi
                if si and cpi is not None:
                    universal_cps[i]=cpi
                    universal_cps_inverse[cpi]=i
                if sj and cpj is not None:
                    universal_cps[j]=cpj
                    universal_cps_inverse[cpj]=j

                break

        return new_ind

    def layer_swap(self, ind: list,threshold: float):
        new_ind=ind[:]
        for i in range(self.base_end):
            cp=self.layout.counterparts[i]
            if random.random()>threshold or i in self.fixed_keys or cp is None or cp in self.fixed_keys or new_ind[i] in self.universal_keybinds_set or new_ind[i] in self.base_keybinds_set or new_ind[cp] in self.shift_keybinds_set:
                continue
            
            new_ind[i], new_ind[cp]=new_ind[cp], new_ind[i]
        return new_ind

    def physical_key_swap(self, ind: list, threshold: float):
        new_ind=ind[:]

        
        #TODO



    def mutate(self,ind, T):

        # r=random.random()
        threshold = max(0.1*0.3+T*0.7, 1.0 / len(ind))

        if random.random()<0.9:
            ind=self.binary_swap(ind,threshold) 
        else:
            ind=self.layer_swap(ind, threshold)


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
    # from evaluate import correct
    layout=Layout()
    init_layout=init.distributed_init(layout)
    m=Mutator(layout)
    # while correct(init_layout, layout):
        # print("hello")
    layout.display(init_layout,name="Initial Layout")
    init_layout=m.binary_swap(init_layout,0.1)
    print(init_layout)
    layout.display(init_layout,name="After Binary Swap")