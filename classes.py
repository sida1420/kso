

from helper import *
import math
from pathlib import Path
import shutil
import matplotlib.pyplot as plt 
import matplotlib.patches as patches


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
        return math.sqrt(self.sq_dist(other))
    def sq_dist(self, other):
        return (self.x-other.x)**2+(self.y-other.y)**2
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
    def __init__(self, lx: float, uy: float, width:float=1,height:float=1, offset:float=0):
        self._pos=Point(lx,uy)
        self._width=width
        self._height=height
        self._offset=offset
    
        self.fpos=self._pos+Point(self._width/2+self._offset,self._height/2)

    def set_pos(self, new_pos: Point):
        self._pos=new_pos
        self.fpos=self._pos+Point(self._width/2+self._offset,self._height/2)

class Validator:
    def __init__(self):
        self._init_finger()
    def _init_finger(self):
        self.FINGER_CODE={'pinky':0,'ring':1,'middle':2,'index':3,'thumb':4} #DO NOT TOUCH
        self.HAND_CODE={'left':0,'right':1} #DO NOT TOUCH

        self.idx2finger=[f"{hand}_{finger}" for hand, hand_idx in sorted(self.HAND_CODE.items(),key=lambda x: x[1]) for finger, finger_idx in sorted(self.FINGER_CODE.items(),key=lambda x: x[1])]
        self.finger2idx={finger: idx for idx, finger in enumerate(self.idx2finger)}
    def _does_key_exist(self,key: str, container: dict, file, root_file):
        if key not in container:
            raise ValueError(f"\nKEY SLOT [{key.upper()}] YOU ASSIGNED IN {file} FILE DOESN'T APPEAR IN {root_file} FILE!")
        return True

    def _is_key_correct_type(self,key: str, file):
        if not isinstance(key,str):
            raise TypeError(f"\nKEY SLOT [{key.upper()}] YOU ASSIGNED IN {file} FILE HAS INCORRECT TYPE, IT NEEDS TO BE STRING NOT ({type(key)})!")
        return True
    def _validate_finger(self, finger, file):
        if finger not in self.finger2idx:
            raise ValueError(f"\nFINGER NAME [{finger.upper()}] YOU ASSIGNED IN {file} FILE IS INVALID!")
        return True

class LayoutOrganizer(Validator):
    def __init__(self):
        super().__init__()
        self.left_most_x=0
        self.left_most_y=0

        self.potential_x=0
        self.previous_y=0

        self.lowest_y=0 #for culling

        self.keys={}
        self.cache=[]
    def cull_cache(self):
        self.cache=[k for k in self.cache if self.keys[k]._pos.y+self.keys[k]._height>=self.lowest_y]

    def load_layout(self, layout, custom_keys={}):

        x_in="x" in custom_keys
        y_in="y" in custom_keys
        width_in="width" in custom_keys
        height_in="height" in custom_keys
        offset_in="offset" in custom_keys
        for line in layout:
            new_line=True
            for key in line:
                self._is_key_correct_type(key, "layout.txt")
                x=None
                y=None
                w=h=1
                offset=0
                if x_in and key in custom_keys["x"]:
                    x=custom_keys["x"][key]
                if y_in and key in custom_keys["y"]:
                    y=custom_keys["y"][key]
                if width_in and key in custom_keys["width"]:
                    w=custom_keys["width"][key]
                if height_in and key in custom_keys["height"]:
                    h=custom_keys["height"][key]
                if offset_in and key in custom_keys["offset"]:
                    offset=custom_keys["offset"][key]
                
                self.add_key(key,x,y,w,h,offset,new_line)
                if new_line: new_line=False
    def add_key(self, name, x=None, y=None, width=1, height=1, offset=0, new_line=False):

        if new_line:
            self.potential_x=self.left_most_x
        if x is None: x=self.potential_x
        if y is None: y=self.left_most_y if new_line else self.previous_y

        #Snap with border
        if x<self.left_most_x:
            x=self.left_most_x
        if y<self.left_most_y:
            y=self.left_most_y


        #Snap with other keys
        for k in self.cache:
            key=self.keys[k]

            if y<key._pos.y+key._height and x<key._pos.x+key._width:
                if new_line:
                    y=key._pos.y+key._height
                else: x=key._pos.x+key._width

            
        self.potential_x=x+width
        self.previous_y=y
        if new_line:

            self.cull_cache()

            self.lowest_y=y+height
        else:
            self.lowest_y=min(self.lowest_y,y+height)

        
        self.keys[name]=Key(x,y,width,height,offset)
        self.cache.append(name)


