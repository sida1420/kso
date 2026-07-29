import numpy as np
import random
from classes import *
import random
import json
class Parameters:
    def __init__(self):
            DEFAULT_GENERATION_LIMIT = 3000
            DEFAULT_POPULATION_SIZE = 10
            DEFAULT_DEV_MODE=False
            self.target_metrics={}
            file_name="target_metrics.json"
            try:
                with open(f'config/{file_name}') as file:
                    target_metrics=json.load(file)
            except json.JSONDecodeError as e:
                print(f"\nSYNTAX ERROR IN {file_name} FILE: {e}")
                raise SystemExit
            self.target_metrics=normalize_weights(target_metrics)
    

            with open('config/parameters.json') as file:
                paras=json.load(file)
            if "generation_limit" in paras:
                self.generation_limit=paras["generation_limit"]
            else:
                self.generation_limit=DEFAULT_GENERATION_LIMIT
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
    # 1. Score and sort positions (best first)
    scored = []
    for key_idx in layout.available_keys:
        finger_idx = layout.key_idx2finger_idx[key_idx]
        score = (
            layout.finger_efforts[finger_idx] *
            layout.key_sq_dists[key_idx][layout.home_keys[finger_idx]] *
            (1 if key_idx < layout.sizes[0] else 1.25) #1.25 is finetunable
        )
        scored.append((score, key_idx))
    scored.sort(key=lambda x: x[0])
    indices = [idx for _, idx in scored]

    # 2. Sort keybinds by probability descending
    keys = sorted(layout.available_keybinds, key=lambda x: layout.key_probs[x], reverse=True)

    # 3. Random swaps for diversity
    for i in range(len(keys)):
        if random.random() < 0.1:
            swap_idx = random.randint(0, len(keys) - 1)
            keys[i], keys[swap_idx] = keys[swap_idx], keys[i]

    
    res = [None] * len(layout.idx2key)
    remaining = list(keys)
    blocked = set()

    # 4. Greedy single pass: best position gets best compatible keybind
    for pos in indices:
        if len(remaining)==0:
            break
        if pos in blocked:
            continue

        chosen = None

        if pos >= layout.sizes[0]:
            # shift layer: take the best remaining non-universal and shift keybinds
            for i, kb in enumerate(remaining):
                if kb not in layout.universal_keybinds_set and kb not in layout.base_keybinds_set:
                    chosen = kb
                    remaining.pop(i)
                    break
        else:
            # base layer: take the best remaining keybind
            cp=layout.counterparts[pos]
            for i, kb in enumerate(remaining):
                if kb in layout.shift_keybinds_set:
                    continue
                if kb not in layout.universal_keybinds_set:
                    chosen = kb
                    remaining.pop(i)
                    break
                if kb in layout.universal_keybinds_set:
                    if cp is not None:
                        if cp in layout.fixed_keys:
                            continue
                        chosen=kb
                        remaining.pop(i)
                        blocked.add(cp)
                        break

        if chosen is not None:
            res[pos] = chosen


    # 5. Apply fixed keys
    for idx, kb in layout.fixed_keys.items():
        res[idx] = kb

    return res
def random_init(layout:Layout):
    #universal keybinds only take key indices from layer 1, and it shouldn't fixed in layer 2
    used_indices=random.sample([key_idx for key_idx in layout.layered_available_keys[0] if layout.counterparts[key_idx] not in layout.fixed_keys],
                                len(layout.available_ukb))

    used_indices_set=set(used_indices)
    used_keybinds_set=set(layout.available_ukb)
    for key_idx in used_indices:
        key=layout.idx2key[key_idx]
        if key in layout.key2idx[1]:
            used_indices_set.add(layout.key2idx[1][key])

    res=[None]*len(layout.idx2key)
    for i,keybind_idx in enumerate(layout.available_ukb):
        res[used_indices[i]]=keybind_idx

    #base layer keybinds
    new_ABK=[key_idx for key_idx in range(layout.sizes[0]) if key_idx not in used_indices_set and key_idx not in layout.fixed_keys]
    new_ABKB=[keybind_idx for keybind_idx in layout.available_bkb]
    
    indices=random.sample(new_ABK,len(new_ABK))
    keys=random.sample(new_ABKB,len(new_ABKB))
    used_keybinds_set.update(keys)

    for idx,key in zip(indices,keys):
        used_indices_set.add(idx)
        res[idx]=key

    #shift layer keybinds
    new_ASK=[key_idx for key_idx in range(layout.sizes[0],layout.sizes[0]+layout.sizes[1]) if key_idx not in used_indices_set and key_idx not in layout.fixed_keys]
    new_ASKB=[keybind_idx for keybind_idx in layout.available_skb]
    indices=random.sample(new_ASK,len(new_ASK))
    keys=random.sample(new_ASKB,len(new_ASKB))
    used_keybinds_set.update(keys)
    for idx,key in zip(indices,keys):
        used_indices_set.add(idx)
        res[idx]=key
    
    #left over keybinds
    new_AK=[key_idx for key_idx in layout.available_keys if key_idx not in used_indices_set]
    new_AKB=[keybind_idx for keybind_idx in layout.available_keybinds if keybind_idx not in used_keybinds_set]
    indices=random.sample(new_AK,len(new_AKB))
    keys=random.sample(new_AKB,len(new_AKB))

    for idx,key in zip(indices,keys):
        res[idx]=key
    for i,j in layout.fixed_keys.items():
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

    weight_vecs=list(samples)

    sorted_vecs=[weight_vector]

    while weight_vecs:
        min_i=np.argmin([np.linalg.norm(sorted_vecs[-1]-v) for v in weight_vecs])
        sorted_vecs.append(weight_vecs[min_i])
        weight_vecs[min_i], weight_vecs[-1]=weight_vecs[-1], weight_vecs[min_i]
        weight_vecs.pop()

    return sorted_vecs



def init(population_size: int, layout: Layout):
    # ind=distributed_init(layout)
    return [distributed_init(layout) for _ in range(population_size)]



if __name__=='__main__':
    from evaluate import Evaluator
    layout=Layout()
    e=Evaluator(layout)
    n=100    
    init_layout=random_init(layout)
    while e.correct(init_layout)[0] and n>0:
        print("hello")
        init_layout=random_init(layout)
        n-=1

    print(init_layout)
    layout.display(init_layout)
    print(init_weight_vectors({1:10,3:10,2:10},10))
    