# CrazyflieSwarm Class Documentation

## Overview
The `CrazyflieSwarm` class is the central hub for managing a swarm of Crazyflie drones. It handles connections, telemetry, state tracking, flight commands, formation control, and safe shutdown. It acts as a bridge between the GUI and the drones, coordinating all hardware interactions through the FormationManager.

## Stored Values (State & Cache)

### Connection Management
- **`uris`** (list): List of drone radio URIs to connect to, passed when creating the object
- **`scfs`** (dict): Map of {uri → SyncCrazyflie} for active drone connections
- **`link_threads`** (dict): Map of {uri → Thread} tracking connection threads

### Thread Safety
- **`lock`** (threading.Lock): Mutex for synchronized access to shared caches
- **`running`** (bool): Flag indicating if the update loop is active

### Drone Telemetry & State
Drones regularly transmit infomration to the computer, this infomration is stored.
- **`battery_cache`** (dict): Map of {uri → voltage} for each drone's battery. Only the last voltage is stored
- **`state_cache`** (dict): Map of {uri → state} for each drone's current state
  - Possible states: idle, connecting, connected, disconnected, flying, hovering, landing, crashed, charging, error. This states come from the supervisor.info variable
- **`_last_state_update_time`** (dict): Map of {uri → timestamp}. It updates every time a state update is recieved. It is udes to decect connection loss
- **`current_positions`** (dict): Map of {uri → (x, y, z)} for real-time drone positions. They are the positions estimated by the drones onboard, communicated to the computer. They are not where they are supposed to be, but where they estimimate they are.
- **`position_cache`** (dict): Map of {uri → [(x,y,z), ...]} storing position history (used for convergence detection)

Battery and state are polled with "low frequency" and posistion is polled with "high frequency". This can be adjusted in config.py
- **`_log_configs`** (dict): Map of {uri → (LogConfig_low, LogConfig_high)} for telemetry subscriptions

### Formation Control
- **`formations`** (FormationManager): Reference to the formation manager for calculating formations
- **`current_formation`** (str): Name of the currently active formation (e.g., "flat_square", "moving_circle")

### Dynamic Formation State
- **`_dynamic_formation_running`** (dict): Map of {uri → bool} tracking which drones are in dynamic formation. This is needed because the dynamic formations use the commander. The commander has higher priority when sending setpoints than the high level commander, so the value in this variable needs to be set to False if the hlc wants to be used, for landing for example.
- **`_dynamic_formation_thread`** (Thread): Reference to the dynamic formation execution thread

## Functions by Category

### Connection Management
These functions are used to establish connection with the drone, then the created objects in scfs are used to perform all other actions (since they have now an open link)
#### `connect_one(uri)`
Connects to a single drone and starts telemetry logging.
- **Parameters**: uri (str) - drone radio URI
- **Interactions**: 
  - Creates a `SyncCrazyflie` object
  - Calls `_setup_logging()` to initialize telemetry
  - Stores in `scfs` dict

#### `connect_all()`
Connects to all drones in parallel using threads.
- **Interactions**:
  - Launches `connect_one()` in separate thread for each URI
  - Waits for all threads to complete

#### `_setup_logging(uri, scf)`
Configures telemetry callbacks for battery, state, and position tracking.
- **Parameters**: 
  - uri (str) - drone identifier
  - scf (SyncCrazyflie) - connection object
- **Creates Callbacks**:
  - `_supervisor_cb()`: Decodes supervisor bits to determine state
  - `_battery_cb()`: Updates battery voltage cache
  - `_position_cb()`: Updates position and position history cache
- **Interactions**: Updates `state_cache`, `battery_cache`, `position_cache`

#### `close_links()`
Safely closes all drone connections.
- **Interactions**: Iterates through `scfs` and closes each link

---

### Drone State Queries
Uses the information stored in the caches to reply to information requests.
#### `get_drone_state(uri)`
Returns the current state of a drone from cache.
- **Returns**: str (state name)
- **Interactions**: Reads from `state_cache`

