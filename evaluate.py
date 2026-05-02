import random
import math
from classes import Layout



def normalize(ind):
    return ind

def distance_sq(pos1, pos2):
    x=(pos1.x-pos2.x)*1.25
    y=pos1.y-pos2.y
    return x**2+y**2

def distance(pos1, pos2):
    return math.sqrt(distance_sq(pos1, pos2))

def finger_cost(ind, layout):
    res = 0
    for i, j in enumerate(ind):
        if j is None:
            continue
        finger = layout.idx2finger[i]
        
        # CPU Optimization: Used distance_sq instead of distance()**2
        anchor_dist_sq = distance_sq(
            layout.keys[layout.idx2key[i]].fpos, 
            layout.keys[layout.idx2key[layout.home_keys[finger]]].fpos
        )
        res += layout.finger_costs[finger] * layout.prob[j] * anchor_dist_sq
    return res


def compute_FMC(finger_cost, pos, prev_pos, time, prev_time):
    return (
        finger_cost
        *distance_sq(prev_pos,pos)
        /(time-prev_time+1)**1.5
    )


def sequence_costs(ind, layout:Layout):
    finger_movement_cost=0
    roll_cost=0
    use_count_cost=0
    finger_dist_cost=0

    keybind_idx2key_idx={j:i for i,j in enumerate(ind)}


    #const
    finger_code={finger:layout.get_finger_roll(finger) for finger in layout.home_keys}
    left_hand_order=sorted([finger for finger in layout.home_keys if finger_code[finger][0]==0],key= lambda finger: finger_code[finger][1])
    right_hand_order=sorted([finger for finger in layout.home_keys if finger_code[finger][0]==1],key= lambda finger: finger_code[finger][1])

    for keystroke_n_weight in layout.keystrokes:
        keystroke=keystroke_n_weight[0]
        weight=keystroke_n_weight[1]
        #finger: [key_idx, last_used, use_count]
        finger_tasks={finger:[key_idx,-1,0] for finger, key_idx in layout.home_keys.items()}
        
        #assume 1 finger is pressing chat
        finger_tasks[layout.idx2finger[layout.chat_i]][0]=layout.key2idx[layout.chat]

        local_finger_movement_cost=0 #base cost
        local_roll_cost=0

        #inititize for roll
        roll_state=-1
        consecutive_roll=0
        prev_hand_i, prev_finger_i=finger_code[layout.idx2finger[layout.chat_i]]


        for time, keybind_idx in enumerate(keystroke):
            key_idx=keybind_idx2key_idx[keybind_idx]
            press_finger=layout.idx2finger[key_idx]
            #increase use_count
            finger_tasks[press_finger][2]+=1

            prev_key_idx=finger_tasks[press_finger][0]
            prev_time=finger_tasks[press_finger][1]
            #finger_cost*distance**2/(moving_time+press_time)**1.5
            #TODO: fine-tuning
            local_finger_movement_cost+=compute_FMC(
                layout.finger_costs[press_finger],
                layout.keys[layout.idx2key[key_idx]].fpos,
                layout.keys[layout.idx2key[prev_key_idx]].fpos,
                time,
                prev_time
            )

            #finger distance(prefer low distanece, original natural distane)
            def compute_FDC(order):
                res=0
                for i in range(len(order)-1):
                    finger_i=order[i]
                    key_i=layout.idx2key[finger_tasks[finger_i][0]]
                    natural_i=layout.finger_natural_pos[finger_i]
                    for j in range(i+1,len(order)):
                        finger_j=order[j]
                        key_j=layout.idx2key[finger_tasks[finger_j][0]]
                        natural_j=layout.finger_natural_pos[finger_j]
                        res+=(
                            (   
                                ((layout.keys[key_i].fpos.y-layout.keys[key_j].fpos.y)-(natural_i.y-natural_j.y))**2
                                +((layout.keys[key_i].fpos.x-layout.keys[key_j].fpos.x)-(natural_i.x-natural_j.x))**2
                            )
                            /layout.finger_dists[(i,j)]**2
                            *layout.finger_costs[finger_i]
                            *layout.finger_costs[finger_j]
                        )
                return res
            local_finger_dist_cost=compute_FDC(left_hand_order)+compute_FDC(right_hand_order)
            



            #roll handling
            #inward roll
            #outward roll
            #redirect

            hand_i, finger_i=finger_code[press_finger]
            if hand_i!=prev_hand_i: #different hand
                roll_state=-1
                consecutive_roll=0
            else:
                # Determine the current direction of the fingers
                if finger_i > prev_finger_i: current_dir = 2     # Inward
                elif finger_i < prev_finger_i: current_dir = 1   # Outward
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
                        local_roll_cost += layout.finger_costs[press_finger]*consecutive_roll

                
                roll_state=current_dir
            prev_hand_i=hand_i
            prev_finger_i=finger_i



            #update
            finger_tasks[press_finger][0]=key_idx            
            finger_tasks[press_finger][1]=time


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
                layout.keys[layout.idx2key[key_idx]].fpos,
                layout.keys[layout.idx2key[prev_key_idx]].fpos,
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



# from Init import init
# l=Layout()
# i=init(l)
# l.display(i)
# print(sequence_costs(i,l))


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

from vector import Vector
def gbip(weight, eva, reference, penalty, objectives):
    v_eva=Vector([eva[obj] for obj in objectives])
    nor_weight=weight/abs(weight)

    fz=reference-v_eva
    d1 = abs(fz.dot(nor_weight)) / abs(nor_weight)
    d2=abs(v_eva - (reference + nor_weight*d1))

    return d1 + penalty*d2
    
def update_ref(evas, reference,objectives):
    for eva in evas:
        for i in range(len(objectives)):
            obj=objectives[i]
            reference.vals[i]=min(reference.vals[i],eva[obj])
    return reference
    