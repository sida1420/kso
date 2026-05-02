

# KSO

A multi-objective optimizer for keyboard keybind layouts using MOEA/D. Optimizes keybind placements.

## Installation

Requires **Python 3.7+**.
After download Python, run this in terminal:
```bash
pip install matplotlib numpy
```

## Project Structure

```
.
├── config/                 # Configuration files (JSON + TXT)
│   ├── assigned_fingers.json
│   ├── available_keys.txt
│   ├── finger_distances.json
│   ├── finger_natural_positions.json
│   ├── fixed_keys.json
│   ├── home_keys.json
│   ├── key_widths.json
│   ├── keystrokes.json     # Your key combinations here
│   ├── layout.txt
│   ├── parameters.json
│   └── target_metrics.json
├── output/                 # Generated layout SVGs
├── run.py                  # Run the code here
└── ...
```

## Usage
After edit your desire keystrokes in `config/keystrokes.json`, run this in terminal

```bash
python run.py
```

The algorithm runs for 500 generations by default. Results are saved as SVG images in the `output/` directory:
- `layout.svg` — initial layout
- `top 1.svg` ... `top 5.svg` — best optimized layouts


## Customization

- **Keystrokes:** Edit `config/keystrokes.json` to define your own key sequences and weights.
- **Which key to optimize**: Edit `config/available_keys.txt` to define what key slot is needed for optimize, and edit `config/fixed_keys.json` to define what key slot can't be used.
- **Target priorities:** Edit `config/target_metrics.json` to change which metrics matter most to you.
- **Which finger to press a key**: Edit `config/assigned_fingers.json`
- **Natural finger positions**: Edit `home_keys.json` to change your start finger positions for each keystroke (Ideally your movement keys).
- **Layout:** Edit `config/layout.txt` and `config/key_widths.json` to change the physical keyboard shape.

## Metrics

The optimizer minimizes five objectives (weights set in `target_metrics.json`):

| Metric | Description |
|--------|-------------|
| **finger_cost** | Penalty for placing frequent keys far from the finger's home position, weighted by finger strength (e.g., pinky = expensive). |
| **movement_cost** | Cost of moving fingers between keys during a keystroke sequence. |
| **use_count_cost** | Penalty for overusing individual fingers|
| **roll_cost** | Rewards smooth inward/outward finger rolls; penalizes redirects and same-finger repetition. |
| **distance_cost** | Penalty for fingers deviating from their natural relative spacing (e.g., stretch too wide or close). |

Lower scores are better.


---