class AdvLayoutOrganizer(LayoutOrganizer):
    def __init__(self):
        super().__init__()
    def new_key(self):
        n=len(self.keys)
        name=f"key_{n}"
        while name in self.keys:
            n+=1
            name=f"key_{n}"

        x=self.left_most_x
        y=self.left_most_y
        for key in self.keys.values():
            if key._pos.y==y:
                x=max(x,key._pos.x+key._width)
            elif key._pos.y>y:
                y=key._pos.y
                x=key._pos.x+key._width


        self.keys[name]=Key(x,y)
        return name

    def remove_key(self, name):
        self.keys.pop(name)


    def save(self, save_layout=True, save_custom_keys=True, available_keys_set=None, available_shift_keys_set=None):
        
        #y grouping
        rows={}
        for name, key in self.keys.items():
            # print(f"{name} {key._pos.x} {key._pos.y} {key._width} {key._height} {key._offset}")
            if key._pos.y not in rows:
                rows[key._pos.y]=[name,]    
            else:
                rows[key._pos.y].append(name)

        

        for row in rows.values():
            row.sort(key=lambda k: self.keys[k]._pos.x)
        

        custom_keys={"x":{},"y":{},"width":{},"height":{},"offset":{}}

        layout=[]

        previous_y=self.left_most_y
        for y, row in rows.items():
            previous_x=self.left_most_x
            aliged=False
            for name in row:
                key=self.keys[name]
                if (key._pos.x-previous_x)>1e-6:
                    custom_keys["x"][name]=key._pos.x
                if not aliged:
                    if(key._pos.y-previous_y)>1e-6:
                        custom_keys["y"][name]=key._pos.y
                    previous_y=key._pos.y+key._height
                    aliged=True
                
                previous_x=key._pos.x+key._width
                if key._width!=1:
                    custom_keys["width"][name]=key._width
                if key._height!=1:
                    custom_keys["height"][name]=key._height
                if key._offset!=0:
                    custom_keys["offset"][name]=key._offset

            layout.append(row)
        if available_keys_set is not None and available_shift_keys_set is not None:
            check_required_config_file("available_keys.txt")
            check_required_config_file("available_shift_keys.txt")
            available_keys=[]
            available_shift_keys=[]
            for row in layout:
                available_keys.append([name for name in row if name in available_keys_set])
                available_shift_keys.append([name for name in row if name in available_shift_keys_set])

        if save_custom_keys:
            check_required_config_file("custom_keys.json")
            custom_keys={k:v for k,v in custom_keys.items() if v}
            write_json("custom_keys.json", custom_keys)
        if save_layout:
            check_required_config_file("layout.txt")
            write_text_rows("layout.txt", layout)

class Variance:
    def get(self):
        return {
            'bspc':{'bspc','backspace','bs','<'},
            'spc':{'sp','space','spc','_'},
            'sft': {'sft','lsft','shift','rsft','lshift', 'rshift'},
            'chat': {'chat'},
            'home': {'home', 'hm'},
        }


