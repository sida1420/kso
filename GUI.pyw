import ctypes
import os
import platform
import queue
import subprocess
import sys
import threading
import tkinter as tk
import traceback
from tkinter import messagebox, ttk


from classes import *
from helper import *


class KeySlot(Key):

    def __init__(self, lx, uy, width=1,height=1, offset=0, active_base=False, active_shift=False, fixed_base=None, fixed_shift=None):
        super().__init__(lx, uy, width, height, offset)
        self._active_base=active_base
        self._active_shift=active_shift
        self._fixed_base=fixed_base
        self._fixed_shift=fixed_shift

class ConfigModel(Validator):
    def __init__(self):
        super().__init__()
        self.load_layout()
        self.load_available_keys()
        self.load_fixed_keys()
        self.load_assigned_fingers()
        self.load_keystrokes()
        self.used_settings=['generation_limit','dev_mode','auto_generate_shift_home']
        self.default_settings=[3000,False,0]
        self.load_options()
        

    def load_layout(self):
        custom_keys=read_json("custom_keys.json")
        layout=read_text_rows("layout.txt")
        self.organizer=AdvLayoutOrganizer()
        self.organizer.load_layout(layout, custom_keys)
    
    def save_layout(self, save_available_keys=False):
        if save_available_keys:
            self.organizer.save(available_keys_set=self.available_keys, available_shift_keys_set=self.available_shift_keys)

        else:
            self.organizer.save()

    def load_available_keys(self):
        check_required_config_file("available_keys.txt")
        self.available_keys = {name for row in read_text_rows("available_keys.txt") for name in row}
        for key in self.available_keys:
            self._does_key_exist(key, self.organizer.keys,"available_keys.txt","layout.txt")
        check_required_config_file("available_shift_keys.txt")
        self.available_shift_keys = {name for row in read_text_rows("available_shift_keys.txt") for name in row}
        for key in self.available_shift_keys:
            self._does_key_exist(key, self.organizer.keys,"available_shift_keys.txt","layout.txt")

    def save_available_keys(self):
        self.organizer.save(False,False, available_keys_set=self.available_keys, available_shift_keys_set=self.available_shift_keys)

    def load_fixed_keys(self):
        check_required_config_file("fixed_keys.json")
        self.fixed_keys = read_json("fixed_keys.json")
        self.chat=None
        special_variances=Variance().get()
        for key, remap in self.fixed_keys.items():
            self._is_key_correct_type(key,"fixed_keys.json")
            if isinstance(remap, str):
                if remap in special_variances['chat']:
                    self.chat=key
            elif isinstance(remap, list):
                if remap[0] in special_variances['chat'] or remap[1] in special_variances['chat']:
                    self.chat=key
            else:
                raise TypeError(f"\nKEY SLOT [{key.upper()}] YOU ASSIGNED IN fixed_keys.json FILE HAS INCORRECT TYPE, IT NEEDS TO BE STRING OR LIST FOR CHAT NOT ({type(remap)})!")



            self._does_key_exist(key, self.organizer.keys,"fixed_keys.json","layout.txt")
        
        if self.chat is not None:
            if isinstance(self.fixed_keys[self.chat], str):
                self.fixed_keys.pop(self.chat)
            elif isinstance(self.fixed_keys[self.chat], list):
                if len(self.fixed_keys[self.chat])==1:
                    self.fixed_keys.pop(self.chat)
                elif self.fixed_keys[self.chat][0] in special_variances['chat']:
                    self.fixed_keys[self.chat]=self.fixed_keys[self.chat][1]
                elif self.fixed_keys[self.chat][1] in special_variances['chat']:
                    self.fixed_keys[self.chat]=self.fixed_keys[self.chat][0]
        check_required_config_file("fixed_shift_keys.json")
        self.fixed_shift_keys = read_json("fixed_shift_keys.json")
        for key, remap in self.fixed_shift_keys.items():
            self._is_key_correct_type(key,"fixed_shift_keys.json")
            self._is_key_correct_type(remap,"fixed_shift_keys.json")
            self._does_key_exist(key, self.organizer.keys,"fixed_shift_keys.json","layout.txt")

    def load_assigned_fingers(self):
        file_name="assigned_fingers.json"
        check_required_config_file(file_name)
        self.assigned_fingers=read_json(file_name)
        for finger, keys in self.assigned_fingers.items():
            self._validate_finger(finger, file_name)
            for key in keys:
                self._is_key_correct_type(key, file_name)
                self._does_key_exist(key, self.organizer.keys,file_name, "layout.txt")

        file_name="home_keys.json"
        check_required_config_file(file_name)
        self.home_keys=read_json("home_keys.json")
        for finger, key in self.home_keys.items():
            self._validate_finger(finger, file_name)
            self._is_key_correct_type(key, file_name)
            self._does_key_exist(key, self.organizer.keys, file_name, "layout.txt")

    def save_assigned_fingers(self):
        write_json("assigned_fingers.json",self.assigned_fingers)
        write_json("home_keys.json",self.home_keys)

    def save_fixed_keys(self):
        temp_fixed_keys = self.fixed_keys.copy()
        if self.chat is not None:
            if self.chat not in temp_fixed_keys:
                temp_fixed_keys[self.chat] = "chat"
            else:
                temp_fixed_keys[self.chat]=[temp_fixed_keys[self.chat],"chat"]
        write_json("fixed_keys.json", temp_fixed_keys)
        write_json("fixed_shift_keys.json", self.fixed_shift_keys)

    def load_keystrokes(self):
        file_name="keystrokes.json"
        check_required_config_file(file_name)
        temp_keystrokes=read_json(file_name)
        self.keystrokes={}
        for name, values in temp_keystrokes.items():
            if isinstance(values,list):
                values={"keys": values,}
            if "keys" not in values:                    
                raise ValueError(f"\nPLEASE ENTER KEYS FOR [{name.upper()}] IN {file_name} FILE FIRST!")
            
            for key in values["keys"]:
                self._is_key_correct_type(key,file_name)
            if "weight" in values:
                weight=values["weight"]
                if not isinstance(weight, (int, float)):
                    raise ValueError(f"\nWEIGHT OF KEYSTROKE [{name.upper()}] IN {file_name} FILE MUST BE A NUMBER (NOT {type(weight)})!")
            else:
                values["weight"]=None

            if "layer" not in values:
                values["layer"]="any"
            else:
                layer=values["layer"]
                if layer not in ("any","both","base","shift"):
                    raise ValueError(f"\nWEIGHT OF KEYSTROKE [{name.upper()}] IN {file_name} FILE MUST BE EITHER base, shift, both or any (NOT {layer})")
            self.keystrokes[name]=values

    def save_keystrokes(self):
        temp_keystrokes={}
        for name, values in self.keystrokes.items():
            if len(values)==1 and "keys" in values:
                values=values["keys"]
            else:
                if values["weight"] is None:
                    del values["weight"]

            temp_keystrokes[name]=values

        write_json("keystrokes.json", temp_keystrokes)

    def load_options(self):
        file_name="settings.json"
        check_required_config_file(file_name)
        temp_settings=read_json(file_name)
        self.settings={}
        for k, d in zip(self.used_settings,self.default_settings):
            v = temp_settings.get(k,d)

            self.settings[k]=v
            

        file_name="target_metrics.json"
        check_required_config_file(file_name)
        self.target_metrics=read_json(file_name)

    def save_options(self):
        file_name="settings.json"
        check_required_config_file(file_name)
        temp_settings=read_json(file_name)
        for k in self.used_settings:
            temp_settings[k]=self.settings[k]
        
        write_json("settings.json", temp_settings)
        write_json("target_metrics.json", self.target_metrics)
        
    def add_key(self):
        return self.organizer.new_key()
    def remove_key(self, key):
        self.organizer.remove_key(key)
    def get_key(self, key) -> Key:
        return self.organizer.keys[key]
    def all_keys(self):
        return list(self.organizer.keys.keys())
    

