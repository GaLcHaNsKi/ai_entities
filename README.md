# AI Entities - Ecosystem Simulation

A sophisticated ecosystem simulation with configurable creatures, energy systems, and reinforcement learning-based AI brains.

## Features

- **Dynamic Ecosystem**: Herbivores and predators with realistic energy/metabolism systems
- **Reinforcement Learning**: PPO-trained agents via Stable-Baselines3 + PyTorch
- **Pluggable Brain System**: Switch between heuristic and RL brains per creature type
- **Configurable Parameters**: Full control over creature counts, energy levels, vision ranges, and more
- **Dual Interface**: 
  - Full Tkinter UI with parameter sliders, preset configurations, and brain type selector
  - Real-time Pygame visualization with statistics overlay
  - Headless mode for batch simulations and server deployments
- **AI Brains**: Heuristic rule-based and neural network PPO decision making
- **Physics Engine**: Vector-based movement, energy costs, speed limiting
- **Resource System**: Multi-consumer plant distribution with energy management

## Installation

### Requirements
- Python 3.8+
- pygame
- numpy
- torch >= 2.0
- stable-baselines3 >= 2.1
- gymnasium >= 0.29
- tensorboard, tqdm, rich
- tkinter (usually included with Python)

### Setup

```bash
cd ai_entities
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running the Simulation

### Mode 1: Full UI (Tkinter + Pygame)

```bash
python3 app.py
```

This launches:
1. Tkinter Settings Window - Configure all parameters with sliders
2. Pygame Visualization - Real-time ecosystem display

**Controls:**
- SPACE: Pause/Resume
- Q: Quit
- +/-: Speed up/down
- R: Reset
- C: Auto-center camera on largest cluster
- M: Toggle edge panning
- Mouse wheel: Zoom in/out

**Brain selector:** In the settings window, choose `heuristic` or `rl` for each creature type to compare AI vs rule-based behavior.

### Mode 2: Headless (Fast, No UI)

```bash
python3 app.py --headless <preset> <duration>

# Examples
python3 app.py --headless balanced 10
python3 app.py --headless predator_dominant 20
python3 app.py --help
```

**Presets:** balanced, herbivore_dominated, predator_dominant, scarce_resources

### Mode 3: RL Training (Headless)

```bash
# Train a herbivore agent (PPO, 200k steps)
python3 train.py --agent herbivore --steps 200000

# Train a predator agent
python3 train.py --agent predator --steps 500000

# Resume from a checkpoint
python3 train.py --agent herbivore --resume models/herbivore_ppo.zip --steps 100000

# Custom hyperparameters
python3 train.py --agent herbivore --steps 300000 --lr 0.0001 --batch-size 128 --n-steps 4096