class Layout(Validator):
    def __init__(self):
        super().__init__()

        self._init_layout()
        self._init_keys()
        self._init_keystrokes()
        self._init_artist()

        self._init_assigned_keys()
        self._init_home_keys()
        self._init_parameters()
        self._init_max_finger_dists()
        self._precompute()
        self._init_visual()

    def _init_layout(self):
        self.custom_keys={}
        file_name="custom_keys.json"

        check_required_config_file(file_name)

        self.custom_keys=read_json(file_name)

        self.keys={}

        self.organizer=LayoutOrganizer()
        file_name="layout.txt"

        check_required_config_file(file_name)
        layout=read_text_rows(file_name)
        self.organizer.load_layout(layout, self.custom_keys)
        
        self.keys=self.organizer.keys.copy()
        # self.num_rows=cur_y
    def _init_keys(self):
        #SHIFT LAYER


        self._init_shift_layer()

        self._init_fixed_keys()
        self._init_available_keys()   

        #hash position
        self.key_positions=[self.keys[key].fpos for i,key in enumerate(self.idx2key)] 

    def _init_shift_layer(self):
        if not check_config_file("available_shift_keys.txt"):
            shutil.copyfile("config/available_keys.txt","config/available_shift_keys.txt")

        if not check_config_file("fixed_shift_keys.json"):
            # shutil.copyfile("config/fixed_keys.json", "config/fixed_shift_keys.json")
            write_json("fixed_shift_keys.json", {})

    def _init_fixed_keys(self):
        #FIXED KEY
        file_name='fixed_keys.json'
        check_required_config_file(file_name)
        self.fixed_keys=[]
        self.fixed_keys.append(read_json(file_name))
        


        #Special keys, with keyslot, name, keybind (if keyslot still none it means the key is flexible)
        
        self.special_keys={
            'bspc':[None,'bspc',None],
            'spc':[None,'spc',None],
            'sft':[None,'sft',None],
            'chat':[None,'chat',None],
            'home':[None,'home',None]
        }
        special_variances=Variance().get()

        # print(self.fixed_keys)

        for key,remap in self.fixed_keys[0].items():
            self._is_key_correct_type(key, file_name)
            self._does_key_exist(key,self.keys,file_name,'layout.txt')

            if isinstance(remap,list):
                if remap[0] in special_variances['chat']:
                    self.special_keys["chat"][0]=key
                    self.special_keys["chat"][1]= remap[0]
                    #Edge case: the other key in the list with chat is also a special key
                    if len(remap)>1:
                        for k,v in special_variances.items():
                            if k=='chat': continue
                            if remap[1] in v:
                                self.special_keys[k][0]=key
                                self.special_keys[k][1]=remap[1]
                elif (len(remap)>1 and remap[1] in special_variances['chat']):
                    self.special_keys["chat"][0]=key
                    self.special_keys["chat"][1]= remap[1]
                    #Edge case: the other key in the list with chat is also a special key

                    for k,v in special_variances.items():
                        if k=='chat': continue
                        if remap[0] in v:
                            self.special_keys[k][0]=key
                            self.special_keys[k][1]=remap[0]
            elif isinstance(remap,str):
                for k,v in special_variances.items():
                    if remap in v:
                        self.special_keys[k][0]=key
                        self.special_keys[k][1]=remap
            elif not isinstance(remap,str):
                raise TypeError(f"\nKEY SLOT [{key.upper()}] NEEDS TO ASSOCIATED WITH A KEY TYPE STRING, NOT [{remap}] ({type(remap)})!")

        # self.fixed_keys.pop(self.chat)
        if self.special_keys['sft'][0] is None:
            raise ValueError(f"\nPLEASE MAP [SHIFT] KEY WITH A KEYSLOT IN {file_name} FILE FIRST!")

        if self.special_keys['chat'][0] is None:
            raise ValueError(f"\nPLEASE MAP [CHAT] KEY WITH A KEYSLOT IN {file_name} FILE FIRST!")
        else:

            remap=self.fixed_keys[0][self.special_keys['chat'][0]]
            if isinstance(remap,str) or (isinstance(remap,list) and len(remap)==1):
                self.fixed_keys[0].pop(self.special_keys['chat'][0])
            elif isinstance(remap,list) and len(remap)>1:
                self.fixed_keys[0][self.special_keys['chat'][0]]=self.fixed_keys[0][self.special_keys['chat'][0]][1 if remap[0] in special_variances['chat'] else 0]
        
        #FOR SHIFT LAYER

        file_name='fixed_shift_keys.json'
        self.fixed_keys.append(read_json(file_name))


        for key,remap in self.fixed_keys[1].items():
            self._is_key_correct_type(key, file_name)
            self._does_key_exist(key,self.keys,file_name,'layout.txt')
            if not isinstance(remap,str):
                raise TypeError(f"\nKEY SLOT [{key.upper()}] IN {file_name} FILE NEEDS TO ASSOCIATED WITH A KEY TYPE STRING, NOT [{remap}] ({type(remap)})!")

    
    def _init_available_keys(self):

        file_name='available_keys.txt'

        check_required_config_file(file_name)
        self.remaps=[{key: remap  for key, remap in layer.items()} for layer in self.fixed_keys]
        layout=read_text_rows(file_name)
        for line in layout:
            for key in line:
                self._is_key_correct_type(key, file_name)
                self._does_key_exist(key,self.keys, file_name, 'layout.txt')
                if key in self.fixed_keys[0] and key!=self.special_keys['chat'][0]:
                    print(f"WARNING: Key [{key}] already in fixed_keys.json, skipping it!")
                    continue
                self.remaps[0][key]=key

        #SHIFT LAYER
        file_name='available_shift_keys.txt'
        check_required_config_file(file_name)
        layout=read_text_rows(file_name)
        for line in layout:
            for key in line:
                self._is_key_correct_type(key, file_name)
                self._does_key_exist(key,self.keys, file_name, 'layout.txt')
                if key in self.fixed_keys[1]:
                    print(f"WARNING: Key [{key}] already in fixed_shift_keys.json, skipping it!")
                    continue
                self.remaps[1][key]=key

        self.key2idx=[{},{}]
        self.sizes=[len(layer) for layer in self.remaps]
        self.idx2key=[]
        
        j=0
        for i, layer in enumerate(self.remaps):
            for key in sorted(layer, key= lambda k: (self.keys[k]._pos.y,self.keys[k]._pos.x)):
                self.key2idx[i][key]=j
                self.idx2key.append(key)
                j+=1

        self.layered_available_keys=[[j for key,j in layer.items() if key not in self.fixed_keys[i]] for i,layer in enumerate(self.key2idx)]
        self.available_keys=[key_idx for layer in self.layered_available_keys for key_idx in layer]

        #store if a key has it shifted couter part or vice versa

        self.counterparts={}
        for i, layer in enumerate(self.key2idx):
            j=1 if i==0 else 0
            for key,key_idx in layer.items():
                self.counterparts[key_idx]=None if key not in self.key2idx[j] else self.key2idx[j][key]


        #use key2idx to combine fixed keys's layers into 1
        #key: remap --> keyIdx: remap
        self.fixed_keys={self.key2idx[i][key]:remap for i,layer in enumerate(self.fixed_keys) for key, remap in layer.items()}

        #encode self.specials' keys to indices
        for i,layer in enumerate(self.key2idx):
            for name in self.special_keys:
                if self.special_keys[name][0] in layer:
                    self.special_keys[name][0]=layer[self.special_keys[name][0]]
        # print(self.fixed_keys)
        # print(self.key2idx)
        # print(self.idx2key)
    


    def _validate_keyspace(self):
        """Ensure that available keys can accommodate the layer-specific keybinds."""

        total_base_available = sum(1 for idx in self.available_keys if idx < self.sizes[0])
        total_shift_available = sum(1 for idx in self.available_keys if idx >= self.sizes[0])

        free_slots=total_base_available-len(self.available_ukb)-len(self.available_bkb)+total_shift_available-len(self.available_skb)-len(self.available_ukb)

        assert free_slots>=0, f"\nYOU DON'T HAVE ENOUGH AVAILABLE KEYS FOR ALL THE KEYBINDS ({len(self.available_keys)}<{len(self.available_keybinds)})"


    def _init_keystrokes(self):
        self.keystrokes=[]
        self.total_weights=0
        file_name="keystrokes.json"
        check_required_config_file(file_name)
        missing_w_count=0

        #universal keys(eat the whole key and don't have shift counterparts)
        self.universal_keybinds_set=set()
        self.base_keybinds_set=set()
        self.shift_keybinds_set=set()

        keystrokes_dict=read_json(file_name)

        
        for name, keystroke in keystrokes_dict.items():
            if isinstance(keystroke,list):
                keystrokes_dict[name]={"keys":keystroke,}
                keystroke=keystrokes_dict[name]
            else:
                if "keys" not in keystroke:
                    raise ValueError(f"\nPLEASE ENTER KEYS FOR [{name.upper()}] IN {file_name} FILE FIRST!")
            
            if "weight" in keystroke:
                weight=keystroke["weight"]
                if not isinstance(weight, (int, float)):
                    raise ValueError(f"\nWEIGHT OF KEYSTROKE [{name.upper()}] IN {file_name} FILE MUST BE A NUMBER (NOT {type(weight)})!")
                # keystroke["weight"]=average
                self.total_weights+=weight
            else: missing_w_count+=1



        #second pass of finding the variance of special keys, if not use the default ones
        #it is crucial to find the special keys first before finding the layer of each keybind, because some keybinds are universal and we don't know the name.
        special_variances=Variance().get()

        for key in special_variances:
            for name, keystroke in keystrokes_dict.items():
                for i, k in enumerate(keystroke["keys"]):
                    if k in special_variances[key]:
                        if self.special_keys[key][1]!=k:
                            print(f"WARNING: Key [{k.upper()}] for [{name.upper()}] in keystrokes.json file is different from the one in fixed_keys.json file [{self.special_keys[key][1].upper()}]! Setted it to [{self.special_keys[key][1].upper()}].")
                            keystrokes_dict[name]["keys"][i]=self.special_keys[key][1]
                        else:
                            self.special_keys[key][1]=k
        self.universal_keybinds_set|={self.special_keys['bspc'][1],self.special_keys['spc'][1],self.special_keys['home'][1],self.special_keys['sft'][1]}

        for name, keystroke in keystrokes_dict.items():
            if "layer" in keystroke:
                layer=keystroke["layer"]
                if layer not in ("any","both","base","shift"):
                    raise ValueError(f"\nWEIGHT OF KEYSTROKE [{name.upper()}] IN {file_name} FILE MUST BE EITHER base, shift, both or any (NOT {layer})")
                match layer:
                    case "both":
                        for key in keystroke["keys"]:
                            if key in self.base_keybinds_set:
                                print(f"WARNING: Key [{key.upper()}] for [{name.upper()}] in keystrokes.json file was a base layer keybind, but trying to be both. Setted it to both layer keybind.")
                            elif key in self.shift_keybinds_set:
                                print(f"WARNING: Key [{key.upper()}] for [{name.upper()}] in keystrokes.json file was a shift layer keybind, but trying to be both. Setted it to both layer keybind.")
                            
                            self.universal_keybinds_set.add(key)

                    case "base":
                        for key in keystroke["keys"]:
                            if key in self.shift_keybinds_set:
                                print(f"WARNING: Key [{key.upper()}] for [{name.upper()}] in keystrokes.json file was a shift layer keybind, but trying to be base. Setted it to both layer keybind.")
                                self.universal_keybinds_set.add(key)
                                self.shift_keybinds_set.discard(key)
                            elif key in self.universal_keybinds_set:
                                print(f"WARNING: Key [{key.upper()}] for [{name.upper()}] in keystrokes.json file is a universal keybind, but trying to be base. Skipping it.")
                            else:
                                self.base_keybinds_set.add(key)
                    case "shift":
                        for key in keystroke["keys"]:
                            if key in self.base_keybinds_set:
                                print(f"WARNING: Key [{key.upper()}] for [{name.upper()}] in keystrokes.json file was a base layer keybind, but trying to be shift. Setted it to both layer keybind.")
                                self.universal_keybinds_set.add(key)
                                self.base_keybinds_set.discard(key)
                            elif key in self.universal_keybinds_set:
                                print(f"WARNING: Key [{key.upper()}] for [{name.upper()}] in keystrokes.json file is a universal keybind, but trying to be shift. Skipping it.")
                            else:
                                self.shift_keybinds_set.add(key)
                    case _:
                        pass
                        #acting for any like default

            # self.keystrokes=list(keystrokes_dict.values())

        
        average_w=self.total_weights/(len(keystrokes_dict)-missing_w_count)
        self.total_weights+=missing_w_count*average_w
        self.keystrokes=[]
        for name,keystroke in keystrokes_dict.items():
            if "weight" not in keystroke:
                print(f"WARNING: Keystroke [{name}] in keystrokes.json file doesn't have a weight! Setting it to average value.")
                keystroke["weight"]=average_w

            self.keystrokes.append({"keys":keystroke["keys"],"weight":keystroke["weight"]})


                
                        

        #make 2 version of each keystoke: normal version and start with shift home version
        self.keystrokes+=[{"keys": [self.special_keys['sft'][1], self.special_keys['home'][1]]+keys_n_weight["keys"],"weight":keys_n_weight["weight"]/2} for keys_n_weight in self.keystrokes]
        self.total_weights*=1.5

        #normalize weight
        for i in range(len(self.keystrokes)):
            self.keystrokes[i]["weight"]/=self.total_weights

        # print(self.keystrokes)
        #add home, lsft, chat for safety
        self.keybinds=sorted({key for data in self.keystrokes for key in data['keys']}.union({self.special_keys['home'][1],self.special_keys['sft'][1],self.special_keys['chat'][1]}))
        # print(self.keybinds)
        self.keybind2idx={keybind: i for i,keybind in enumerate(self.keybinds)}

        self.available_keybinds=[i for i, key in enumerate(self.keybinds) if key not in self.fixed_keys.values() and key!=self.special_keys['chat'][1]]


        #special keys
        # self.special_keybinds=[]
        for k in self.special_keys:
            if self.special_keys[k][1] in self.keybind2idx:
                self.special_keys[k][2]=self.keybind2idx[self.special_keys[k][1]]
                # self.special_keybinds.append(self.special_keys[k][1])
        self.universal_keybinds=[self.keybind2idx[keybind] for keybind in self.universal_keybinds_set]
        self.universal_keybinds_set=set(self.universal_keybinds)
        self.available_ukb=[kb_idx for kb_idx in self.universal_keybinds if kb_idx in set(self.available_keybinds)]
        self.base_keybinds=[self.keybind2idx[keybind] for keybind in self.base_keybinds_set]
        self.base_keybinds_set=set(self.base_keybinds)
        self.available_bkb=[kb_idx for kb_idx in self.base_keybinds if kb_idx in set(self.available_keybinds)]
        self.shift_keybinds=[self.keybind2idx[keybind] for keybind in self.shift_keybinds_set]
        self.shift_keybinds_set=set(self.shift_keybinds)
        self.available_skb=[kb_idx for kb_idx in self.shift_keybinds if kb_idx in set(self.available_keybinds)]

        #verify that the available keys can accommodate the layer-specific keybinds
        self._validate_keyspace()

        #frequency of keys
        freq=[0]*len(self.keybinds)
        self.total_keybinds=0
        for data in self.keystrokes:
            for key in data['keys']:
                if key==self.special_keys['sft'][1]: #skip shift
                    continue
                freq[self.keybind2idx[key]]+=data['weight']
                self.total_keybinds+=data['weight']

        # freq[self.keybind2idx[key]]=0

        

        #weighted probability

        # freq[self.keybind2idx[self.chat_name]]+=len(self.keystrokes)*self.total_weights/len(self.keystrokes)
        #Chat probability
        freq[self.keybind2idx[self.special_keys['chat'][1]]]+=average_w/self.total_weights*len(self.keystrokes)
        self.total_keybinds+=average_w/self.total_weights*len(self.keystrokes)
        #Shift probability compute when evalutate
        

        #probability of keys in keystrokes
        self.key_probs=tuple(f/self.total_keybinds for f in freq)


        #turn dict to list and encode into indices
        self.keystrokes=[([self.keybind2idx[key] for key in data["keys"]],data["weight"]) for data in self.keystrokes]
        # print(self.keystrokes)


        #encode fixed keys into keybind indices (if it is in self.keybinds) 
        #keyIdx: keybind --> keyIdx: keybindIdx
        encoded_fixed_keys={}
        for keyIdx, remap in self.fixed_keys.items():
            if remap in self.keybind2idx:
                encoded_fixed_keys[keyIdx]=self.keybind2idx[remap]
            else:
                pass
                # raise ValueError(f"KEYBIND {remap} IN fixed_keys.json FILE IS UNUSED!")
                print(f"WARNING: Keybind {remap} in fixed_keys.json file is unused, skipping it")
        self.fixed_keys=encoded_fixed_keys
        # self.fixed_keys={keyIdx:(self.keybind2idx[remap] if remap in self.keybind2idx else remap) for keyIdx, remap in self.fixed_keys.items()}


    def _init_assigned_keys(self):
        self.assigned_keys={}
        file_name='assigned_fingers.json'
        check_required_config_file(file_name)
        self.assigned_keys=read_json(file_name)


        self.key_idx2finger_idx=[None]*len(self.idx2key)

        for finger, keys in self.assigned_keys.items():
            self._validate_finger(finger,file_name)
            for key in keys:
                
                for i,layer in enumerate(self.key2idx):
                    if key not in layer:
                        continue
                    if self.key_idx2finger_idx[self.key2idx[i][key]] is not None:
                        print(f"WARNING: Finger [{finger.upper()}] is pressing the same key [{key}] as another finger in {file_name}! Skipping it.")
                        continue
                    self.key_idx2finger_idx[self.key2idx[i][key]]=self.finger2idx[finger]
        
        for key_idx, finger_idx in enumerate(self.key_idx2finger_idx):
            if finger_idx is None:
                raise ValueError(f"\nKEY [{self.idx2key[key_idx].upper()}] DOES'T HAVE AN ASSINGED FINGER! PLEASE ASSIGN IT IN {file_name} FILE.")


    def _init_artist(self):
        self.fig, self.ax = plt.subplots(figsize=(6.4,3.6))
        bgc='#13161B'
        tc='#CBF1F5'
        self.fig.patch.set_facecolor(bgc)
        self.ax.set_facecolor(bgc) 
        self.ax.tick_params(colors=tc)
        self.ax.spines["left"].set_color(tc)
        self.ax.spines["right"].set_color(tc)
        self.ax.spines["top"].set_color(tc)
        self.ax.spines["bottom"].set_color(tc)
        self.ax.xaxis.label.set_color(tc)
        self.ax.yaxis.label.set_color(tc)
        self.ax.title.set_color(tc)
        self.ax.set_aspect('equal', adjustable='box')
        self.ax.invert_yaxis()

    def _init_visual(self):
        self.rects=[]
        self.texts=[]
        ec='#3F72AF'
        fc='#00ADB5'
        tc='#E3FDFD'
        stc='#E3FDFD'
        base_x_offset=-0.1
        base_y_offset=-0.1

        shift_x_offset=0.25
        shift_y_offset=0.25
        for key, data in self.keys.items():
            if all(key not in layer for layer in self.key2idx):
                continue
            rect = patches.Rectangle((data._pos.x, data._pos.y), data._width, data._height, 
                         linewidth=0.1, edgecolor=ec, facecolor=fc, alpha=1)
            self.rects.append(rect)
            self.ax.add_patch(rect)

            if key in self.key2idx[0]:
                
                self.texts.append(self.ax.text(data.fpos.x+base_x_offset, data.fpos.y+base_y_offset, self.remaps[0][key] if key in self.remaps[0] else key, 
                    color=tc, fontsize=12, fontweight='bold',
                    ha='center', va='center'))

            #SHIFT LAYER
            if key in self.key2idx[1]:
                self.texts.append(self.ax.text(data.fpos.x+shift_x_offset, data.fpos.y+shift_y_offset, self.remaps[1][key] if key in self.remaps[1] else key, 
                    color=stc, fontsize=8, fontweight='bold',
                    ha='center', va='center'))


        self.ax.autoscale_view()
        Path("output").mkdir(parents=True, exist_ok=True)
        plt.savefig('output/layout.svg')

    def _init_home_keys(self):
        self.home_keys={}
        self.hand=[[],[]] # Initialize two empty lists for left and right hands
        file_name="home_keys.json"
        check_required_config_file(file_name)
        temp_home_keys=read_json(file_name)
        for finger, key in temp_home_keys.items():
            self._validate_finger(finger,file_name)
            self._does_key_exist(key, self.keys, file_name, 'layout.txt')
            found=False
            for i,layer in enumerate(self.key2idx):
                if key not in layer:
                    continue
                self.home_keys[self.finger2idx[finger]]=self.key2idx[i][key]
                found=True
            if found:
                hand_code, finger_code=self.get_finger_roll(self.finger2idx[finger])
                self.hand[hand_code].append(finger_code)
            else:
                print(f"WARNING: Home key [{key}] for finger [{finger}] is not active (not in fixed/available keys), skipping finger.")


        self.hand[0].sort()
        self.hand[1].sort()

        natural_pos={}
        file_name='finger_natural_positions.json'
        check_required_config_file(file_name)
        natural_pos=read_json(file_name)
        self.finger_natural_pos={}
        for finger_idx in self.home_keys:
            hand, finger=self.idx2finger[finger_idx].split('_')
            if hand not in natural_pos:
                raise ValueError(f"\nHAND [{hand.upper()}] IN {file_name} FILE IS INVALID!")
            if finger not in natural_pos[hand]['x']:
                raise ValueError(f"\nFINGER [{finger.upper()}] DOESNT APPEAR IN [{hand.upper()}]:X HAND IN {file_name} FILE!")
            if finger not in natural_pos[hand]['y']:
                raise ValueError(f"\nFINGER [{finger.upper()}] DOESNT APPEAR IN [{hand.upper()}]:Y HAND IN {file_name} FILE!")

            self.finger_natural_pos[finger_idx]=Point(natural_pos[hand]['x'][finger],natural_pos[hand]['y'][finger])

    def _init_parameters(self):
        self.finger_efforts={}
        file_name='parameters.json'
        check_required_config_file(file_name)
        parameters=read_json(file_name)
        if "finger_efforts" not in parameters:
            raise IndexError(f"\nPLEASE ENTER FINGER EFFORTS IN {file_name} FILE FIRST!")
        self.finger_efforts=parameters["finger_efforts"]
        for finger in self.finger_efforts:
            if finger not in self.finger2idx:
                raise ValueError(f"\nFINGER NAME [{finger.upper()}] YOU ASSIGNED IN {file_name}:FINGER_EFFORTS FILE IS INVALID!")
        #encode
        self.finger_efforts={self.finger2idx[finger]: effort for finger, effort in self.finger_efforts.items()}

    def _init_max_finger_dists(self): #need init finger roll first
        tfinger_dists={}
        file_name='max_finger_distances.json'
        check_required_config_file(file_name)
        tfinger_dists=read_json(file_name)

        self.finger_dists={} #THIS USE FINGER CODE AND HAND CODE AS INDEX SYSTEM (SAME WITH FINGER_CODE, HAND_CODE) NOT THE FINGER_IDX SYSTEM (SAME WITH finger2idx)
        for FF, dist in tfinger_dists.items():
            x, y=FF.split('_')
            assert x in self.FINGER_CODE and y in self.FINGER_CODE, f"\nFINGER NAMES [{FF.upper()}] IN {file_name} FILE ARE INVALID!"
            self.finger_dists[(self.FINGER_CODE[x],self.FINGER_CODE[y])]=dist
            self.finger_dists[(self.FINGER_CODE[y],self.FINGER_CODE[x])]=dist


    def _precompute(self):
        self.key_sq_dists=tuple([distance_sq(self.keys[self.idx2key[i]].fpos,self.keys[self.idx2key[j]].fpos) for i in range(len(self.idx2key))] for j in range(len(self.idx2key))) #SQUARE OF DISTANCE BETWEEN KEYS, USE KEY_IDX AS INDEX SYSTEM

        # PRECOMPUTING MAXIMUM DISTANCE FOR PRINCIPLED GEOMETRIC PENALTIES
        self.max_sq_dist = max(max(row) for row in self.key_sq_dists)

        #finger strain heapmap
        self.strain_heapmap=[]

        for key_idx in range(len(self.idx2key)):
            finger_idx=self.key_idx2finger_idx[key_idx]
            anchor_dist_sq=self.key_sq_dists[key_idx][self.home_keys[finger_idx]]
            self.strain_heapmap.append(anchor_dist_sq*self.finger_efforts[finger_idx])
        self.strain_heapmap=tuple(self.strain_heapmap)
        #available only strain heapmap, cumulate them, flatten out
        FLATTEN_STRENGTH=0.5
        self.cum_avai_strain_heapmap=[]
        last_strain=0
        for k in self.available_keys:
            last_strain=self.strain_heapmap[k]**FLATTEN_STRENGTH+last_strain
            self.cum_avai_strain_heapmap.append(last_strain)

        self.cum_avai_strain_heapmap=tuple(self.cum_avai_strain_heapmap)

        #TODO: precompute FS factors



    
            
    #GETTERS
    def get_finger_roll(self, finger_idx): #THIS FUNCTION RETURNS DIFFERENT INDEX SYSTEM (SAME WITH FINGER_CODE, HAND_CODE)
        hand_code=finger_idx//5
        finger_code=finger_idx%5
        return hand_code, finger_code

    def get_finger_idx(self, hand_code, finger_code): #THIS FUNCTION TAKES IN DIFFERENT INDEX SYSTEM (SAME WITH FINGER_CODE, HAND_CODE)
        return hand_code*5+finger_code

    def display(self, potential_remaps:list, scores:tuple=(), name='layout'):
        for i in range(len(self.texts)):
            self.texts[i].remove()
        self.texts=[]
        base_x_offset=-0.1
        base_y_offset=-0.1
        tc='#EEEEEE'

        for keyIdx, remapIdx in enumerate(potential_remaps):
            if remapIdx is None:
                continue
            key=self.idx2key[keyIdx]
            remap=self.keybinds[remapIdx]
            if keyIdx<self.sizes[0]:
                self.texts.append(self.ax.text(self.keys[key].fpos.x+base_x_offset, self.keys[key].fpos.y+base_y_offset, remap, 
                    color=tc, fontsize=12, fontweight='bold',
                    ha='center', va='center'))
            else:
                self.texts.append(self.ax.text(self.keys[key].fpos.x+0.25, self.keys[key].fpos.y+0.25, remap, 
                    color=tc, fontsize=8, fontweight='bold',
                    ha='center', va='center'))


        title=''
        for metric_name, metric_score in scores:
            abbreviated=''
            for w in metric_name.split("_"):
                abbreviated+=w[0].upper()
            title+=f"{abbreviated}: {round(metric_score,2)}, "
        self.ax.set_title(title[:-2])
        self.ax.autoscale_view()
        plt.savefig(f'output/{name}.svg')





