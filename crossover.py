
import random

from classes import Layout
import mutation


# def random_position(p1, p2):
#     n=random.randint(1,len(p2)-1)

#     indices=random.sample(range(len(p2)),k=n)

#     child=p1.copy()

#     for i in indices:
#         child[i]=p2[i]

#     return child

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


# from Init import init
# l=Layout()
# i=init(l)
# j=init(l)
# # print([[x,y] for x,y in enumerate(i)])
# # print([[x,y] for x,y in enumerate(j)])
# l.display(cycle_crossover(i,j))

    

        


    

    
def crossover(population, neighbours, layout):

    offsprings=[]
    

    for idx in range(len(population)):
        p1i=random.randint(0,len(neighbours[idx])-1)
        p2i=random.randint(0,len(neighbours[idx])-1)
        p1=population[neighbours[idx][p1i]]
        p2=population[neighbours[idx][p2i]]

        child=cycle_crossover(p1,p2)

        if random.random()<0.5:
            child=mutation.mutate(child,layout)

        offsprings.append(child)
    return offsprings

