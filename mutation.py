import random

from classes import Layout

def binary_swap(ind,layout):
    for i in range(len(ind)):
        if i in layout.fixed_keys:
            continue
        if random.random()>0.1:
            continue
        j=random.randrange(0,len(ind))
        while j in layout.fixed_keys:
            j=random.randrange(0,len(ind))  
        ind[i], ind[j]= ind[j], ind[i]
    return ind

def mutate(ind,layout):
    
    r=random.random()

    ind=binary_swap(ind,layout)


    return ind
