This file is intended to explain the structure and functions in the code

This project consists of 3 main files,
- The GUI (gui.py)
- The swarm (drone_commands)
- The formations (formations.py)

The GUI uses Tkinter, it is a recycled GUI from a Crazyflie project. It has the swarm object, with it, it can retrieve information about the states of the drones, and call functions on it when buttons are pushed.

The swarm is a complex class, it keeps all the information about the drones and communicates with them, however this two task require a lot of coordination and functions

Finally the formations consist of 2 classes, the FormationCalculator and the FormationManager. The Formation calculator stores no infomration about the current states of the drones, but it contains the methods that are able to generate formations or dynamic trajectories. This is used by the swarm to then send that information to the drones. However, the swarm itself does not interact with the FormationCalculator, instead, it interacts with the FormationManager, and is this one that interacts with the calculator. The FormationManager task is to keep track of which drones are actively in a formation. It does not have access to the swarm, instead, the swarm manipulates it's values through the given methods. It serves as a kind of "foramtion storage", where the swarm keeps swarming state information, and when requested can get new formations.

The general schema of the funcitoning is can be seen in [ARCHITECTURE.md](readme/ARCHITECTURE.md)

Now we will go into detail in each of the classes

## GUI
Inside the GUI file there are 2 classes. The `Crazyflie_report` is the basic building block for giving information about one drone. This class is then used by `ControlTowerGUI` to generate the GUI.

This GUI is done with Tkinter, a Python GUI library that comes built-in with Python.
Read more about the GUI in [GUI.md](readme/GUI.md)

## CrazyflieSwarm
The `CrazyflieSwarm` class is the central hub for drone management and coordination. It maintains the current state of all drones in the swarm, handles communication with each drone, and orchestrates their movements. The swarm class processes commands from the GUI and translates them into actions by interfacing with the `FormationManager` to generate and execute formations. It also continuously monitors drone states and stores them in so they can be polled by the GUI later.

More information about the CrazyflieSwarm can be found here [CrazyflieSwarm.md](readme/CrazyflieSwarm.md)

## Interaction Diagram with Other Objects

```
GUI (gui.py)
  ↓ (calls methods)
  ├→ takeoff(), land(), emergency_land()
  ├→ flat_square(), circle(), tilted_plane()
  └→ moving_circle(), sin_wave()
  
CrazyflieSwarm (drone_commands.py)
  ├→ manages connections via SyncCrazyflie
  ├→ queries state via get_drone_state(), get_drone_battery()
  └→ delegates formation calculations to FormationManager
  
FormationManager (formations.py)
  ├→ provides get_formation_positions()
  ├→ provides get_dynamic_formation_positions()
  └→ checks collisions via positions_intersect()
  
FormationCalculator (formations.py)
  └→ stateless calculator for positions/trajectories
  
Drones (Crazyflie Hardware)
  ↓ (telemetry logs)
  ├→ battery voltage
  ├→ supervisor state bits
  └→ position (x, y, z)
```

## Key Design Patterns

1. **Thread-Safe Caching**: All drone state is cached with locks to prevent race conditions
2. **Shared Clock Synchronization**: Dynamic formations use a shared start time so all drones move in lockstep
3. **Graceful Degradation**: When a drone disconnects mid-formation, the formation recalculates for remaining drones
4. **Connection Monitoring**: Background loop detects stale connections and attempts reconnection
5. **Multi-Step Transitions**: Collision detection enables safe multi-step formation transitions

## Developing new formations
To add a new formation, implement the following in order:

### 1. FormationCalculator (formations.py)
Add a new static method that calculates drone positions for your formation. It should take parameters like `num_drones`, `center`, `scale`, and return a list of `(x, y, z)` tuples.

```python
@staticmethod
def your_formation_name(drones: {str: bool}): #uri : available
    # Calculate and return positions
    positions = {}
    # ... your logic
    return positions #{uri: [positions]}
```

### 2. FormationManager (formations.py)
Add a your function in the existing 'get_formation_positions' or 'get_dynamic_formation_positions" by adding a new option of a formation:

```python
    def get_formation_positions(self, formation_type):
        if formation_type == "flat_square":
            positions = FormationCalculator().flat_square(self.connected_to_formation)
        ...
        elif formation_type == "new_formation"
            postions = FormationCalculator().your_new_method(self.connected_to_foramtion)
        ...
        else:
            raise ValueError("Unknown formation type.")
        return positions
```

### 3. CrazyflieSwarm (drone_commands.py)
Add a command method that calls the FormationManager and sends positions to drones. Follow the same format as existning methods:
Static:
```python
def new_formation(self):
    print("[FORMATION] New Formation command issued")
    self.current_formation = "new_formation"
    new_formation = self.formations.get_formation_positions("new_formation")
    self.send_formation(new_formation)
```
Dynamic
```python
def new_formation(self):
    print("[FORMATION] new_formation command issued")
    self.current_formation = "new_formation"
    initial_positions, trajectories = self.formations.get_dynamic_formation_positions("new_foramtion", duration)
    self.send_formation(initial_positions)
    self.send_dynamic_formation(trajectories, dynamic_waypoint_dt)
```

### 4. GUI (gui.py)
Add a button in the `ControlTowerGUI` class that calls the swarm method when clicked.
```python
        btn_moving_circle = tkinter.Button(self.content, text="new method", bg="purple", fg="white",
                           command=self.swarm.new_formation, width=btn_width)
        btn_moving_circle.grid(column=0, row=rows_used+2, sticky="ew", padx=padx, pady=pady)
```