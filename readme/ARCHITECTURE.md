# Architecture Schema

## Component Interaction Flow

```
┌─────────────┐
│     GUI     │
│  (gui.py)   │
└──────┬──────┘
       │ orders/commands (button clicks)
       │
       ▼
┌─────────────────────────┐
│  Swarm                  │
│  (drone_commands.py)    │
│                         │
│  - Manages drones       │
│  - Sends commands       │
│  - Tracks states        │
└──────┬──────────────────┘
       │ polls for formations
       │ updates connected drones
       │
       ▼
┌─────────────────────────┐
│  FormationManager       │
│  (formations.py)        │
│                         │
│  - Tracks active drones │
│  - Stores formation     │
│    state                │
└──────┬──────────────────┘
       │ requests specific formations
       │ passes drone availability
       │
       ▼
┌─────────────────────────┐
│  FormationCalculator    │
│  (formations.py)        │
│                         │
│  - Generates           │
│    formations           │
│  - Calculates          │
│    trajectories         │
│  - No state tracking   │
└─────────────────────────┘
```

## Data Flow

1. **GUI → Swarm**: User clicks buttons to command swarm
   - Examples: `flat_square()`, `moving_circle()`, `sin_wave()`
   
2. **Swarm → FormationManager**: Swarm polls and updates formations
   - Updates which drones are connected: `connect_to_formation(uri)`
   - Requests specific formations: `get_formation_positions(type)` or `get_dynamic_formation_positions(type, period)`
   
3. **FormationManager → FormationCalculator**: Manager requests calculations
   - Calls calculator methods with current connected drones
   - Calculator generates positions/trajectories based on available drones
   
4. **Result → Swarm → Drones**: Swarm sends formation data to drones
   - Sends static formations via `send_formation(positions)`
   - Sends dynamic formations via `send_dynamic_formation(trajectories, waypoint_dt)`

## Key Design Principles

- **Separation of Concerns**: Calculator is stateless, Manager tracks state, Swarm manages hardware
- **One-way Dependency**: GUI → Swarm → Manager → Calculator (no backwards calls)
- **FormationManager as Intermediary**: Acts as "formation storage" keeping track of which drones are active
- **Scalability**: Easy to add new formation types; just add methods to FormationCalculator