if __name__=="__main__":

    l=Layout()
    
    print("Layout:",list(l.keys.keys()))
    print("Shift key:", l.special_keys['sft'][0],l.special_keys['sft'][1])
    print("Chat key:",l.special_keys['chat'][0])
    print("Fixed keys (Multiple layers):",[(l.idx2key[key],l.keybinds[remap]) for key, remap in l.fixed_keys.items()])
    print("Remaps:", [[(key,remap) for key,remap in layer.items()] for layer in l.remaps])
    print("Available keys:", [l.idx2key[key] for key in l.available_keys])
    print("Key positions: (Multiple layers)", [(l.idx2key[i],pos) for i, pos in enumerate(l.key_positions)])
    print("Keystrokes:", [[l.keybinds[key] for key in keystroke[0]]for keystroke in l.keystrokes])
    print("Available keybinds:", [l.keybinds[key] for key in l.available_keybinds])
    print("Keybind probability:", [(l.keybinds[i],round(prob,2)) for i,prob in enumerate(l.key_probs)])
    print("Universal keybinds:", [l.keybinds[key] for key in l.universal_keybinds])
    print("Base keybinds:", [l.keybinds[key] for key in l.base_keybinds])
    print("Shift keybinds:", [l.keybinds[key] for key in l.shift_keybinds])
    # print("Available special keybinds:", [l.keybinds[key] for key in l.available_skb])
    # print("Assiged finger:")
    #TODO: continue