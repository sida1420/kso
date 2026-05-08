
import random
from classes import Layout, Vector
import random

'''
'''
def distributed_init(layout: Layout):

    indices=[]
    scores={}
    for key_idx in layout.available_keys:
        if key_idx in layout.fixed_keys:
            continue
        indices.append(key_idx)
        finger_idx=layout.key_idx2finger_idx[key_idx]
        scores[key_idx] = layout.finger_costs[finger_idx]*layout.key_sq_dists[key_idx][layout.home_keys[finger_idx]]

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

def init(population_size: int, layout: Layout):
    ind=random_init(layout)
    return [ind.copy() for _ in range(population_size)]


if __name__=='__main__':
    l=Layout()
    i=distributed_init(l)
    print(i)
    l.display(i)