#### `get_drone_battery(uri)`
Returns the current battery voltage of a drone from cache.
- **Returns**: float (voltage)
- **Interactions**: Reads from `battery_cache`

#### `position_has_converged(uri)`
Checks if a drone's position has stabilized within the last N measurements. This avoid chashes because a faulty drone
- **Returns**: bool
- **Logic**: Compares max distance between all recorded positions against threshold
- **Interactions**: Reads from `position_cache`; uses `position_convergence_distance` config

---

### Flight Control

#### `takeoff_one(uri, scf, height, duration)`
Commands a single drone to takeoff.
- **Parameters**:
  - uri, scf: drone identifiers
  - height (float): takeoff altitude (meters)
  - duration (float): time to reach altitude (seconds)
- **Safety Checks**:
  - Verifies battery level ≥ `low_battery_on_ground`
  - Ensures drone is not already flying
  - Confirms position has converged
- **Interactions**:
  - Calls `scf.cf.high_level_commander.takeoff()`
  - Calls `connect_to_formation()` to add drone to formation tracking

#### `takeoff(height=default, duration=default)`
Commands all connected drones to takeoff in parallel.
- **Interactions**:
  - Calls `_stop_dynamic_formation()` to cancel any running dynamic formations
  - Launches `takeoff_one()` in threads for each drone

#### `land_one(uri, scf, duration)`
Commands a single drone to land.
- **Parameters**:
  - uri, scf: drone identifiers
  - duration (float): time to land (seconds)
- **Interactions**:
  - Sets `_dynamic_formation_running[uri] = False`
  - Calls `scf.cf.high_level_commander.land()`
  - Calls `disconnect_from_formation()` to remove from formation

#### `land(duration=default)`
Commands all connected drones to land in parallel.
- **Interactions**:
  - Calls `_stop_dynamic_formation()`
  - Launches `land_one()` in threads for each drone

#### `emergency_one(uri, scf)`
Immediately kills motors on a single drone (hard stop).
- **Interactions**:
  - Calls `scf.cf.commander.send_stop_setpoint()`

#### `emergency_land()`
Emergency stops all drones immediately.
- **Interactions**:
  - Calls `_stop_dynamic_formation()`
  - Launches `emergency_one()` in threads for each drone

---

### Safe Shutdown

#### `stop_background(timeout=default)`
Stops the main update loop and cleans up all background threads and logging.
- **Actions**:
  - Sets `running = False` to stop `_update_loop()`
  - Joins update thread with timeout
  - Stops all LogConfig callbacks
  - Joins connection threads
- **Purpose**: Graceful shutdown before closing links

#### `forced_stop_flying()`
Ensures all drones land, then emergency stops any that didn't land in time.
- **Interactions**:
  - Calls `land()` with normal duration
  - Waits 3 seconds
  - Calls `emergency_land()` if drones still flying

---

### Formation Control

#### `send_formation(target_formation, duration=default)`
Moves all drones to specified positions over a given duration.
- **Parameters**:
  - target_formation (dict): {uri → (x, y, z)} target positions
  - duration (float): time to reach positions (seconds)
- **Logic**:
  - Calls `_stop_dynamic_formation()` first
  - Checks for collisions with `formations.positions_intersect()`
  - If collision risk, uses `formations.get_transition_positions()` for multi-step movement
  - Sends commands via `high_level_commander.go_to()`
- **Interactions**:
  - Reads from `current_positions` and `state_cache`
  - Calls FormationManager to check intersections and calculate transitions

#### `send_dynamic_formation(trajectories, waypoint_dt)`
Continuously sends position commands along trajectories with **shared clock synchronization**.
- **Parameters**:
  - trajectories (dict): {uri → [waypoints]} where waypoint = (x, y, z, yaw)
  - waypoint_dt (float): time between waypoints (seconds)
