import numpy as np
import random
from classes import *
import random
import json
class Parameters:
    def __init__(self):
            DEFAULT_GENERATION_LIMIT = 1000
            DEFAULT_ITERATION_LIMIT = 500
            DEFAULT_POPULATION_SIZE = 10
            DEFAULT_DEV_MODE=False
            self.target_metrics={}
            with open('config/target_metrics.json') as file:
                target_metrics=json.load(file)
            self.target_metrics=normalize_weights(target_metrics)
    

            with open('config/parameters.json') as file:
                paras=json.load(file)
            if "generation_limit" in paras:
                self.generation_limit=paras["generation_limit"]
            else:
                self.generation_limit=DEFAULT_GENERATION_LIMIT
            if "iteration_limit" in paras:
                self.iteration_limit=paras["iteration_limit"]
            else:
                self.iteration_limit=DEFAULT_ITERATION_LIMIT
            if "population_size" in paras:
                self.population_size=paras["population_size"]
            else:
                self.population_size=DEFAULT_POPULATION_SIZE
            if "dev_mode" in paras:
                self.dev_mode=paras["dev_mode"]
            else:
                self.dev_mode=DEFAULT_DEV_MODE



'''
'''
def distributed_init(layout: Layout):

    indices=[]
    scores={}
    for key_idx in layout.available_keys:
        if key_idx in layout.fixed_keys and key_idx!=layout.chat_i:
            continue
        indices.append(key_idx)
        finger_idx=layout.key_idx2finger_idx[key_idx]
        scores[key_idx] = layout.finger_efforts[finger_idx]*layout.key_sq_dists[key_idx][layout.home_keys[finger_idx]]

    indices.sort(key=lambda x:scores[x])

    keys=sorted(layout.available_keybinds, key=lambda x: layout.key_probs[x],reverse=True)


    for i in range(len(keys)):
        if random.random()<0.1:
            swap_idx=random.randint(0,len(keys)-1)
            keys[i],keys[swap_idx]=keys[swap_idx],keys[i]
    
    res=[None]*len(layout.idx2key)
    for idx,key in zip(indices,keys):
        res[idx]=key
    for i,j in layout.fixed_keys.items():
        if i==layout.key2idx[layout.chat]:
            continue
        res[i]=j
    return res




def random_init(layout:Layout):
    indices=random.sample(layout.available_keys,len(layout.available_keys))
    keys=random.sample(layout.available_keybinds,len(layout.available_keybinds))

    res=[None]*len(layout.idx2key)
    for idx,key in zip(indices,keys):
        res[idx]=key
    for i,j in layout.fixed_keys.items():
        if i==layout.key2idx[layout.chat]:
            continue
        res[i]=j
    return res

def normalize_weights(target_metrics):
    total_weight=sum(target_metrics.values())
    if total_weight==0:
        return
    return {name:value/total_weight for name, value in target_metrics.items()}

def init_temperature(population_size:int, min_T:float, max_T:float):
    step=(max_T/min_T)**(1/(population_size-1))
    res=[min_T]
    for i in range(1,population_size-1):
        res.append(res[-1]*step)
    res.append(max_T)
    return res

def init_weight_vectors(target_metrics, population_size:int, concentration=10.0 ):
    target_metrics=normalize_weights(target_metrics)

    weight_vector=np.array(list(target_metrics.values()))

    alpha=weight_vector*concentration

    samples=np.random.dirichlet(alpha, size=population_size-1)



    weight_vecs=list(samples)+[weight_vector]



    distances=[np.linalg.norm(weight_vector-v) for v in weight_vecs]

    return [v for _,v in sorted(zip(distances,weight_vecs))]



def init(population_size: int, layout: Layout):
    # ind=distributed_init(layout)
    return [distributed_init(layout) for _ in range(population_size)]


if __name__=='__main__':
    # layout=Layout()
    # init_layout=distributed_init(layout)
    # print(init_layout)
    # layout.display(init_layout)
    # print(init_temperature(10, 2, 20))
    print(init_weight_vectors({"a":5,"6":3,"5":1},5))