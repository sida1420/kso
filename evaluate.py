import random
import math
from classes import *
import copy

def normalize(ind):
    return ind

def finger_cost(ind, layout):
    res = 0
    for i, j in enumerate(ind):
        if j is None:
            continue
        finger_idx = layout.key_idx2finger_idx[i]
        
        # CPU Optimization: Used distance_sq instead of distance()**2
        
        anchor_dist_sq = layout.key_sq_dists[i][layout.home_keys[finger_idx]]
        res += layout.finger_costs[finger_idx] * layout.key_probs[j] * anchor_dist_sq
    return res


def compute_FMC(finger_cost, sq_dist, time, prev_time):
    return (
        finger_cost
        *sq_dist
        /(time-prev_time+1)**1.5
    )


#finger distance(prefer low distanece, original natural distane)
def compute_FDC(key_i_pos, key_j_pos, natural_i, natural_j, finger_dist, finger_cost_i, finger_cost_j):
    return (
        (   
            ((key_i_pos.y-key_j_pos.y)-(natural_i.y-natural_j.y))**2
            +((key_i_pos.x-key_j_pos.x)-(natural_i.x-natural_j.x))**2
        )
        /finger_dist**2
        *finger_cost_i
        *finger_cost_j
    )


def FDC_full(layout, finger_tasks, order, hand_code, cache): #finger_tasks only have 1 value for key_idx, not the time and count, since it's only used for initialization
    res=0
    for finger_i in order: #THIS USE FINGER CODE AND HAND CODE AS INDEX SYSTEM (SAME WITH FINGER_CODE, HAND_CODE) NOT THE FINGER_IDX SYSTEM (SAME WITH finger2idx)
        finger_idx_i=layout.get_finger_idx(hand_code, finger_i) #REVERT BACK TO FINGER_IDX SYSTEM FOR FINGER COST
        key_i=layout.idx2key[finger_tasks[finger_idx_i]]
        natural_i=layout.finger_natural_pos[finger_idx_i]
        for finger_j in order:
            if finger_j<=finger_i:
                continue
            finger_idx_j=layout.get_finger_idx(hand_code, finger_j) #REVERT
            key_j=layout.idx2key[finger_tasks[finger_idx_j]]
            natural_j=layout.finger_natural_pos[finger_idx_j]
            cost=compute_FDC(
                layout.keys[key_i].fpos,
                layout.keys[key_j].fpos,
                natural_i,
                natural_j,
                layout.finger_dists[(finger_i,finger_j)], #FINGER DISTANCE USE FINGER CODE AS INDEX SYSTEM
                layout.finger_costs[finger_idx_i],
                layout.finger_costs[finger_idx_j]
            )
            cache[hand_code][(finger_i,finger_j)]=cost

            res+=cost
    return res

def FDC_partial(layout, finger_tasks, finger_i, finger_idx_i, order, hand_code, old_res, cache):
    key_i=layout.idx2key[finger_tasks[finger_idx_i][0]]
    natural_i=layout.finger_natural_pos[finger_idx_i]
    res=old_res
    for finger_j in order:
        if finger_i==finger_j:
            continue
        finger_idx_j=layout.get_finger_idx(hand_code, finger_j) #REVERT
        key_j=layout.idx2key[finger_tasks[finger_idx_j][0]]
        natural_j=layout.finger_natural_pos[finger_idx_j]
        
        order_pair=(min(finger_i,finger_j),max(finger_i,finger_j))

        res-=cache[hand_code][order_pair]
        cost=compute_FDC(
            layout.keys[key_i].fpos,
            layout.keys[key_j].fpos,
            natural_i,
            natural_j,
            layout.finger_dists[(finger_i,finger_j)],
            layout.finger_costs[finger_idx_i],
            layout.finger_costs[finger_idx_j]
        )
        cache[hand_code][order_pair]=cost
        res+=cost
    return res


