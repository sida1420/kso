

import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import math

def distance_sq(pos1, pos2): #special distance
    x=(pos1.x-pos2.x)*1.25
    y=pos1.y-pos2.y
    return x**2+y**2

class Point:
    __slots__ = ['x', 'y']
    def __getstate__(self):
        return (self.x, self.y)
    def __setstate__(self, state):
        self.x, self.y = state
    def __init__(self,x,y):
        self.x=x
        self.y=y

    def __add__(self,other):
        return Point(self.x+other.x,self.y+other.y)
    def __sub__(self,other):
        return Point(self.x-other.x,self.y-other.y)
    #scale
    def __mul__(self,other):
        if isinstance(other,Point):
            return self.x*other.x+ self.y*other.y
        return Point(self.x*other,self.y*other)
    def __truediv__(self,other):
        return Point(self.x/other,self.y/other)
    def __neg__(self):
        return Point(-self.x,-self.y)
    def __eq__(self,other):
        return self.x==other.x and self.y==other.y
    def dist(self,other):
        return math.sqrt((self.x-other.x)**2+(self.y-other.y)**2)
    def cross(self, other):
        return self.x*other.y-self.y*other.x

    def __abs__(self):
        return math.sqrt(self.x**2+self.y**2)

    def __repr__(self):
        return f"{round(self.x,1)} {round(self.y,1)}"
    def __call__(self):
        return (self.x,self.y)
    def __hash__(self):
        return hash((self.x, self.y))
    def copy(self):
        return Point(self.x,self.y)


class Vector():
    def __init__(self, vals):
        
        self.vals=vals
        self.n=len(vals)

    def __sub__(self, other):
        if self.n!=other.n:
            return None
        return Vector([self.vals[i]-other.vals[i] for i in range(self.n)])
    def __add__(self, other):
        if self.n!=other.n:
            return None
        return Vector([self.vals[i]+other.vals[i] for i in range(self.n)])

    def dist(self, other):
        if self.n!=other.n:
            return None

        dist=0

        for i in range(self.n):
            dist+=(self.vals[i]-other.vals[i])**2
        return math.sqrt(dist)
    def dot(self, other):
        return sum(self.vals[i] * other.vals[i] for i in range(self.n))
    def __mul__(self, other):
        if isinstance(other, Vector):
            return Vector([self.vals[i]*other.vals[i] for i in range(self.n)])

        return Vector([val*other for val in self.vals])
    def __truediv__(self, other):
        return Vector([val/other for val in self.vals])
    def __abs__(self):
        dist=0

        for i in range(self.n):
            dist+=self.vals[i]**2
        return math.sqrt(dist)

    def __repr__(self):

        ans=""
        for i in range(self.n):
            ans+=f"{round(self.vals[i],2)} "
        return ans
    

class Key:
    def __init__(self, lx, uy, width=1, offset=0):
        self._pos=Point(lx,uy)
        self._width=width
        self._offset=offset
        self.fpos=self._pos+Point(self._width/2+self._offset,0.5)