class KeyboardCanvas(tk.Canvas):
    FINGER_PALETTE = (
        "#a85a5a",  # 0  muted red
        "#b8a030",  # 1  dark gold
        "#5a9e5a",  # 2  muted green
        "#4a9e9e",  # 3  muted cyan
        "#5a7a9e",  # 4  muted blue
        "#9e5a8e",  # 5  muted magenta
        "#9e7a4a",  # 6  muted orange
        "#8a9e5a",  # 7  muted olive
        "#4a9e7a",  # 8  muted sea green
        "#7a5a9e",  # 9  muted purple
    )
    def __init__(self, parent, model: ConfigModel, mode="layout", **kwargs):
        super().__init__(parent, bg="#181a1f", highlightthickness=0, **kwargs)
        self.model=model
        self.mode=mode

        self._scale=60
        self.margin=8

        self.snap_step=0.25
        self.selected=None
        self.dragging=False
        self.drag_anchor=None
        self.drag_offset_x=0
        self.drag_offset_y=0
        self.original_pos=None
        self.show_labels=True
        self.show_all_labels=False


        #??
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.redraw()
        
    def set_mode(self,mode):
        self.mode=mode
        self.redraw()
    
    def set_view_options(self, show_labels=True, show_all_labels=False):
        self.show_labels = show_labels
        self.show_all_labels = show_all_labels
        self.redraw()

    def snap(self, val):
        return round(val/self.snap_step)*self.snap_step

    def redraw(self):
        self.delete("all")
        keys=self.model.organizer.keys
        if not keys:
            self.config(width=300,height=200)
            return

        max_x=max(key._pos.x+key._width for key in keys.values())+1
        max_y=max(key._pos.y+key._height for key in keys.values())+1
        width_px=int(max_x*self._scale+self.margin*2)
        height_px=int(max_y*self._scale+self.margin*2)
        self.config(width=width_px, height=height_px)

        for name in sorted(keys.keys(),key=lambda x: (keys[x]._pos.y, keys[x]._pos.x)):
            
            self.draw_key(name,keys[name])

    def _finger_color(self, name):
        fingers=list(self.model.assigned_fingers.keys())
        for idx, finger in enumerate(fingers):
            if name in self.model.assigned_fingers[finger]:
                return self.FINGER_PALETTE[idx%len(self.FINGER_PALETTE)]
        return None

    def draw_key(self, name, key: Key):
        x0=self.margin+key._pos.x*self._scale
        y0=self.margin+key._pos.y*self._scale
        x1=x0+key._width*self._scale
        y1=y0+key._height*self._scale

        #Fill color
        fill="#2f343f"
        if self.mode=="finger":
            color=self._finger_color(name)
            if color:
                fill=color
        
        if name==self.selected:
            fill="#70c0ff"
        
        #Main rectangle

        outline="#ffffff" if name==self.selected else "#bdd5ed"
        width=2 if name== self.selected else 1
        self.create_rectangle(x0,y0,x1,y1, fill=fill, outline=outline, width=width, tags=("key", name))

        #Layout mode: Triangles
        if self.mode=="layout":
            if name in self.model.available_keys:
                self.create_polygon(x0,y0,x1,y0,x0,y1, fill="#4a90e2",tags=("keys",name))
            if name in self.model.available_shift_keys:
                self.create_polygon(x1, y1, x1, y0, x0, y1, fill="#ffb86c", tags=("keys", name))
        

        # Fixed mode: show remapping text
        if self.mode == "fixed":
            if name == self.model.chat:
                self.create_text(x0 + 4, y0 + 4, text="CHAT", anchor="nw",
                    fill="#ff79c6", font=("Arial", 10, "bold"), tags=("key", name))
            if not self.show_all_labels and not self.show_labels:
                if name in self.model.fixed_keys:
                    self.create_text((x0+x1)/2,(y0+y1)/2,text=self.model.fixed_keys[name],
                        fill="#f8f8f2", font=("Arial", 10, "bold"), tags=("key", name))
                if name in self.model.fixed_shift_keys:
                    self.create_text(x1-(x1-x0)/10,y1-(y1-y0)/10,text=self.model.fixed_shift_keys[name],
                        fill="#f8f8f2", font=("Arial", 8), anchor="se", tags=("key", name))

        #Layout/ finger modes/fixed mode: names
        if self.mode in ["layout", "finger", "fixed"]:
            label = name if (self.show_labels or self.show_all_labels or self.mode == "finger") else ""
            if label:
                label_x = (x0 + x1) / 2 + key._offset * self._scale
                underline=0
                if self.mode=="finger" and name in self.model.home_keys.values():
                    underline=1
                self.create_text(label_x, (y0 + y1) / 2, text=label, fill="#f8f8f2", font=("Arial", 10, "bold underline" if underline else "bold"), tags=("key", name))
    def identify_slot(self, event):
        """Identify key at event"""
        items = self.find_overlapping(event.x, event.y, event.x, event.y)
        for item in items:
            tags = self.gettags(item)
            for tag in tags:
                if tag != "key":
                    return tag
        current = self.find_withtag("current")
        if current:
            tags = self.gettags(current[0])
            for tag in tags:
                if tag != "key":
                    return tag
        return None

    def on_click(self, event):
        """Click handler"""
        name = self.identify_slot(event)
        if name:
            self.selected = name
            if self.mode == "layout":
                self.dragging = False
                self.drag_anchor = (event.x, event.y)
                key = self.model.get_key(name)
                if key:
                    self.drag_offset_x = event.x - (self.margin + key._pos.x * self._scale)
                    self.drag_offset_y = event.y - (self.margin + key._pos.y * self._scale)
                    self.original_pos = key._pos
            self.redraw()
            self.event_generate("<<KeySlotSelected>>")
        else:
            if self.selected:
                self.selected = None
                self.redraw()
                self.event_generate("<<KeySlotSelected>>")
    def on_drag(self, event):
        if self.mode != "layout" or not self.selected:
            return

        key = self.model.get_key(self.selected)
        if not key or not self.drag_anchor:
            return

        
        ax, ay = self.drag_anchor
        if not self.dragging and abs(event.x - ax) + abs(event.y - ay) <= 1:
            return
        
        self.dragging = True

        drag_x=event.x-self.drag_offset_x
        drag_y=event.y-self.drag_offset_y
        

        # compute continuous position then snap to configured step
        val_x = (drag_x - self.margin) / self._scale
        val_y = (drag_y - self.margin) / self._scale
        try:
            step = float(self.snap_step)
            if step <= 0:
                step = 1.0
        except Exception:
            step = 1.0

        new_x = max(self.model.organizer.left_most_x, self.snap(val_x))
        new_y = max(self.model.organizer.left_most_y, self.snap(val_y))

        key.set_pos(Point(new_x,new_y))
        self.redraw()
        self.event_generate("<<KeySlotMoved>>")

    def on_release(self, event):
        did_drag = self.dragging
        self.dragging=False
        self.drag_anchor=None

        if self.mode != "layout" or not self.selected or not self.original_pos or not did_drag:
            self.redraw()
            return

        key = self.model.get_key(self.selected)

        if not key:
            return

        swap_target=None
        block=False

        for name, other in self.model.organizer.keys.items():
            if name == self.selected:
                continue

            overlap_x = min(key._pos.x + key._width, other._pos.x + other._width) - max(key._pos.x, other._pos.x)
            if overlap_x<=0:
                continue
            overlap_y = min(key._pos.y + key._height, other._pos.y + other._height) - max(key._pos.y, other._pos.y)
            if overlap_y<=0:
                continue

            overlap = overlap_x * overlap_y

            if overlap<key._width*key._height*0.95 or key._width!=other._width or key._height!=other._height:
                block=True
            else:
                swap_target=other
                break

        if swap_target is not None:
            key.set_pos(swap_target._pos)
            swap_target.set_pos(self.original_pos)
        elif block:
            key.set_pos(self.original_pos)

        self.original_pos=None
        self.redraw()
        self.event_generate("<<KeySlotMoved>>")


    def get_selected_key(self):
        if not self.selected:
            return None
        if self.selected not in self.model.organizer.keys:
            return None
        return self.model.organizer.keys[self.selected]

    def set_selected(self, name):
        self.selected=name
        self.redraw()