def sequence_costs(ind, layout:Layout):
    finger_movement_cost=0
    roll_cost=0
    use_count_cost=0
    finger_dist_cost=0

    keybind_idx2key_idx={j:i for i,j in enumerate(ind) if j is not None}


    #const

    for keystroke_n_weight in layout.keystrokes:
        keystroke=keystroke_n_weight[0]
        weight=keystroke_n_weight[1]
        #finger: [key_idx, last_used, use_count]
        finger_tasks={finger_idx:[key_idx,-1,0] for finger_idx, key_idx in layout.home_keys.items()}
        
        #assume 1 finger is pressing chat
        finger_tasks[layout.key_idx2finger_idx[layout.chat_i]][0]=layout.chat_i

        local_finger_movement_cost=0 #base cost
        local_roll_cost=0

        #inititize for roll
        roll_state=-1
        consecutive_roll=0
        prev_hand_code, prev_finger_code=layout.get_finger_roll(layout.key_idx2finger_idx[layout.chat_i])

        FDC_cache=copy.deepcopy(layout.initial_FDC_cache) #cache for FDC calculation, index by hand code, key is (finger_i, finger_j) with finger code as index system, value is the FDC cost between the two fingers
        current_FDC_total=layout.initial_FDC_total
        local_finger_dist_cost=0  # accumulate over time

        for time, keybind_idx in enumerate(keystroke):
            key_idx=keybind_idx2key_idx[keybind_idx]
            press_finger=layout.key_idx2finger_idx[key_idx]
            #increase use_count
            finger_tasks[press_finger][2]+=1

            prev_key_idx=finger_tasks[press_finger][0]
            prev_time=finger_tasks[press_finger][1]
            #finger_cost*distance**2/(moving_time+press_time)**1.5
            #TODO: fine-tuning
            local_finger_movement_cost+=compute_FMC(
                layout.finger_costs[press_finger],
                layout.key_sq_dists[key_idx][prev_key_idx],
                time,
                prev_time
            )

            hand_code, finger_code=layout.get_finger_roll(press_finger)
            

            #roll handling
            #inward roll
            #outward roll
            #redirect
            if prev_hand_code!=hand_code: #different hand
                roll_state=-1
                consecutive_roll=0
            else:
                # Determine the current direction of the fingers
                if finger_code > prev_finger_code: current_dir = 2     # Inward
                elif finger_code < prev_finger_code: current_dir = 1   # Outward
                else: current_dir = 0                            # Same finger



                if current_dir!=roll_state and roll_state!=-1: #redirect
                    local_roll_cost += layout.finger_costs[press_finger] * 2
                    consecutive_roll = 1
                else:
                    consecutive_roll+=1
                    if current_dir==2:
                        local_roll_cost -= consecutive_roll*2/layout.finger_costs[press_finger]
                    elif current_dir==1:
                        local_roll_cost -= consecutive_roll/layout.finger_costs[press_finger]
                    elif current_dir==0:
                        local_roll_cost += layout.finger_costs[press_finger]*consecutive_roll*2

                
                roll_state=current_dir
            prev_hand_code=hand_code
            prev_finger_code=finger_code



            #update
            finger_tasks[press_finger][0]=key_idx            
            finger_tasks[press_finger][1]=time

            
            current_FDC_total=(
                FDC_partial(layout,finger_tasks, finger_code, press_finger, layout.hand[hand_code], hand_code, current_FDC_total, FDC_cache)
            )
            local_finger_dist_cost += current_FDC_total


        #cost of moving all finger back to home row
        #only calculate if finger need to move
        time=len(keystroke)
        for finger, key_idx_n_time_n_count in finger_tasks.items():
            prev_key_idx=key_idx_n_time_n_count[0]
            prev_time=key_idx_n_time_n_count[1]

            key_idx=layout.home_keys[finger]
            if prev_key_idx==key_idx:
                continue
            local_finger_movement_cost+=compute_FMC(
                layout.finger_costs[finger],
                layout.key_sq_dists[key_idx][prev_key_idx],
                time,
                prev_time
            )
        

        #use count
        local_use_count_cost=0
        for finger, key_idx_n_time_n_count in finger_tasks.items():
            #count*fingercost
            local_use_count_cost+=(
                key_idx_n_time_n_count[2]**2
                *layout.finger_costs[finger]
            )
        

        use_count_cost+=local_use_count_cost*weight
        finger_movement_cost+=local_finger_movement_cost*weight
        roll_cost+=local_roll_cost*weight
        finger_dist_cost+=local_finger_dist_cost*weight
    return finger_movement_cost, use_count_cost, roll_cost, finger_dist_cost


if __name__ == '__main__':
    from init import distributed_init
    l=Layout()
    i=distributed_init(l)
    l.display(i)
    print(sequence_costs(i,l))


def evaluate(population, layout):

    evas=[]
    for i in range(len(population)):
        finger_movement_cost, use_count_cost, roll_cost, finger_dist_cost=sequence_costs(population[i],layout)
        eva={
            "finger_cost":finger_cost(population[i],layout),
            "movement_cost":finger_movement_cost,
            "use_count_cost":use_count_cost,
            "roll_cost": roll_cost,
            "distance_cost": finger_dist_cost
            }
        evas.append(eva)

    return evas

# target=[Point(0,0.5),Point(0.5,0.5),Point(0.6,0.5),Point(1,0.5)]
# print(evaluate([[1,0,0,0,0,0,0,0,0,0],],target))

