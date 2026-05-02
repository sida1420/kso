

import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import math

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
        self._init_keystrokes()
        self._init_artist()


        self.assigned_keys={}
        with open('config/assigned_fingers.json','r') as file:
            self.assigned_keys=json.load(file)

        self.idx2finger=[None]*len(self.key2idx)

        for finger, keys in self.assigned_keys.items():
            for key in keys:
                self.idx2finger[self.key2idx[key]]=finger
        self._init_home_keys()
        self._init_parameters()
        self._init_finger_rolls()
        self._init_finger_distances()
        self._init_visual()
        # print(self.idx2finger)


    def _init_artist(self):
        self.fig, self.ax = plt.subplots()
        self.ax.set_aspect('equal', adjustable='box')
        self.ax.invert_yaxis()



    def _init_keystrokes(self):
        self.keystrokes={}
        with open('config/keystrokes.json','r') as file:
            self.keystrokes=list(json.load(file).values())

        #make 2 version of each keystoke: normal version and start with shift home version
        self.keystrokes+=[{"keys": ["lsft","home"]+keys_n_weight["keys"],"weight":keys_n_weight["weight"]/2} for keys_n_weight in self.keystrokes]

        # print(self.keystrokes)
        #add home, lsft, chat for safety
        self.keybinds=sorted({key for data in self.keystrokes for key in data['keys']}.union({'home','lsft','chat'}))
        print(self.keybinds)
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

        self.prob=[f/key_count for f in freq]

        
        

        #turn dict to list and encode into indices
        self.keystrokes=[[[self.keybind2idx[key] for key in data["keys"]],data["weight"]] for data in self.keystrokes]
        print(self.keystrokes)


        #encode fixed keys into indices that point to indices too
        self.fixed_keys={self.key2idx[key]:(self.keybind2idx[remap] if remap in self.keybind2idx else remap) for key,remap in self.fixed_keys.items()}
        self.chat_i=self.key2idx[self.chat]
        print(self.fixed_keys)


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
        with open('config/fixed_keys.json','r') as file:
            self.fixed_keys=json.load(file)

        
        
        for key, remap in self.fixed_keys.items():
            if remap=='chat':
                self.chat=key
        # self.fixed_keys.pop(self.chat)


        self.remaps={}
        with open('config/available_keys.txt','r') as file:
            self.remaps={key: remap for key,remap in self.fixed_keys.items()}
            for line in file:
                for key in line.split():
                    if key in self.fixed_keys:
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
            rect = patches.Rectangle((data._pos.x, data._pos.y), data._width, 1, 
                         linewidth=0.1, edgecolor='blue', facecolor='lightblue', alpha=0.5)
            self.rects.append(rect)
            self.ax.add_patch(rect)


            self.texts.append(self.ax.text(data.fpos.x, data.fpos.y, self.remaps[key] if key!=self.chat else 'chat', 
                color='black', fontsize=12, fontweight='bold',
                ha='center', va='center'))
        self.ax.autoscale_view()
        plt.savefig('output/layout.svg')


    def _init_home_keys(self):
        self.home_keys={}
        with open('config/home_keys.json','r') as file: 
            self.home_keys={finger:self.key2idx[key] for finger, key in json.load(file).items()}
        
        natural_pos={}

        with open('config/finger_natural_positions.json','r') as file:
            natural_pos=json.load(file)
        self.finger_natural_pos={}
        for ffinger in self.home_keys:
            hand, finger=ffinger.split("_")
            self.finger_natural_pos[ffinger]=Point(natural_pos[hand]['x'][finger],natural_pos[hand]['y'][finger])


    def _init_parameters(self):
        self.finger_costs={}
        with open('config/parameters.json','r') as file:
            parameters=json.load(file)
            self.finger_costs=parameters["finger_costs"]

    def _init_finger_rolls(self):
        self.finger_roll={'pinky':0,'ring':1,'middle':2,'index':3,'thumb':4} #DO NOT TOUCH
        self.hand={'left':0,'right':1} #DO NOT TOUCH

    def _init_finger_distances(self): #need init finger roll first
        tfinger_dists={}
        with open("config/finger_distances.json","r") as file:
            tfinger_dists=json.load(file)

        self.finger_dists={}
        for FF, dist in tfinger_dists.items():
            x, y=FF.split('_')
            self.finger_dists[(self.finger_roll[x],self.finger_roll[y])]=dist
            
    
    #GETTERS
    def get_finger_roll(self, finger):
        hand_n_finger=finger.split('_')
        return self.hand[hand_n_finger[0]], self.finger_roll[hand_n_finger[1]]


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

# l=Layout()
# print(l.available_keybinds)
# print(l.available_keys)