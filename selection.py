import random

def dominate(eva1, eva2, objectives):
    count=0
    for key in objectives:
        if eva1[key]>eva2[key]:
            return False
        if eva1[key]<eva2[key]:
            count+=1
    return count>0
import evaluate

def update_EP(offsprings,offspring_eva, EP, EP_eva, objectives):
    new_EP=[]
    new_EP_eva=[]
    removed=set()

    existing_signatures = set(tuple(eva[obj] for obj in objectives) for eva in EP_eva)

    for i in range(len(offsprings)):
        sig = tuple(offspring_eva[i][obj] for obj in objectives)

        if sig in existing_signatures:
            continue

        non_dominated=True
        for j in range(len(EP)):
            if j in removed:
                continue
            if dominate(offspring_eva[i],EP_eva[j],objectives):
                removed.add(j)
            elif dominate(EP_eva[j],offspring_eva[i],objectives):
                non_dominated=False
                break

        if non_dominated:
            new_EP.append(offsprings[i])
            new_EP_eva.append(offspring_eva[i])
            existing_signatures.add(sig)

    for j in range(len(EP)):
        if j in removed:
            continue
        new_EP.append(EP[j])
        new_EP_eva.append(EP_eva[j])

    return (new_EP,new_EP_eva)


def selection(weights, population, evas, offsprings, offspring_eva, neighbours, gbips,objectives, reference, replace_limit):
    #e, n, s
    n=len(population)

    for i in range(n):
        local_neighs=neighbours[i]
        replace_count=0
        for ind_idx in local_neighs:

            neigh_gbip=gbips[ind_idx]
            offspring_gbip=evaluate.gbip(weights[ind_idx],offspring_eva[i],reference,2,objectives)

            if offspring_gbip<neigh_gbip:
                replace_count+=1
                #replace
                population[ind_idx]=offsprings[i].copy()
                evas[ind_idx]=offspring_eva[i]
                gbips[ind_idx]=offspring_gbip

                if replace_count==replace_limit:
                    break



    return (population,evas,gbips)

        