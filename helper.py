import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
CONFIG_DIR = ROOT_DIR / "config"
OUTPUT_DIR = ROOT_DIR / "output"

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