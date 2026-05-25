import random
import numpy as np
import math
from classes import *
class Evaluator:
    def __init__(self, layout: Layout):
        self.layout=layout

        # direct aliases for speed
        self.idx2key=layout.idx2key
        self.key_probs=layout.key_probs
        self.home_keys=layout.home_keys
        self.key_idx2finger_idx=layout.key_idx2finger_idx
        self.chat_i=layout.chat_i
        self.hand=layout.hand
        self.sizes=layout.sizes
        self.shift_kbi=layout.shift_kbi
        self.no_shift_variance_skb_set=layout.no_shift_variance_skb_set
        self.keystrokes=layout.keystrokes
        self.total_keybinds=layout.total_keybinds
        self.special_keybinds=layout.special_keybinds
        self.counterparts=layout.counterparts
        self.available_keybinds=layout.available_keybinds
        self.fixed_keys=layout.fixed_keys
        self.strain_heapmap=layout.strain_heapmap
        self.shift_i=layout.shift_i
        self.keys=layout.keys
        self.finger_natural_pos=layout.finger_natural_pos
        self.finger_dists=layout.finger_dists
        self.finger_efforts=layout.finger_efforts
        self.max_sq_dist=layout.max_sq_dist
        self.key_sq_dists=layout.key_sq_dists
        self.keybinds=layout.keybinds

        self.get_finger_idx=layout.get_finger_idx
        self.get_finger_roll=layout.get_finger_roll



        self.REDIRECT_PENALTY_COEFF=4
        self.INWARD_REWARD_COEFF=3
        self.OUTWARD_REWARD_COEFF=1
        self.SAME_FINGER_PENALTY_COEFF=3
        self.TRAVEL_DISTANCE_COEFF=0.6
        self.FINGER_STRETCH_COEFF=0.6
        self.SHIFT_HOLDING_STRAIN_COEFF=0.5
        self.stretch_decaying_factor=math.exp(self.FINGER_STRETCH_COEFF)
        self._precompute()

    def _precompute(self):
        #cache finger roll
        self.finger_rolls={}
        for finger_idx in self.home_keys.keys():
            self.finger_rolls[finger_idx]=self.get_finger_roll(finger_idx)
        
        max_time=0
        for keystroke in self.keystrokes:
            max_time=max(max_time,len(keystroke[0]))
        max_time=max_time*2+1
        self.TD_decay_cache=[1/math.exp(time*self.TRAVEL_DISTANCE_COEFF) for time in range(max_time)]
        max_time*=2
        self.FS_decay_cache=[self.stretch_decaying_factor**time for time in range(max_time)]


        self.initial_FS_cache=[{},{}] #cache for FS calculation, index by hand code, key is (finger_i, finger_j) with finger code as index system, value is the FS cost between the two fingers
        self.initial_FS_total=0
        #finger_tasks only have 1 value for key_idx, not the time and count, since it's only used for initialization
        #assume 1 finger is pressing chat
        temp_key=self.home_keys[self.key_idx2finger_idx[self.chat_i[0]]] #store the original key idx for the finger that presses chat
        self.home_keys[self.key_idx2finger_idx[self.chat_i[0]]]=self.chat_i[0]


        for hand_code in [0,1]:
            self.initial_FS_total+=self.FS_full(self.home_keys, self.hand[hand_code], hand_code, self.initial_FS_cache)

        self.home_keys[self.key_idx2finger_idx[self.chat_i[0]]]=temp_key #revert back

    def normalize_keystrokes(self, ind: list):
        shift_s=set(ind[i] for i in range(self.sizes[0],self.sizes[0]+self.sizes[1]))
        nkeystrokes=[]
        shift_w=0

        for keystroke, weight in self.keystrokes:
            shift=False
            nkeystroke=[]
            shift_durations=[]
            last_duration=0
            shift_intended=False
            for i,kb_idx in enumerate(keystroke):
                if kb_idx==self.shift_kbi:
                    if shift:
                        continue
                    shift_w+=weight
                    shift=True
                    shift_intended=True
                elif kb_idx in shift_s or shift_intended:
                    if not shift:
                        nkeystroke.append(self.shift_kbi)
                        shift_durations.append(1)
                        last_duration=1
                        shift_w+=weight
                        shift=True
                    shift_intended=False
                elif not(shift and kb_idx in self.no_shift_variance_skb_set and i<len(keystroke)-1 and (keystroke[i+1] in shift_s or keystroke[i+1]==self.shift_kbi)):
                    if shift:
                        nkeystroke.append(self.shift_kbi) #if you are shifting are seeing shift, which mean come back to base layer
                        shift_durations.append(0)
                        last_duration=0
                    shift=False
                if shift:
                    last_duration+=1
                    shift_durations.append(last_duration)
                else:
                    shift_durations.append(0)
                    last_duration=0

                nkeystroke.append(kb_idx)
            nkeystrokes.append((nkeystroke,shift_durations))

        #recal the probability
        total = self.total_keybinds + shift_w
        nkey_probs = [0.0] * len(self.key_probs)
        for i in range(len(self.key_probs)):
            if i != self.shift_kbi:
                nkey_probs[i] = self.key_probs[i] * self.total_keybinds / total
        nkey_probs[self.shift_kbi] = shift_w / total

        return nkeystrokes, nkey_probs


    def correct(self, ind):
        s=set()

        for j,i in enumerate(ind):
            if i is not None:
                s.add(i)
                if i in self.special_keybinds:
                    if j>=self.sizes[0]:
                        return False
                    if self.counterparts[j] is not None and ind[self.counterparts[j]] is not None:
                        return False
        return len(s)==len(self.available_keybinds)+len(set(self.fixed_keys.values()))

    def finger_strain(self, ind, nkey_probs):
        res = 0
        total_shift_hold_prob=0
        for i, j in enumerate(ind):
            if j is None:
                continue
            if self.sizes[0] <=i and i!=self.shift_i[0]:
                total_shift_hold_prob+=nkey_probs[j]

            res += self.strain_heapmap[i]* nkey_probs[j] 

        #add bonus for shift
        res+=self.strain_heapmap[self.shift_i[0]]*total_shift_hold_prob*self.SHIFT_HOLDING_STRAIN_COEFF

        return res


    #TODO: fine-tuning
    def compute_TD(self, finger_cost, sq_dist, time, prev_time):
        delta_time = time - prev_time+1
        return (
            finger_cost
            *sq_dist
            *self.TD_decay_cache[delta_time] #fine-tune
        )


    #finger distance(prefer low distanece, original natural distane)
    def compute_FS(self,key_i_pos, key_j_pos, natural_i, natural_j, finger_dist, finger_cost_i, finger_cost_j):
        return (
            (   
                ((key_i_pos.y-key_j_pos.y)-(natural_i.y-natural_j.y))**2
                +((key_i_pos.x-key_j_pos.x)-(natural_i.x-natural_j.x))**2
            )
            /finger_dist**2
            *finger_cost_i
            *finger_cost_j
        )


    def FS_full(self, finger_tasks, order, hand_code, cache): #finger_tasks only have 1 value for key_idx, not the time and count, since it's only used for initialization
        res=0
        for finger_i in order: #THIS USE FINGER CODE AND HAND CODE AS INDEX SYSTEM (SAME WITH FINGER_CODE, HAND_CODE) NOT THE FINGER_IDX SYSTEM (SAME WITH finger2idx)
            finger_idx_i=self.get_finger_idx(hand_code, finger_i) #REVERT BACK TO FINGER_IDX SYSTEM FOR FINGER COST
            key_i=self.idx2key[finger_tasks[finger_idx_i]]
            natural_i=self.finger_natural_pos[finger_idx_i]
            for finger_j in order:
                if finger_j<=finger_i:
                    continue
                finger_idx_j=self.get_finger_idx(hand_code, finger_j) #REVERT
                key_j=self.idx2key[finger_tasks[finger_idx_j]]
                natural_j=self.finger_natural_pos[finger_idx_j]
                cost=self.compute_FS(
                    self.keys[key_i].fpos,
                    self.keys[key_j].fpos,
                    natural_i,
                    natural_j,
                    self.finger_dists[(finger_i,finger_j)], #FINGER DISTANCE USE FINGER CODE AS INDEX SYSTEM
                    self.finger_efforts[finger_idx_i],
                    self.finger_efforts[finger_idx_j]
                )
                cache[hand_code][(finger_i,finger_j)]=cost
                res+=cost
        return res

    def FS_partial(self, finger_tasks, key_idx, finger_i, finger_idx_i, time, order, hand_code, old_res, cache): #finger task still stores old key
        key_i=self.idx2key[key_idx] #key str
        natural_i=self.finger_natural_pos[finger_idx_i]
        res=old_res
        for finger_j in order:
            if finger_i==finger_j:
                continue
            finger_idx_j=self.get_finger_idx(hand_code, finger_j) #REVERT
            key_j=self.idx2key[finger_tasks[finger_idx_j][0]] #key str
            natural_j=self.finger_natural_pos[finger_idx_j]

            order_pair=(min(finger_i,finger_j),max(finger_i,finger_j))

            res-=cache[hand_code][order_pair]*self.FS_decay_cache[finger_tasks[finger_idx_i][1]+finger_tasks[finger_idx_j][1]]
            cost=self.compute_FS(
                self.keys[key_i].fpos,
                self.keys[key_j].fpos,
                natural_i,
                natural_j,
                self.finger_dists[(finger_i,finger_j)],
                self.finger_efforts[finger_idx_i],
                self.finger_efforts[finger_idx_j],
            )
            cache[hand_code][order_pair]=cost

            res+=cost* self.FS_decay_cache[time+ finger_tasks[finger_idx_j][1]]
        return res


    def sequence_costs(self, ind: list, nkeystrokes):
        #init total costs
        travel_distance_cost=0
        roll_cost=0
        use_count_cost=0
        finger_stretch_cost=0

        keybind_idx2key_idx=[None]*len(self.keybinds)
        for i,j in enumerate(ind):
            if j is not None:
                keybind_idx2key_idx[j]=i


        #const

        for i in range(len(nkeystrokes)):
            keystroke,shift_durations=nkeystrokes[i]
            weight=self.keystrokes[i][1]
            #finger: [key_idx, last_used, use_count]
            finger_tasks={finger_idx:[key_idx,0,0] for finger_idx, key_idx in self.home_keys.items()}

            #assume 1 finger is pressing chat
            finger_tasks[self.key_idx2finger_idx[self.chat_i[0]]][0]=self.chat_i[0]

            #init 3 local costs
            local_travel_distance=0
            local_roll_cost=0
            local_finger_stretch=0  # accumulate over time

            #inititize for roll
            roll_state=-1
            consecutive_roll=0
            prev_hand_code, prev_finger_code=self.finger_rolls[self.key_idx2finger_idx[self.chat_i[0]]]

            FS_cache=[dict(self.initial_FS_cache[0]),dict(self.initial_FS_cache[1])] #cache for FS calculation, index by hand code, key is (finger_i, finger_j) with finger code as index system, value is the FS cost between the two fingers
            current_FS_total=self.initial_FS_total

            #keep track of what finger is pressing shift
            pressing_shift=None

            for j, keybind_idx in enumerate(keystroke):
                time=j+1
                key_idx=keybind_idx2key_idx[keybind_idx]
                press_finger=self.key_idx2finger_idx[key_idx]

                if key_idx==self.shift_i[0]: #shift action
                    if pressing_shift is None: #Start pressing shift
                        pressing_shift=press_finger
                    else: #Stop pressing shift
                        pressing_shift=None

                prev_key_idx=finger_tasks[press_finger][0]
                prev_time=finger_tasks[press_finger][1]
                #finger_cost*distance**2/(moving_time+press_time)**1.5

                local_travel_distance+=self.compute_TD(
                    self.finger_efforts[press_finger],
                    self.max_sq_dist if(press_finger==pressing_shift and shift_durations[j]>1) else #Try to press another key on shift layer with shift pressing finger
                    self.key_sq_dists[key_idx][prev_key_idx],
                    time,
                    prev_time
                )

                #ROLL HANDLING
                hand_code, finger_code=self.finger_rolls[press_finger]

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
                        local_roll_cost += self.REDIRECT_PENALTY_COEFF*self.finger_efforts[press_finger]
                        consecutive_roll = 0
                    else:
                        consecutive_roll+=1
                        if current_dir==2:
                            local_roll_cost -= self.INWARD_REWARD_COEFF*consecutive_roll/self.finger_efforts[press_finger]
                        elif current_dir==1:
                            local_roll_cost -= self.OUTWARD_REWARD_COEFF*consecutive_roll/self.finger_efforts[press_finger]
                            # pass
                        elif current_dir==0:
                            local_roll_cost += self.SAME_FINGER_PENALTY_COEFF*self.finger_efforts[press_finger]*consecutive_roll*2


                    roll_state=current_dir
                prev_hand_code=hand_code
                prev_finger_code=finger_code



                # 1. FS for pressing finger
                current_FS_total=(
                    self.FS_partial(finger_tasks, key_idx, finger_code, press_finger, time, self.hand[hand_code], hand_code, current_FS_total, FS_cache)
                )

                # 2. Update pressing finger
                finger_tasks[press_finger][0]=key_idx            
                finger_tasks[press_finger][1]=time
                finger_tasks[press_finger][2]+=1

                # 3. If shift held by different finger, FS for shift too
                if pressing_shift is not None and pressing_shift != press_finger:
                    shift_hand_code, shift_finger_code = self.finger_rolls[pressing_shift]
                    shift_key_idx = finger_tasks[pressing_shift][0]
                    current_FS_total = self.FS_partial(finger_tasks, shift_key_idx, shift_finger_code, pressing_shift, time, self.hand[shift_hand_code], shift_hand_code, current_FS_total, FS_cache)

                    # 4. Update shift (time + use_count)
                    finger_tasks[pressing_shift][1]=time
                    finger_tasks[pressing_shift][2]+=0.5

                # 5. Global decay (once per timestep)
                local_finger_stretch += current_FS_total/(self.FS_decay_cache[2*time])








            #cost of moving all finger back to home row
            #only calculate if finger need to move
            time=len(keystroke)
            if pressing_shift is not None:
                finger_tasks[pressing_shift][1]=time-1
            for finger, key_idx_n_time_n_count in finger_tasks.items():
                prev_key_idx=key_idx_n_time_n_count[0]
                prev_time=key_idx_n_time_n_count[1]

                key_idx=self.home_keys[finger]
                if prev_key_idx==key_idx:
                    continue
                local_travel_distance+=self.compute_TD(
                    self.finger_efforts[finger],
                    self.key_sq_dists[key_idx][prev_key_idx],
                    time,
                    prev_time
                )


            #use count
            local_use_count_cost=0
            for finger, key_idx_n_time_n_count in finger_tasks.items():
                #count*fingercost
                local_use_count_cost+=(
                    key_idx_n_time_n_count[2]**2
                    *self.finger_efforts[finger]
                )


            use_count_cost+=local_use_count_cost*weight
            travel_distance_cost+=local_travel_distance*weight
            roll_cost+=local_roll_cost*weight
            finger_stretch_cost+=local_finger_stretch*weight
        return travel_distance_cost, use_count_cost, roll_cost, finger_stretch_cost



    def evaluate(self, population):

        evas=[]
        for i in range(len(population)):
            nkeystrokes, nkey_probs=self.normalize_keystrokes(population[i])
            # print([[self.keybinds[key] for key in keystroke[0]] for keystroke in nkeystrokes])
            # break

            travel_distance_cost, use_count_cost, roll_cost, finger_stretch_cost=self.sequence_costs(population[i], nkeystrokes)
            eva={
                "finger_strain":self.finger_strain(population[i], nkey_probs),
                "travel_distance":travel_distance_cost,
                "use_count":use_count_cost,
                "bad_roll": roll_cost,
                "finger_stretch": finger_stretch_cost
                }
            evas.append(eva)

        return evas

# target=[Point(0,0.5),Point(0.5,0.5),Point(0.6,0.5),Point(1,0.5)]
# print(evaluate([[1,0,0,0,0,0,0,0,0,0],],target))


if __name__ == '__main__':
    from init import *
    l=Layout()
    i=distributed_init(l)
    l.display(i)
    e=Evaluator(l)
    print(e.evaluate([i]))



def apply_scale(evaluation, mins, maxs):
    return (evaluation-np.array(mins))/(np.array(maxs)-np.array(mins))

def weighted_sum_scaled(scaled_eval: np.ndarray, target_vector: np.ndarray):
    return np.sum(scaled_eval*target_vector)

def update_global(global_extreme, evas, mode='min'):
    range_changed=False
    for e in evas:
        for i,v in enumerate(e):
            if mode == 'min' and v < global_extreme[i]:
                global_extreme[i] = v
                range_changed=True
            elif mode == 'max' and v > global_extreme[i]:
                global_extreme[i] = v
                range_changed=True
    return range_changed