import importlib.util
import subprocess
import sys

def install(package_to_install):
    if importlib.util.find_spec(package_to_install) is None:
        print(f"WARNING: {package_to_install} not found. Installing... this may take a while.")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_to_install])

def install_dependencies():
    install("matplotlib")
    install("numpy")
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
CONFIG_DIR = ROOT_DIR / "config"
OUTPUT_DIR = ROOT_DIR / "output"

def has_no_whitespace(text: str) -> bool:
    return not any(char.isspace() for char in text)

def read_json(file_name):
    """Read JSON file."""
    try:
        with open(CONFIG_DIR / file_name, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as e:
        print(f"\nSYNTAX ERROR IN {file_name} FILE: {e}")
        raise SystemExit

def write_json(file_name, data):
    """Write JSON file."""
    with open(CONFIG_DIR / file_name, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

def read_text_rows(file_name):
    """Read space-separated rows from text file."""
    with open(CONFIG_DIR / file_name, "r", encoding="utf-8") as file:
        return [[token for token in line.strip().split() if token] for line in file if line.strip()]

def write_text_rows(file_name, rows):
    """Write rows as space-separated lines."""
    with open(CONFIG_DIR / file_name, "w", encoding="utf-8") as file:
        for row in rows:
            line = " ".join(str(token) for token in row)
            file.write(line + "\n")



def AABB(pos1, width1, height1, pos2, width2, height2):
    return (pos1.x < pos2.x + width2 and
            pos1.x + width1 > pos2.x and
            pos1.y < pos2.y + height2 and
            pos1.y + height1 > pos2.y)

    
def check_config_file(name):
    a=Path(f"config/{name}")

    return a.exists()

def check_required_config_file(name):
    if not check_config_file(name):
        raise FileNotFoundError(f"\aREQUIRED FILE {name.upper()} IN CONFIG FOLDER IN ORDER TO RUN THIS SCRIPT!")

def distance_sq(pos1, pos2): #special distance
    x=(pos1.x-pos2.x)*1.25
    y=pos1.y-pos2.y
    return x**2+y**2
class Variance:
    def get(self):
        return {
            'bspc':{'bspc','backspace','bs','<'},
            'spc':{'sp','space','spc','_'},
            'sft': {'sft','lsft','shift','rsft','lshift', 'rshift'},
            'chat': {'chat'},
            'home': {'home', 'hm'},
        }

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
            raise ValueError(f"\nKEY [{key.upper()}] YOU ASSIGNED IN {file} FILE DOESN'T APPEAR IN {root_file} FILE!")
        return True

    def _is_key_correct_type(self,key: str, file):
        if not isinstance(key,str):
            raise TypeError(f"\nKEY [{key.upper()}] YOU ASSIGNED IN {file} FILE HAS INCORRECT TYPE, IT NEEDS TO BE STRING NOT ({type(key)})!")
        if not has_no_whitespace(key):
            raise ValueError(f"\nKEY [{key.upper()}] YOU ASSIGNED IN {file} FILE HAS INCORRECT FORMAT, MAYBE IT CONTAINS WHITESPACES!")

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

            write_text_rows("available_keys.txt",available_keys)
            write_text_rows("available_shift_keys.txt",available_shift_keys)

        if save_custom_keys:
            check_required_config_file("custom_keys.json")
            custom_keys={k:v for k,v in custom_keys.items() if v}
            write_json("custom_keys.json", custom_keys)
        if save_layout:
            check_required_config_file("layout.txt")
            write_text_rows("layout.txt", layout)