class GUI(tk.Tk):

    def __init__(self):
        super().__init__()

        self.title("KSO")

        self.geometry("1400x720")
        self.minsize(1160,600)

        self._setup_theme()
        self.model=ConfigModel()
        self.shift_pressed=False
        self.process=None
        self.output_queue=queue.Queue()
        self.current_keystroke = None
        self.new_selected_keystroke= None
        self._poll_id=None

        self._setup_ui()

        self.bind_all("<KeyPress-Shift_L>", self._on_shift_press)
        self.bind_all("<KeyPress-Shift_R>", self._on_shift_press)
        self.bind_all("<KeyRelease-Shift_L>", self._on_shift_release)
        self.bind_all("<KeyRelease-Shift_R>", self._on_shift_release)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._poll_queue()


    def _setup_theme(self):
        """Setup dark theme."""
        bg = "#12141a"
        fg = "#e6e6e6"
        field_bg = "#1b1f28"
        accent_bg = "#1f242c"
        select_bg = "#29323b"
        active_bg = "#343e49"

        self.configure(bg=bg)

        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        # General Layout
        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=fg)

        # Buttons & Interaction
        style.configure("TButton", background=accent_bg, foreground=fg, borderwidth=1, relief="flat")
        style.map("TButton",
            background=[("active", active_bg), ("disabled", "#161920")],
            foreground=[("disabled", "#555b6e")]
        )

        # Text Entries (insertcolor sets the text cursor color)
        style.configure("TEntry", fieldbackground=field_bg, background=field_bg, foreground=fg, insertcolor=fg)

        # Checkbuttons (prevents flashing white on hover/click)
        style.configure("TCheckbutton", background=bg, foreground=fg)
        style.map("TCheckbutton",
            background=[("active", bg)],
            foreground=[("active", fg)]
        )

        # LabelFrames
        style.configure("TLabelframe", background=bg, foreground=fg)
        style.configure("TLabelframe.Label", background=bg, foreground=fg)

        # Notebook Tabs
        style.configure("TNotebook", background=bg, borderwidth=0)
        style.configure("TNotebook.Tab", background=field_bg, foreground=fg, padding=[8, 4])
        style.map("TNotebook.Tab", background=[("selected", select_bg)])

        # Treeview
        style.configure("Treeview", background=field_bg, foreground=fg, fieldbackground=field_bg, borderwidth=0)
        style.configure("Treeview.Heading", background=accent_bg, foreground=fg, relief="flat")
        style.map("Treeview",
            background=[("selected", select_bg)],
            foreground=[("selected", fg)]
        )
        style.map("Treeview.Heading",
            background=[("active", active_bg)]
        )

        # Combobox
        style.configure("TCombobox", fieldbackground=field_bg, background=field_bg, foreground=fg, insertcolor=fg, arrowcolor=fg)
        style.map("TCombobox", fieldbackground=[("readonly", field_bg), ("active", field_bg)])
        self.option_add("*TCombobox*Listbox.background", field_bg)
        self.option_add("*TCombobox*Listbox.foreground", fg)
        self.option_add("*TCombobox*Listbox.selectBackground", select_bg)
        self.option_add("*TCombobox*Listbox.selectForeground", fg)

    def _setup_ui(self):
        """Setup 5-tab interface."""
        self.notebook= ttk.Notebook(self)

        self.notebook.pack(fill="both",expand=True, padx=8, pady=8)

        self._create_layout_tab()
        self._create_fixed_tab()
        self._create_finger_tab()
        self._create_keystrokes_tab()
        self._create_options_tab()
        self._create_run_tab()


        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _create_layout_tab(self):

        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Layout")        
        left = ttk.Frame(frame)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        right = ttk.Frame(frame)
        right.pack(side="left", fill="y")

        self.layout_canvas = KeyboardCanvas(left, self.model, mode="layout")

        self.layout_canvas.pack(fill="both", expand=True)
        self.layout_canvas.bind("<<KeySlotSelected>>", lambda e: self._refresh_layout())
        self.layout_canvas.bind("<<KeySlotMoved>>", lambda e: self._refresh_layout())

        editor = ttk.Labelframe(right, text="Selected Key")
        editor.pack(fill="x", pady=(0, 8))

        self.layout_sel_label = ttk.Label(editor, text="None")
        self.layout_sel_label.pack(anchor="w", padx=6, pady=4)

        self.layout_fields = {}
        for fname, flabel in [("x", "X"), ("y", "Y"), ("width", "Width"), ("height", "Height"), ("offset", "Offset")]:
            f = ttk.Frame(editor)
            f.pack(fill="x", padx=6, pady=2)
            ttk.Label(f, text=flabel + ":", width=10).pack(side="left")
            var = tk.StringVar()
            var.trace_add("write", lambda *a, fn=fname: self._on_layout_field_changed(fn))
            self.layout_fields[fname] = var
            ttk.Entry(f, textvariable=var, width=20).pack(side="left", fill="x", expand=True)

        self.layout_active_base = tk.BooleanVar()
        self.layout_active_shift = tk.BooleanVar()
        # Snap step control
        f = ttk.Frame(right)
        f.pack(fill="x", padx=6, pady=2)
        ttk.Label(f, text="Snap:", width=10).pack(side="left")
        self.snap_var = tk.StringVar(value=str(self.layout_canvas.snap_step))
        self.snap_var.trace_add("write", lambda *a: self._on_snap_changed())
        ttk.Entry(f, textvariable=self.snap_var, width=20).pack(side="left", fill="x", expand=True)

        ttk.Checkbutton(editor, text="Active base", variable=self.layout_active_base, command=self._on_layout_active_changed).pack(anchor="w", padx=6, pady=2)
        ttk.Checkbutton(editor, text="Active shift", variable=self.layout_active_shift, command=self._on_layout_active_changed).pack(anchor="w", padx=6, pady=2)

        self.delete_key_button=ttk.Button(right, text="Delete Key", command=self._delete_layout_key, state="disabled")
        self.delete_key_button.pack(fill="x", padx=6, pady=2)
        ttk.Button(right, text="Add Key", command=self._add_layout_key).pack(fill="x", padx=6, pady=2)
        ttk.Button(right, text="Reload", command=self._reload_layout).pack(fill="x", padx=6, pady=2)
        ttk.Button(right, text="Save", command=self._save_layout).pack(fill="x", padx=6, pady=2)


    def _create_fixed_tab(self):

        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Fixed Keys")

        left = ttk.Frame(frame)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        right = ttk.Frame(frame)
        right.pack(side="left", fill="y")

        self.fixed_canvas = KeyboardCanvas(left, self.model, mode="fixed")
        self.fixed_canvas.pack(fill="both", expand=True)
        self.fixed_canvas.set_view_options(show_labels=False)
        self.fixed_canvas.bind("<<KeySlotSelected>>", lambda e: self._refresh_fixed())

        editor = ttk.Labelframe(right, text="Fixed Assignment")
        editor.pack(fill="x", pady=(0, 8))

        self.fixed_sel_label = ttk.Label(editor, text="None")
        self.fixed_sel_label.pack(anchor="w", padx=6, pady=4)

        f = ttk.Frame(editor)
        f.pack(fill="x", padx=6, pady=2)
        ttk.Label(f, text="Base:", width=10).pack(side="left")
        self.fixed_base_var = tk.StringVar()
        self.fixed_base_var.trace_add("write", lambda *a: self._on_fixed_changed("base"))
        ttk.Entry(f, textvariable=self.fixed_base_var, width=20).pack(side="left", fill="x", expand=True)
        
        f = ttk.Frame(editor)
        f.pack(fill="x", padx=6, pady=2)
        ttk.Label(f, text="Shift:", width=10).pack(side="left")
        self.fixed_shift_var = tk.StringVar()
        self.fixed_shift_var.trace_add("write", lambda *a: self._on_fixed_changed("shift"))
        ttk.Entry(f, textvariable=self.fixed_shift_var, width=20).pack(side="left", fill="x", expand=True)

        # Chat identifier checkbox
        self.fixed_chat_var = tk.BooleanVar()
        self.fixed_chat_var.trace_add("write", lambda *a: self._on_fixed_changed("chat"))
        ttk.Checkbutton(editor, text="Chat key", variable=self.fixed_chat_var).pack(anchor="w", padx=6, pady=2)
        
        self.remove_fixed_button=ttk.Button(right, text="Remove", command=self._remove_fixed, state="disabled")
        self.remove_fixed_button.pack(fill="x", padx=6, pady=2)
        ttk.Button(right, text="Reload", command=self._reload_fixed).pack(fill="x", padx=6, pady=2)
        ttk.Button(right, text="Save", command=self._save_fixed).pack(fill="x", padx=6, pady=2)
            

            
    def _create_finger_tab(self):
        """Finger assignment tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Finger Assignment")
        
        left = ttk.Frame(frame)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        right = ttk.Frame(frame)
        right.pack(side="left", fill="y")
        
        self.finger_canvas = KeyboardCanvas(left, self.model, mode="finger")
        self.finger_canvas.pack(fill="both", expand=True)
        self.finger_canvas.bind("<<KeySlotSelected>>", lambda e: self._refresh_finger())
        
        editor = ttk.Labelframe(right, text="Finger Assignment")
        editor.pack(fill="x", pady=(0, 8))
        
        self.finger_sel_label = ttk.Label(editor, text="None")
        self.finger_sel_label.pack(anchor="w", padx=6, pady=4)
        
        f = ttk.Frame(editor)
        f.pack(fill="x", padx=6, pady=2)
        ttk.Label(f, text="Finger:", width=12).pack(side="left")
        self.finger_select_var = tk.StringVar()
        self.finger_select_var.trace_add("write", lambda *a: self._on_finger_selected())
        self.finger_combo = ttk.Combobox(f, textvariable=self.finger_select_var, width=24)
        self.finger_combo.pack(side="left", fill="x", expand=True)
        
        self.home_key_var = tk.BooleanVar()
        self.home_key_var.trace_add("write", lambda *a: self._on_home_key_changed())
        ttk.Checkbutton(editor, text="Home key", variable=self.home_key_var).pack(anchor="w", padx=6, pady=2)
        
        legend = ttk.Labelframe(editor, text="Colors")
        legend.pack(fill="x", padx=6, pady=(8, 4))
        for idx, finger in enumerate(self.model.assigned_fingers.keys()):
            color = KeyboardCanvas.FINGER_PALETTE[idx % len(KeyboardCanvas.FINGER_PALETTE)]
            row = ttk.Frame(legend)
            row.pack(fill="x", padx=4, pady=1)
            color_box = tk.Label(row, width=2, background=color)
            color_box.pack(side="left", padx=(0, 4))
            ttk.Label(row, text=finger).pack(side="left")
        
        self.remove_from_finger_button=ttk.Button(right, text="Remove from finger", command=self._remove_key_from_finger, state="disabled")
        self.remove_from_finger_button.pack(fill="x", padx=6, pady=2)
        ttk.Button(right, text="Reload", command=self._reload_finger).pack(fill="x", padx=6, pady=2)
        ttk.Button(right, text="Save", command=self._save_finger).pack(fill="x", padx=6, pady=2)
    
    def _create_keystrokes_tab(self):
        """Keystrokes editor tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Keystrokes")
        
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill="x", padx=8, pady=8)
        ttk.Button(toolbar, text="Reload", command=self._reload_keystrokes).pack(side="left")
        ttk.Button(toolbar, text="Save", command=self._save_keystrokes).pack(side="left", padx=(4, 0))
        ttk.Button(toolbar, text="Add Keystroke", command=self._add_keystroke).pack(side="left", padx=(4,0))
        self.delete_keystroke_button=ttk.Button(toolbar, text="Remove Keystroke", command=self._delete_keystroke, state="disabled")
        self.delete_keystroke_button.pack(side="left",padx=(4,0))
        
        self.keystroke_tree = ttk.Treeview(frame, columns=("name", "weight", "layer", "keys"), show="headings", height=15)
        self.keystroke_tree.heading("name", text="Name")
        self.keystroke_tree.heading("weight", text="Weight")
        self.keystroke_tree.heading("layer", text="Layer")
        self.keystroke_tree.heading("keys", text="Keys")
        self.keystroke_tree.column("name", width=150)
        self.keystroke_tree.column("weight", width=80)
        self.keystroke_tree.column("layer", width=100)
        self.keystroke_tree.column("keys", width=500)
        self.keystroke_tree.pack(fill="both", expand=True, padx=8, pady=4)
        self.keystroke_tree.bind("<<TreeviewSelect>>", self._on_keystroke_select)
        
        editor = ttk.Labelframe(frame, text="Selected Keystroke")
        editor.pack(fill="x", padx=8, pady=(0, 8))


        self.keystroke_fields = {}
        for fname, flabel in [("name", "Name"), ("weight", "Weight"), ("layer", "Layer"), ("keys", "Keys")]:
            f = ttk.Frame(editor)
            f.pack(fill="x", padx=6, pady=2)
            ttk.Label(f, text=flabel + ":", width=14).pack(side="left")
            var = tk.StringVar()
            var.trace_add("write", lambda *a, fn=fname: self._on_keystroke_field_changed(fn))
            self.keystroke_fields[fname] = var
            if fname == "layer":
                combo = ttk.Combobox(f, textvariable=var, values=("any", "both", "base", "shift"), width=37)
                combo.pack(side="left", fill="x", expand=True)
            else:
                ttk.Entry(f, textvariable=var, width=40).pack(side="left", fill="x", expand=True)

        self._refresh_keystrokes()

    def _create_options_tab(self):
        frame=ttk.Frame(self.notebook)
        frame.columnconfigure(0, weight=1, uniform="equal_cols")
        frame.columnconfigure(1, weight=1, uniform="equal_cols")
        frame.rowconfigure(0, weight=0)
        frame.rowconfigure(1, weight=1)

        self.notebook.add(frame, text="Options")
        toolbar = ttk.Frame(frame)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=8)        
        ttk.Button(toolbar, text="Reload", command=self._reload_options).pack(side="left")
        ttk.Button(toolbar, text="Save", command=self._save_options).pack(side="left", padx=(4, 0))
        
        metric_editor = ttk.Labelframe(frame, text="Target Metrics")
        metric_editor.grid(row=1, column=0, columnspan=1, sticky="nsew", padx=8, pady=(0, 8))

        self.metric_option_fields={}
        for fname, flabel in [("finger_strain", "Finger strain"), ("travel_distance", "Travel distance"), ("use_count", "Use count"), ("bad_roll","Bad roll"),("finger_stretch","Finger stretch")]:
            f = ttk.Frame(metric_editor)
            f.pack(fill="x", padx=6, pady=2)
            ttk.Label(f, text=flabel + ":", width=25).pack(side="left")
            var = tk.StringVar()
            var.trace_add("write", lambda *a, fn=fname: self._on_metric_option_field_changed(fn))
            ttk.Entry(f, textvariable=var, width=40).pack(side="left", fill="x", expand=True)
            self.metric_option_fields[fname] = var

        mixed_editor = ttk.Labelframe(frame, text="Mixed")
        mixed_editor.grid(row=1, column=1, columnspan=1, sticky="nsew", padx=8, pady=(0, 8))

        self.mixed_option_fields = {}
        for fname, flabel in [("generation_limit", "Generation limit"), ("auto_generate_shift_home", "Auto generate shift home"), ("dev_mode", "Dev mode")]:
            f = ttk.Frame(mixed_editor)
            f.pack(fill="x", padx=6, pady=2)
            ttk.Label(f, text=flabel + ":", width=25).pack(side="left")
            if fname == "dev_mode":
                var = tk.BooleanVar()
                var.trace_add("write", lambda *a, fn=fname: self._on_mixed_option_field_changed(fn))
                ttk.Checkbutton(f, variable=var).pack(side="left", fill="x", expand=True)
            else:
                var = tk.StringVar()
                var.trace_add("write", lambda *a, fn=fname: self._on_mixed_option_field_changed(fn))
                ttk.Entry(f, textvariable=var, width=40).pack(side="left", fill="x", expand=True)
            self.mixed_option_fields[fname] = var
        self._refresh_options()

    def _create_run_tab(self):
        """Optimization runner tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Run")
        
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill="x", padx=8, pady=8)
        self.start_button = ttk.Button(toolbar, text="Start Optimization", command=self._start_optimization)
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(toolbar, text="Stop", command=self._stop_optimization, state="disabled")
        self.stop_button.pack(side="left", padx=(4, 0))
        ttk.Button(toolbar, text="Open Output Folder", command=self._open_output_folder).pack(side="right")
        
        self.run_output = tk.Text(frame, wrap="none", state="disabled", font=("Courier", 9), 
                                bg="#0f1318", fg="#e6e6e6", relief="flat", highlightthickness=0)
        self.run_output.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    
    def _refresh_layout(self):
        key = self.layout_canvas.get_selected_key()
        if not key:
            self.layout_sel_label.config(text="None")
            for v in self.layout_fields.values():
                v.set("")
            self.layout_active_base.set(False)
            self.layout_active_shift.set(False)
            self.delete_key_button.config(state="disabled")
            return
        self.delete_key_button.config(state="normal")
        
        self.layout_sel_label.config(text=f"Selected: {self.layout_canvas.selected}")
        self.layout_fields["x"].set(str(round(key._pos.x, 2)))
        self.layout_fields["y"].set(str(round(key._pos.y, 2)))
        self.layout_fields["width"].set(str(round(key._width, 2)))
        self.layout_fields["height"].set(str(round(key._height, 2)))
        self.layout_fields["offset"].set(str(round(key._offset, 2)))
        self.layout_active_base.set(self.layout_canvas.selected in self.model.available_keys)
        self.layout_active_shift.set(self.layout_canvas.selected in self.model.available_shift_keys)

    def _on_layout_field_changed(self, fname):
        """Handle layout field edits."""
        key = self.layout_canvas.get_selected_key()
        if not key:
            return
        try:
            val = float(self.layout_fields[fname].get() or 0)
            if fname == "x":
                val=max(self.model.organizer.left_most_x,val)
                if abs(key._pos.x - val) < 0.001:
                    return
                key.set_pos(Point(val,key._pos.y))
                self.layout_fields["x"].set(str(round(val, 3)))
            elif fname == "y":
                val=max(self.model.organizer.left_most_y,val)
                if abs(key._pos.y - val) < 0.001:
                    return
                key.set_pos(Point(key._pos.x,val))
                self.layout_fields["y"].set(str(round(val, 3)))
            elif fname == "width":
                val=max(val,1)
                if abs(key._width - val) < 0.001:
                    return
                key._width = val
                self.layout_fields["width"].set(str(round(val, 3)))
            elif fname == "height":
                val=max(val,1)
                if abs(key._height - val) < 0.001:
                    return
                key._height = val
                self.layout_fields["height"].set(str(round(val, 3)))
            elif fname == "offset":
                val=max(-key._width/2,min(val,key._width/2))
                if abs(key._offset - val) < 0.001:
                    return
                key._offset = val
                self.layout_fields["offset"].set(str(round(val, 3)))
            self.layout_canvas.redraw()
        except ValueError:
            pass

    def _on_layout_active_changed(self):
        """Handle active base/shift checkbox changes."""
        if not self.layout_canvas.selected:
            return
        if self.layout_active_base.get():
            self.model.available_keys.add(self.layout_canvas.selected)
        else:
            self.model.available_keys.discard(self.layout_canvas.selected)
        
        if self.layout_active_shift.get():
            self.model.available_shift_keys.add(self.layout_canvas.selected)
        else:
            self.model.available_shift_keys.discard(self.layout_canvas.selected)
        
        self.layout_canvas.redraw()

    def _on_snap_changed(self):
        """Handle changes to snap step from the UI."""
        try:
            v = float(self.snap_var.get())
            if v <= 0:
                return
            self.layout_canvas.snap_step = v
        except Exception:
            return

    def _add_layout_key(self):
        """Add new key."""
        new_name = self.model.add_key()
        self.layout_canvas.set_selected(new_name)
        self._refresh_layout()
        self.layout_canvas.redraw()

    def _delete_layout_key(self):
        """Delete selected key."""
        if self.layout_canvas.get_selected_key:
            self.model.remove_key(self.layout_canvas.selected)
            self.model.available_keys.discard(self.layout_canvas.selected)
            self.model.available_shift_keys.discard(self.layout_canvas.selected)
            self.layout_canvas.selected = None
            self.layout_canvas.redraw()
            self._refresh_layout()

    def _reload_layout(self):
        """Reload layout from files."""
        try:
            self.model.load_layout()
            self.model.load_available_keys()
            self.layout_canvas.set_selected(None)
            self.layout_canvas.redraw()
            self._refresh_layout()
        except Exception as e:
            messagebox.showerror("Error", "Failed to reload:\n" + traceback.format_exc())

    def _save_layout(self):
        try:
            self.model.save_layout(save_available_keys=True)
            messagebox.showinfo("Success", "Layout saved!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")
    def _refresh_fixed(self):
        """Refresh fixed keys tab."""
        key_name = self.fixed_canvas.selected
        if not key_name:
            self.fixed_sel_label.config(text="None")
            self.fixed_base_var.set("")
            self.fixed_shift_var.set("")
            self.fixed_chat_var.set(False)
            self.remove_fixed_button.config(state="disabled")
            return
        self.remove_fixed_button.config(state="normal")
        
        self.fixed_sel_label.config(text=f"Selected: {key_name}")
        is_chat = self.model.chat == key_name
        fk = self.model.fixed_keys.get(key_name)
        self.fixed_base_var.set(fk if fk else "")
        self.fixed_shift_var.set(self.model.fixed_shift_keys.get(key_name, ""))
        self.fixed_chat_var.set(is_chat)

    def _on_fixed_changed(self, field=None):
        """Handle fixed key remapping changes."""
        if not self.fixed_canvas.selected:
            return
        key = self.fixed_canvas.selected

        if field == "base":
            base = self.fixed_base_var.get()
            if base:
                self.model.fixed_keys[key] = base
            else:
                self.model.fixed_keys.pop(key, None)

        elif field == "shift":
            shift = self.fixed_shift_var.get()
            if shift:
                self.model.fixed_shift_keys[key] = shift
            else:
                self.model.fixed_shift_keys.pop(key, None)

        elif field == "chat":
            chat = self.fixed_chat_var.get()
            if chat:
                self.model.chat = key
            else:
                if self.model.chat == key:
                    self.model.chat = None

        self.fixed_canvas.redraw()

    def _remove_fixed(self):
        """Remove fixed assignment for selected key."""
        if self.fixed_canvas.selected:
            if self.model.chat == self.fixed_canvas.selected:
                self.model.chat = None
            self.model.fixed_keys.pop(self.fixed_canvas.selected, None)
            self.model.fixed_shift_keys.pop(self.fixed_canvas.selected, None)
            self.fixed_base_var.set("")
            self.fixed_shift_var.set("")
            self.fixed_chat_var.set(False)
            self.fixed_canvas.redraw()

    def _reload_fixed(self):
        """Reload fixed keys from files."""
        try:
            self.model.load_fixed_keys()
            self.fixed_canvas.selected = None
            self.fixed_canvas.redraw()
            self._refresh_fixed()
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")
    
    def _save_fixed(self):
        """Save fixed keys to files."""
        try:
            self.model.save_fixed_keys()
            messagebox.showinfo("Success", "Fixed keys saved!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")

    def _refresh_finger(self):
        """Refresh finger assignment tab."""
        key_name = self.finger_canvas.selected
        self.finger_combo['values'] = sorted(self.model.assigned_fingers.keys())
        
        if not key_name:
            self.finger_sel_label.config(text="None")
            self.finger_select_var.set("")
            self.home_key_var.set(False)
            self.remove_from_finger_button.config(state="disabled")
            return
        self.remove_from_finger_button.config(state="normal")
        
        self.finger_sel_label.config(text=f"Selected: {key_name}")
        assigned = [f for f, keys in self.model.assigned_fingers.items() if key_name in keys]
        self.finger_select_var.set(assigned[0] if assigned else "")
        current_finger = self.finger_select_var.get()
        self.home_key_var.set(self.model.home_keys.get(current_finger) == key_name)

    def _on_finger_selected(self):
        """Handle finger combo selection."""
        if not self.finger_canvas.selected:
            return
        finger = self.finger_select_var.get()
        if not finger:
            return
        
        # Already assigned to this finger - just sync home key checkbox
        if self.finger_canvas.selected in self.model.assigned_fingers.get(finger, []):
            is_home = self.model.home_keys.get(finger) == self.finger_canvas.selected
            self.home_key_var.set(is_home)
            return
        
        # Remove from old finger
        for f, keys in self.model.assigned_fingers.items():
            if self.finger_canvas.selected in keys:
                if self.model.home_keys.get(f) == self.finger_canvas.selected:
                    self.model.home_keys.pop(f, None)
                keys.remove(self.finger_canvas.selected)
                break
        
        # Add to new finger
        if finger not in self.model.assigned_fingers:
            self.model.assigned_fingers[finger] = []
        self.model.assigned_fingers[finger].append(self.finger_canvas.selected)
        
        # Sync home key checkbox for new finger
        is_home = self.model.home_keys.get(finger) == self.finger_canvas.selected
        self.home_key_var.set(is_home)
        
        self.finger_canvas.redraw()

    def _on_home_key_changed(self):
        """Handle home key checkbox."""
        if not self.finger_canvas.selected:
            return
        finger = self.finger_select_var.get()
        if not finger:
            return
        
        is_home = self.model.home_keys.get(finger) == self.finger_canvas.selected
        
        if self.home_key_var.get():
            if not is_home:
                self.model.home_keys[finger] = self.finger_canvas.selected
        else:
            if is_home:
                self.model.home_keys.pop(finger, None)
        
        self.finger_canvas.redraw()

    def _remove_key_from_finger(self):
        """Remove selected key from its finger."""
        if self.finger_canvas.selected:
            # Remove from assigned fingers
            for keys in self.model.assigned_fingers.values():
                if self.finger_canvas.selected in keys:
                    keys.remove(self.finger_canvas.selected)
            # Remove any home key references safely
            to_remove = [f for f, k in list(self.model.home_keys.items()) if k == self.finger_canvas.selected]
            for f in to_remove:
                self.model.home_keys.pop(f, None)
            self.finger_select_var.set("")
            self.home_key_var.set(False)
            self.finger_canvas.redraw()

    def _reload_finger(self):
        """Reload finger assignments from files."""
        try:
            self.model.load_assigned_fingers()
            self.finger_canvas.selected = None
            self.finger_canvas.redraw()
            self._refresh_finger()
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")

    
    def _save_finger(self):
        """Save finger assignments to files."""
        try:
            self.model.save_assigned_fingers()
            messagebox.showinfo("Success", "Finger assignments saved!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")

    def _refresh_keystrokes(self, preserve_name=None):
        """Refresh keystrokes treeview."""
        selected_name = preserve_name
        if selected_name is None:
            if self.new_selected_keystroke:
                selected_name=self.new_selected_keystroke
                self.keystroke_tree.selection_set(self.keystroke_tree.get_children()[-1])
                self.new_selected_keystroke=None
            else:
                sel = self.keystroke_tree.selection()
                if sel:
                    selected_name = self.keystroke_tree.item(sel[0], "values")[0]
        
        self.keystroke_tree.unbind("<<TreeviewSelect>>")
        self.keystroke_tree.delete(*self.keystroke_tree.get_children())
        for name, data in self.model.keystrokes.items():
            keys = ", ".join(data.get("keys", []))
            weight = data.get("weight", "")
            layer = data.get("layer", "")
            self.keystroke_tree.insert("", tk.END, values=(name, weight, layer, keys))
        
        if selected_name:
            for item in self.keystroke_tree.get_children():
                vals = self.keystroke_tree.item(item, "values")
                if vals and vals[0] == selected_name:
                    self.keystroke_tree.selection_set(item)
                    break
        
        self.keystroke_tree.bind("<<TreeviewSelect>>", self._on_keystroke_select)
        
    
    def _on_keystroke_select(self, event):
        """Handle keystroke selection."""
        sel = self.keystroke_tree.selection()
        if not sel:
            self.current_keystroke = None
            self.delete_keystroke_button.config(state="disabled")
            for v in self.keystroke_fields.values():
                v.set("")
            return

        self.delete_keystroke_button.config(state="normal")

        item = sel[0]
        values = self.keystroke_tree.item(item, "values")
        name = values[0]
        weight = values[1]
        layer = values[2]
        keys = values[3]

        if name == self.current_keystroke:
            return

        self.current_keystroke = None
        self.keystroke_fields["name"].set(name)
        self.keystroke_fields["weight"].set(str(weight) if weight is not None else "")
        self.keystroke_fields["layer"].set(layer)
        self.keystroke_fields["keys"].set(keys)
        self.current_keystroke = name

    def _on_keystroke_field_changed(self, fname):
        """Handle edits to the keystroke editor fields and update the model."""
        if not self.current_keystroke:
            return

        # Read fields
        name = self.keystroke_fields["name"].get().strip()
        weight_s = self.keystroke_fields["weight"].get().strip()
        layer = self.keystroke_fields["layer"].get().strip() or "any"
        keys_s = self.keystroke_fields["keys"].get().strip()

        if not name:
            return

        # parse keys
        keys_list = [k.strip() for k in keys_s.split(",") if k.strip()]

        # parse weight
        if weight_s == "":
            weight = None
        else:
            try:
                if "." in weight_s:
                    weight = float(weight_s)
                else:
                    weight = int(weight_s)
            except Exception:
                weight = None

        values = {"keys": keys_list, "weight": weight, "layer": layer}

        old_name = self.current_keystroke
        if name != old_name:
            self.model.keystrokes.pop(old_name, None)
            self.model.keystrokes[name] = values
            self.current_keystroke = name
        else:
            old = self.model.keystrokes.get(name, {})
            if (old.get("keys") == keys_list and 
                old.get("weight") == weight and 
                old.get("layer", "any") == layer):
                return
            self.model.keystrokes[name] = values

        self._refresh_keystrokes(preserve_name=name)

    def _reload_keystrokes(self):
        """Reload keystrokes from files."""
        try:
            self.model.load_keystrokes()
            self._refresh_keystrokes()
            self.current_keystroke = None
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")

    def _save_keystrokes(self):
        """Save keystrokes to files."""
        try:
            self.model.save_keystrokes()
            messagebox.showinfo("Success", "Keystrokes saved!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")

    def _add_keystroke(self):
        n=len(self.model.keystrokes)
        name=f"keystroke_{n}"
        while name in self.model.keystrokes:
            n+=1
            name=f"keystroke_{n}"

        self.model.keystrokes[name]={"keys":[],"weight": None,"layer": "any"}
        self.new_selected_keystroke=name
        self._refresh_keystrokes()

    def _delete_keystroke(self):
        if not self.current_keystroke:
            return
        self.model.keystrokes.pop(self.current_keystroke)
        self._refresh_keystrokes()

    def _refresh_options(self):
        for fname in ["finger_strain", "travel_distance", "use_count", "bad_roll","finger_stretch"]:
            self.metric_option_fields[fname].set(str(self.model.target_metrics[fname]))
        for fname in ["generation_limit", "auto_generate_shift_home", "dev_mode"]:
            self.mixed_option_fields[fname].set(str(self.model.settings[fname]))
        
    def _reload_options(self):
        try:
            self.model.load_options()
            self._refresh_options()
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")

    def _save_options(self):
        try:
            self.model.save_options()
            messagebox.showinfo("Success", "Options saved!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")

    def _on_metric_option_field_changed(self, field=None):
        
        if not field:
            return

        val=float(self.metric_option_fields[field].get().strip())
        if val<0:
            val=0
            self.metric_option_fields[field].set(str(val))
        self.model.target_metrics[field]=val

    def _on_mixed_option_field_changed(self, field=None):
        
        val=self.mixed_option_fields[field].get()
        match field:
            case "generation_limit":
                val=int(val)
                if val<0:
                    val=0
                    self.mixed_option_fields[field].set(str(val))
            case "auto_generate_shift_home":
                val=float(val)
                if val<0 or val>1:
                    val=min(max(0,val),1)
                    self.mixed_option_fields[field].set(str(val))
            case "dev_mode":
                val=bool(val) 
            case _:
                return            
        self.model.settings[field]=val

    def _start_optimization(self):
        """Start optimization subprocess."""
        try:
            cmd = [sys.executable, "-u", str(ROOT_DIR / "run.py")]
            self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                text=True, bufsize=1, universal_newlines=True)
            self.start_button.config(state="disabled")
            self.stop_button.config(state="normal")
            self.run_output.config(state="normal")
            self.run_output.delete("1.0", tk.END)
            self.run_output.config(state="disabled")
            t = threading.Thread(target=self._read_process_output, daemon=True)
            t.start()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start: {e}")
    
    def _stop_optimization(self):
        """Stop optimization subprocess."""
        if self.process:
            self.process.terminate()
            self.process = None
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")

    def _open_output_folder(self):
        system_name = platform.system()
    
        if system_name == "Windows":
            os.startfile(OUTPUT_DIR)
        elif system_name == "Darwin":  # macOS
            subprocess.Popen(["open", OUTPUT_DIR])
        else:  # Linux / Unix
            subprocess.Popen(["xdg-open", OUTPUT_DIR])
    
    def _read_process_output(self):
        """Read and display subprocess output."""
        if not self.process:
            return

        try:
            for line in iter(self.process.stdout.readline, ''):
                if not line:
                    break
                try:
                    self.output_queue.put(line.rstrip('\n'))
                except Exception:
                    pass
            try:
                self.process.wait()
            except Exception:
                pass
        finally:
            self.process = None
            try:
                self.output_queue.put(None)
            except Exception:
                pass

    def _poll_queue(self):
        """Poll output queue for subprocess messages."""
        while not self.output_queue.empty():
            try:
                msg = self.output_queue.get_nowait()
                if msg is None:
                    self.start_button.config(state="normal")
                    self.stop_button.config(state="disabled")
                    continue

                self.run_output.config(state="normal")
                self.run_output.insert(tk.END, msg + "\n")
                self.run_output.see(tk.END)
                self.run_output.config(state="disabled")
            except queue.Empty:
                break
        
        self._poll_id = self.after(100, self._poll_queue)


    def _on_shift_press(self, event):
        """Handle shift key press."""
        self.shift_pressed = True
        if self.notebook.index(self.notebook.select()) == 1:
            self.fixed_canvas.set_view_options(show_labels=True)
    
    def _on_shift_release(self, event):
        """Handle shift key release."""
        self.shift_pressed = False
        if self.notebook.index(self.notebook.select()) == 1:
            self.fixed_canvas.set_view_options(show_labels=False)
    
    def _on_tab_changed(self, event):
        """Handle tab change."""
        idx = self.notebook.index(self.notebook.select())
        if idx == 0:
            self.layout_canvas.redraw()
        elif idx == 1:
            self.fixed_canvas.set_view_options(show_labels=self.shift_pressed)
            self.fixed_canvas.redraw()
        elif idx == 2:
            self.finger_canvas.redraw()
    
    def _on_close(self):
        """Handle window close."""
        if self._poll_id:
            self.after_cancel(self._poll_id)
        if self.process:
            self.process.terminate()
        self.destroy()

if __name__ == "__main__":
    # Tell Windows not to bitmap-stretch this app
    if platform.system() == "Windows":
        try:
            # Per-Monitor DPI awareness (Windows 8.1 / 10 / 11)
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                # Fallback for older Windows versions
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass
    app = GUI()
    app.mainloop()