# Force CPU (default: auto-detect GPU)
python3 train.py --agent herbivore --steps 200000 --device cpu
```

**Training arguments:**

| Argument | Default | Description |
|---|---|---|
| `--agent` | herbivore | Creature type to train (`herbivore` / `predator`) |
| `--steps` | 200000 | Total training timesteps |
| `--lr` | 3e-4 | Learning rate |
| `--batch-size` | 64 | Minibatch size |
| `--n-steps` | 2048 | Steps per rollout |
| `--max-episode-steps` | 4000 | Max steps before episode truncation |
| `--save-dir` | models/ | Directory for saved models |
| `--log-dir` | logs/ | Tensorboard log directory |
| `--resume` | — | Path to `.zip` model to continue training |
| `--device` | auto | PyTorch device (`auto` / `cpu` / `cuda`) |

**Monitor training:**

```bash
tensorboard --logdir logs
```

Trained models are saved to `models/` and can be used in the simulation by selecting `rl` brain type in the settings UI.

## Project Structure

```
ai_entities/
├── core/
│   ├── physics.py          # Vector2, energy system
│   ├── entity.py           # Base Entity class with sensors
│   ├── world.py            # World simulation loop
│   ├── config.py           # Configuration, presets & brain_type
│   └── resource.py         # Plant resource system
├── creatures/
│   ├── base.py             # Animal base class
│   ├── herbivore.py        # Herbivore (pluggable brain)
│   └── predator.py         # Predator (pluggable brain)
├── ai/
│   ├── brain.py            # Brain ABC, heuristic brains, factory
│   ├── rl_brain.py         # RLBrain — PPO model wrapper
│   ├── reward.py           # RewardCalculator for RL training
│   └── gym_env.py          # Gymnasium environment wrapper
├── ui/
│   ├── pygame_renderer.py  # Pygame visualization & camera
│   ├── settings.py         # Tkinter settings (brain selector)
│   ├── ui_components.py    # UI panels & buttons
│   └── application.py      # Main app coordinator
├── models/                 # Trained RL models (.zip)
├── logs/                   # Tensorboard training logs
├── train.py                # Headless RL training script
├── app.py                  # Entry point
└── headless.py             # Headless mode
```

## Ecosystem Mechanics

### Energy System
- Movement cost: speed^2 × 0.02 × dt
- Metabolic cost: 0.001 × dt
- Max speed = 100 × sqrt(energy_ratio)

### Behaviors

**Herbivores:**
- Flee from predators
- Search for plants
- Wander if idle
- Reproduce at 70% energy

**Predators:**
- Hunt herbivores
- Attack with energy-dependent damage
- Gain 85% of damage as energy
- Reproduce when well-fed
- Die from starvation

### Population Balance

When herbivores abundant → predators reproduce
When herbivores scarce → predators starve
When predators rare → herbivores multiply
Plants respawn → natural resource limitation

## Testing

```bash
python3 tests.py
```

Tests cover physics, entities, world updates, and neural networks.

## Performance

- UI Mode: 30 FPS rendering, ~1000 updates/second
- Headless Mode: ~5000 updates/second
- Max creatures: 50-100 (depending on config)

## Troubleshooting

### UI doesn't work
Use headless mode: `python3 app.py --headless balanced 10`

### Creatures dying too fast
- Increase initial energy
- Increase plant count
- Use herbivore_dominated preset

## Reinforcement Learning Architecture

### Brain System

All creatures use a **pluggable brain** — the `Brain` abstract class defines `decide_action(sensor_data, entity)` returning an action dict. Two implementations ship out of the box:

- **HeuristicHerbivoreBrain / HeuristicPredatorBrain** — hand-crafted rules (flee, hunt, eat, wander)
- **RLHerbivoreBrain / RLPredatorBrain** — wraps a trained PPO model from Stable-Baselines3

The `create_brain(brain_type, creature_type)` factory selects the right class based on config.

### Observation Space (49-dim)

| Slice | Dim | Content |
|---|---|---|
| Self state | 5 | energy ratio, velocity x/y, position x/y (normalized) |
| Nearest plants | 20 | 5 slots × (distance, dir_x, dir_y, energy) |
| Nearest herbivores | 12 | 3 slots × (distance, dir_x, dir_y, energy) |
| Nearest predators | 12 | 3 slots × (distance, dir_x, dir_y, energy) |

### Action Space (3-dim, continuous)

`[move_x, move_y, speed_factor]` — all in `[-1, 1]`

### Reward Shaping

**Herbivore rewards:**
- Eating energy: +1.0 × (energy gained / max_energy)
- Survival per step: +0.01
- Reproduction: +5.0
- Death: −10.0
- Taking damage: −2.0
- Low energy warning: −0.05
- Wall proximity: −0.1

**Predator rewards:**
- Kill prey: +5.0
- Deal damage: +2.0 × (damage / max_energy)
- Survival per step: +0.01
- Reproduction: +5.0
- Death: −10.0
- Hunger (below 30%): −0.05
- Wall proximity: −0.1

### Training Environment

`SingleAgentEnv` wraps the full `World` simulation as a Gymnasium env. One creature is the RL agent; all others run on heuristic brains, creating a realistic multi-agent environment for training.

## Future Enhancements

- Multi-agent PPO (train multiple RL agents simultaneously)
- Curriculum learning (gradually increase difficulty)
- Genome persistence & evolution tracking
- Multi-species support
- Advanced behaviors (pack hunting, territories)
- Statistical analysis & comparison tools
- Save/load simulation state

## License

MIT License