class Layout:
    def __init__(self):
        self._init_layout()
        self._init_keys()
        self._init_finger()
        self._init_keystrokes()
        self._init_artist()

        self._init_assigned_keys()
        self._init_home_keys()
        self._init_parameters()
        self._init_finger_distances()
        self._precompute()
        self._init_visual()

    def _init_assigned_keys(self):
        self.assigned_keys={}
        with open('config/assigned_fingers.json','r') as file:
            self.assigned_keys=json.load(file)


        self.key_idx2finger_idx=[None]*len(self.key2idx)

        for finger, keys in self.assigned_keys.items():
            assert self._validate_finger(finger), f"\nFINGER NAME [{finger.upper()}] YOU ASSIGNED IN assigned_fingers.json FILE IS INVALID!"
            for key in keys:
                self.key_idx2finger_idx[self.key2idx[key]]=self.finger2idx[finger]

    def _init_artist(self):
        self.fig, self.ax = plt.subplots()
        self.ax.set_aspect('equal', adjustable='box')
        self.ax.invert_yaxis()



    def _init_keystrokes(self):
        self.keystrokes=[]
        with open('config/keystrokes.json','r', encoding='utf-8') as file:
            keystrokes_dict=json.load(file)
            for name, keystroke in keystrokes_dict.items():
                assert "keys" in keystroke, f"\nPLEASE ENTER KEYS FOR [{name.upper()}] IN keystrokes.json FILE FIRST!"

                if "weight" not in keystroke:
                    print(f"WARNING: Keystroke [{name}] in keystrokes.json file doesn't have a weight! Setting it to 1.")
                    keystroke["weight"]=1
            self.keystrokes=list(keystrokes_dict.values())

        #make 2 version of each keystoke: normal version and start with shift home version
        self.keystrokes+=[{"keys": ["lsft","home"]+keys_n_weight["keys"],"weight":keys_n_weight["weight"]/2} for keys_n_weight in self.keystrokes]

        # print(self.keystrokes)
        #add home, lsft, chat for safety
        self.keybinds=sorted({key for data in self.keystrokes for key in data['keys']}.union({'home','lsft','chat'}))
        # print(self.keybinds)
        self.keybind2idx={keybind: i for i,keybind in enumerate(self.keybinds)}

        self.available_keybinds=[i for i, key in enumerate(self.keybinds) if key not in self.fixed_keys.values()]
        #frequency of keys
        freq=[0]*len(self.keybinds)
        key_count=0
        for data in self.keystrokes:
            for key in data['keys']:
                freq[self.keybind2idx[key]]+=1
                key_count+=1

        freq[self.keybind2idx['home']]+=len(self.keystrokes)
        freq[self.keybind2idx['lsft']]+=len(self.keystrokes)
        freq[self.keybind2idx['chat']]+=len(self.keystrokes)
        key_count+=len(self.keystrokes)*3

        #probability of keys in keystrokes
        self.key_probs=[f/key_count for f in freq]

        
        

        #turn dict to list and encode into indices
        self.keystrokes=[[[self.keybind2idx[key] for key in data["keys"]],data["weight"]] for data in self.keystrokes]
        # print(self.keystrokes)


        #encode fixed keys into indices that point to indices too
        self.fixed_keys={self.key2idx[key]:(self.keybind2idx[remap] if remap in self.keybind2idx else remap) for key,remap in self.fixed_keys.items()}
        self.chat_i=self.key2idx[self.chat]
        # print(self.fixed_keys)


    def _init_layout(self):
        self.KEY_WIDTH={}
        with open('config/key_widths.json','r') as file:
            self.KEY_WIDTH=json.load(file)

        self.keys={}
        self.chat='t'
        cur_y=0
        with open('config/layout.txt','r') as file:
            for line in file:
                cur_x=0
                for key in line.split():

                    if key in self.KEY_WIDTH:
                        self.keys[key]=Key(cur_x,cur_y,self.KEY_WIDTH[key][0], self.KEY_WIDTH[key][1])
                        cur_x+=self.KEY_WIDTH[key][0]
                    else:
                        self.keys[key]=Key(cur_x,cur_y)
                        cur_x+=1
                cur_y+=1
                

    def _init_keys(self):
        self.fixed_keys={}
        with open('config/fixed_keys.json','r', encoding='utf-8') as file:
            self.fixed_keys=json.load(file)

        
        
        for key, remap in self.fixed_keys.items():
            assert key in self.keys, f"\nKEY SLOT [{key.upper()}] YOU ASSIGNED IN fixed_keys.json FILE DOESN'T APPEAR IN layout.txt FILE!"


            if remap=='chat':
                self.chat=key
        # self.fixed_keys.pop(self.chat)


        self.remaps={}
        with open('config/available_keys.txt','r') as file:
            self.remaps={key: remap for key,remap in self.fixed_keys.items()}
            for line in file:
                for key in line.split():
                    assert key in self.keys, f"\nKEY SLOT [{key.upper()}] IN available_keys.txt FILE DOESN'T APPEAR IN layout.txt FILE!"

                    if key in self.fixed_keys:
                        print(f"WARNING: Key [{key}] already in fixed_key.json, skipping it!")
                        continue
                    self.remaps[key]=key

        # print(self.remaps)
        self.key2idx={}
        self.idx2key=[]
        for i,key in enumerate(sorted(self.remaps)):
            self.key2idx[key]=i
            self.idx2key.append(key)


        self.available_keys=[i for i,key in enumerate(self.idx2key) if key not in self.fixed_keys or key==self.chat]

        # print(self.fixed_keys)
        # print(self.key2idx)
        # print(self.idx2key)
    
    
    def _init_visual(self):
        self.rects=[]
        self.texts=[]
        for key, data in self.keys.items():
            if key not in self.remaps:
                continue
            ec='#0000FF'
            fc='#ADD8E6'
            rect = patches.Rectangle((data._pos.x, data._pos.y), data._width, 1, 
                         linewidth=0.1, edgecolor=ec, facecolor=fc, alpha=0.5)
            self.rects.append(rect)
            self.ax.add_patch(rect)


            self.texts.append(self.ax.text(data.fpos.x, data.fpos.y, self.remaps[key] if key!=self.chat else 'chat', 
                color='black', fontsize=12, fontweight='bold',
                ha='center', va='center'))
        self.ax.autoscale_view()
        plt.savefig('output/layout.svg')


    def _init_finger(self):
        self.FINGER_CODE={'pinky':0,'ring':1,'middle':2,'index':3,'thumb':4} #DO NOT TOUCH
        self.HAND_CODE={'left':0,'right':1} #DO NOT TOUCH

        self.idx2finger=[f"{hand}_{finger}" for hand, hand_idx in sorted(self.HAND_CODE.items(),key=lambda x: x[1]) for finger, finger_idx in sorted(self.FINGER_CODE.items(),key=lambda x: x[1])]
        self.finger2idx={finger: idx for idx, finger in enumerate(self.idx2finger)}



    def _init_home_keys(self):
        self.home_keys={}
        self.hand=[[],[]] # Initialize two empty lists for left and right hands
        with open('config/home_keys.json','r') as file: 
            for finger, key in json.load(file).items():
                assert self._validate_finger(finger), f"\nFINGER NAME [{finger.upper()}] YOU ASSIGNED IN home_keys.json FILE IS INVALID!"
                assert key in self.keys,  f"\nKEY SLOT [{key.upper()}] YOU ASSIGNED IN home_keys.json FILE DOESN'T APPEAR IN layout.txt FILE!"
                
                self.home_keys[self.finger2idx[finger]]=self.key2idx[key]

                hand_code, finger_code=self.get_finger_roll(self.finger2idx[finger])

                if hand_code==self.HAND_CODE['left']:
                    self.hand[hand_code].append(finger_code)
                else:
                    self.hand[hand_code].append(finger_code)

        self.hand[0].sort()
        self.hand[1].sort()

        natural_pos={}

        with open('config/finger_natural_positions.json','r') as file:
            natural_pos=json.load(file)
        self.finger_natural_pos={}
        for finger_idx in self.home_keys:
            hand, finger=self.idx2finger[finger_idx].split('_')
            assert hand in natural_pos, f"\nHAND [{hand.upper()}] IN finger_natural_positions.json FILE IS INVALID!"
            assert finger in natural_pos[hand]['x'], f"\nFINGER [{finger.upper()}] DOESNT APPEAR IN [{hand.upper()}]:X HAND IN finger_natural_positions.json FILE!"
            assert finger in natural_pos[hand]['y'], f"\nFINGER [{finger.upper()}] DOESNT APPEAR IN [{hand.upper()}]:Y HAND IN finger_natural_positions.json FILE!"

            self.finger_natural_pos[finger_idx]=Point(natural_pos[hand]['x'][finger],natural_pos[hand]['y'][finger])



        



    def _init_parameters(self):
        self.finger_costs={}
        with open('config/parameters.json','r') as file:
            parameters=json.load(file)
            assert "finger_costs" in parameters, f"\nPLEASE ENTER FINGER COSTS IN parameters.json FILE FIRST!"
            self.finger_costs=parameters["finger_costs"]

            for finger in self.finger_costs:
                assert self._validate_finger(finger), f"\nFINGER NAME [{finger.upper()}] YOU ASSIGNED IN parameters.json:FINGER_COSTS FILE IS INVALID!"
        #encode
        self.finger_costs={self.finger2idx[finger]: cost for finger, cost in self.finger_costs.items()}

    def _validate_finger(self, finger):
        if finger not in self.finger2idx:
            return False
        return True



    def _init_finger_distances(self): #need init finger roll first
        tfinger_dists={}
        with open("config/finger_distances.json","r") as file:
            tfinger_dists=json.load(file)

        self.finger_dists={} #THIS USE FINGER CODE AND HAND CODE AS INDEX SYSTEM (SAME WITH FINGER_CODE, HAND_CODE) NOT THE FINGER_IDX SYSTEM (SAME WITH finger2idx)
        for FF, dist in tfinger_dists.items():
            x, y=FF.split('_')
            assert x in self.FINGER_CODE and y in self.FINGER_CODE, f"\nFINGER NAMES [{FF.upper()}] IN finger_distances.json FILE ARE INVALID!"
            self.finger_dists[(self.FINGER_CODE[x],self.FINGER_CODE[y])]=dist
            self.finger_dists[(self.FINGER_CODE[y],self.FINGER_CODE[x])]=dist

    def _precompute(self):
        self.key_sq_dists=[[distance_sq(self.keys[self.idx2key[i]].fpos,self.keys[self.idx2key[j]].fpos) for i in range(len(self.idx2key))] for j in range(len(self.idx2key))] #SQUARE OF DISTANCE BETWEEN KEYS, USE KEY_IDX AS INDEX SYSTEM

        self.initial_FDC_cache=[{},{}] #cache for FDC calculation, index by hand code, key is (finger_i, finger_j) with finger code as index system, value is the FDC cost between the two fingers
        self.initial_FDC_total=0
        from evaluate import FDC_full
        #finger_tasks only have 1 value for key_idx, not the time and count, since it's only used for initialization
        #assume 1 finger is pressing chat
        temp_key=self.home_keys[self.key_idx2finger_idx[self.chat_i]] #store the original key idx for the finger that presses chat
        self.home_keys[self.key_idx2finger_idx[self.chat_i]]=self.chat_i


        for hand_code in [0,1]:
            self.initial_FDC_total+=FDC_full(self, self.home_keys, self.hand[hand_code], hand_code, self.initial_FDC_cache)


        self.home_keys[self.key_idx2finger_idx[self.chat_i]]=temp_key #revert back

        #TODO: precompute FDC factors



    
            
    #GETTERS
    
    def get_finger_roll(self, finger_idx): #THIS FUNCTION RETURNS DIFFERENT INDEX SYSTEM (SAME WITH FINGER_CODE, HAND_CODE)
        hand_code=finger_idx//5
        finger_code=finger_idx%5
        return hand_code, finger_code

    def get_finger_idx(self, hand_code, finger_code): #THIS FUNCTION TAKES IN DIFFERENT INDEX SYSTEM (SAME WITH FINGER_CODE, HAND_CODE)
        return hand_code*5+finger_code

    def display(self, potential_remaps:list, scores={}, name='layout'):
        for i in range(len(self.texts)):
            self.texts[i].remove()
        self.texts=[]
        for keyIdx, remapIdx in enumerate(potential_remaps):
            if remapIdx is None:
                continue
            key=self.idx2key[keyIdx]
            remap=self.keybinds[remapIdx]
            self.texts.append(self.ax.text(self.keys[key].fpos.x, self.keys[key].fpos.y, remap, 
                color='black', fontsize=12, fontweight='bold',
                ha='center', va='center'))

        title=''
        for metric_name, metric_score in scores.items():
            abbreviated=''
            for w in metric_name.split("_"):
                abbreviated+=w[0].upper()
            title+=f"{abbreviated}: {round(metric_score,2)}, "
        self.ax.set_title(title[:-2])
        self.ax.autoscale_view()
        plt.savefig(f'output/{name}.svg')

if __name__=="__main__":

    l=Layout()
    print(l.finger2idx)
    print(l.available_keys)
    print(l.key_idx2finger_idx)