- **Key Feature**: All drones synchronized to shared start time
  - Uses `start_time = time.time()` as reference
  - Each drone computes `target_time = start_time + (i + 1) * waypoint_dt`
  - Sleeps only until target time (compensates for jitter)
- **Interactions**:
  - Sets `_dynamic_formation_running[uri] = True` for each drone
  - Launches threads running `run_sequence()` for each drone
  - Uses `cf.commander.send_position_setpoint()` to send waypoints

#### `_stop_dynamic_formation()`
Stops all running dynamic formation threads and sends stop commands.
- **Interactions**:
  - Sets all `_dynamic_formation_running[uri] = False`
  - Joins thread with timeout
  - Each thread sends `send_stop_setpoint()` and `send_notify_setpoint_stop()`

---

### Formation Types (High-Level Commands)

These methods request formations from the FormationManager and execute them.

#### `flat_square()`
Arranges drones in a 2D grid pattern.
- **Interactions**:
  - Sets `current_formation = "flat_square"`
  - Calls `formations.get_formation_positions("flat_square")`
  - Calls `send_formation()`

#### `circle()`
Arranges drones in a circular pattern.
- **Interactions**:
  - Sets `current_formation = "circle"`
  - Calls `formations.get_formation_positions("circle")`
  - Calls `send_formation()`

#### `tilted_plane()`
Arranges drones in a tilted plane pattern.
- **Interactions**:
  - Sets `current_formation = "tilted_plane"`
  - Calls `formations.get_formation_positions("tilted_plane")`
  - Calls `send_formation()`

#### `moving_circle()`
Drones rotate continuously in a circle.
- **Interactions**:
  - Sets `current_formation = "moving_circle"`
  - Calls `formations.get_dynamic_formation_positions("moving_circle", circle_rotation_period)`
  - Calls `send_formation()` for initial positions
  - Calls `send_dynamic_formation()` for trajectory execution

#### `sin_wave()`
Drones oscillate vertically in a sine wave pattern.
- **Interactions**:
  - Sets `current_formation = "sin_wave"`
  - Calls `formations.get_dynamic_formation_positions("sin_wave", sin_wave_period)`
  - Calls `send_formation()` for initial positions
  - Calls `send_dynamic_formation()` for trajectory execution

---

### Formation Management

#### `connect_to_formation(uri)`
Adds a drone to active formation tracking and recalculates formation for current drones.
- **Interactions**:
  - Calls `formations.connect_to_formation(uri)`
  - Calls `recalculate_current_formation()` to update positions

#### `disconnect_from_formation(uri)`
Removes a drone from formation tracking and recalculates if drones remain.
- **Interactions**:
  - Calls `formations.disconnect_from_formation(uri)`
  - Calls `recalculate_current_formation()` if any drones remain

#### `recalculate_current_formation()`
Re-executes the current formation based on which drones are now active.
- **Purpose**: When drones join/leave mid-formation, automatically recalculate positions for remaining drones
- **Interactions**:
  - Looks up current formation name in `current_formation`
  - Calls corresponding formation method (flat_square, circle, etc.)

---

### Main Update Loop

#### `run()`
Starts the background update loop in a daemon thread.
- **Interactions**:
  - Sets `running = True`
  - Creates and starts `_update_loop()` thread

#### `_update_loop()`
Continuous background loop monitoring drone connectivity, battery, and reconnection.
- **Loop Interval**: `swarm_loop_interval` seconds
- **For Each Drone**:
  - If **connected**: 
    - Checks if connection lost (no state update for too long)
    - Monitors low battery during flight → initiates landing
  - If **disconnected**:
    - Attempts reconnection periodically every `reconnect_attempt_interval` seconds
- **Interactions**:
  - Monitors `state_cache` and `_last_state_update_time`
  - Reads `battery_cache`
  - Calls `land_one()` if battery low during flight
  - Calls `connect_one()` to attempt reconnection
  - Calls `formations.disconnect_from_formation()` on connection loss

---
