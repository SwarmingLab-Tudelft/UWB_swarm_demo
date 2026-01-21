# Formations Module Documentation

## Overview

The formations module contains two classes that work together to generate and manage drone formations:

1. **FormationCalculator** - Stateless calculator that generates formation positions and dynamic trajectories
2. **FormationManager** - Maintains formation state and tracks which drones are active in formations

The separation allows for flexible formation calculations independent of drone state, while the manager tracks which drones should participate in formations.

---

## FormationManager Class

### Overview
The FormationManager acts as an intermediary between the Swarm and FormationCalculator. It tracks which drones are actively participating in formations and provides methods to request specific formation types.

### Stored Values

#### Drone Participation Tracking
- **`uris`** (list): List of all drone identifiers in the system
- **`connected_to_formation`** (dict): Map of {uri → bool} indicating which drones are active in formations
- **`n_connected_drones`** (int): Count of drones currently active in formations

### Functions

#### `__init__(uris)`
Initializes the manager with a list of drone URIs.
- **Parameters**: uris (list) - list of drone identifiers
- **Initialization**: Creates empty `connected_to_formation` dict with all URIs set to False

#### `connect_to_formation(uri)`
Marks a drone as active in formations.
- **Parameters**: uri (str) - drone identifier
- **Actions**:
  - Sets `connected_to_formation[uri] = True`
  - Increments `n_connected_drones`
  - Prints confirmation message
- **Called By**: Swarm when drone takes off

#### `disconnect_from_formation(uri)`
Marks a drone as no longer participating in formations.
- **Parameters**: uri (str) - drone identifier
- **Actions**:
  - Sets `connected_to_formation[uri] = False`
  - Decrements `n_connected_drones`
  - Prints status message
- **Called By**: Swarm when drone lands or connection is lost

#### `get_formation_positions(formation_type)`
Requests static formation positions for all active drones.
- **Parameters**: formation_type (str) - one of: "flat_square", "circle", "tilted_plane"
- **Returns**: dict of {uri → (x, y, z)} target positions
- **Logic**:
  - Creates FormationCalculator instance
  - Calls appropriate method with `connected_to_formation` dict
  - Returns position dict
- **Interactions**: Calls FormationCalculator methods

#### `get_dynamic_formation_positions(formation_type, period=10.0)`
Requests dynamic formation trajectories for all active drones.
- **Parameters**:
  - formation_type (str) - one of: "moving_circle", "sin_wave"
  - period (float) - duration of one complete cycle (seconds)
- **Returns**: tuple of (start_positions dict, trajectories dict)
  - start_positions: {uri → (x, y, z)} - first waypoint for each drone
  - trajectories: {uri → [(x,y,z,yaw), ...]} - full trajectory for each drone
- **Logic**:
  - Creates FormationCalculator instance
  - Calls appropriate method with `connected_to_formation` dict and period
  - Returns both starting positions and trajectories
- **Interactions**: Calls FormationCalculator methods

#### `positions_intersect(start_positions, end_positions, threshold=default)`
Checks if trajectories between two position sets would collide.
- **Parameters**:
  - start_positions (dict): {uri → (x, y, z)} starting positions
  - end_positions (dict): {uri → (x, y, z)} target positions
  - threshold (float): minimum safe distance (meters)
- **Returns**: bool - True if collision risk detected, False otherwise
- **Tolerance**: Handles different numbers of drones
  - If new drones appear in end positions: returns False with warning
  - If drones disappear: ignores them silently
- **Interactions**: Delegates to FormationCalculator

#### `get_transition_positions(start_positions, end_positions)`
Generates multi-step transition path to avoid collisions.
- **Parameters**:
  - start_positions (dict): current drone positions
  - end_positions (dict): desired target positions
- **Returns**: list of position dicts representing intermediate steps
  - Step 1: Vertical elevation (lift)
  - Step 2: Horizontal repositioning (permute)
  - Step 3: Vertical descent to final height (drop)
- **Interactions**: Delegates to FormationCalculator

---

## FormationCalculator Class

### Overview
The FormationCalculator is a stateless utility that generates formation positions and trajectories. It contains no drone state and can be instantiated with custom boundaries.

### Stored Values

#### Spatial Configuration
- **`min_spacing`** (float): Minimum safe distance between drones (meters)
- **`boundaries`** (dict): 3D arena limits
  - `boundaries["x"]`: (min, max) X coordinate bounds
  - `boundaries["y"]`: (min, max) Y coordinate bounds
  - `boundaries["z"]`: (min, max) Z coordinate bounds (altitude)

### Functions

#### `__init__(spacing, x_boundaries, y_boundaries, z_boundaries)`
Initializes calculator with arena dimensions.
- **Parameters**:
  - spacing (float): minimum drone spacing (default from config)
  - x/y/z_boundaries (tuple): (min, max) for each axis
- **Default Boundaries**: Uses absolute_boundaries from config.py

#### `plot_formation(position_sets)`
Visualizes one or more formation snapshots in 3D.
- **Parameters**: position_sets (list of dicts) - each dict is {uri → (x, y, z)}
- **Visualization**: Creates 3D scatter plot with configurable axis limits
- **Usage**: Debug tool to verify formation geometry

---

### Static Formation Methods

#### `available_drones(drones)`
Filters connected drones from a drone status dict.
- **Parameters**: drones (dict) - {uri → bool} where bool = connected
- **Returns**: list of URIs that are connected
- **Error Handling**: Raises ValueError if no drones available

#### `flat_square(drones)`
Arranges drones in a 2D grid pattern.
- **Parameters**: drones (dict) - {uri → connected_bool}
- **Returns**: {uri → (x, y, z)} positions
- **Layout Logic**:
  - Calculates grid as √n × √n
  - Distributes evenly across arena X and Y
  - Places all drones at mid-height Z
  - Respects minimum spacing requirement
- **Safety**: Raises error if insufficient space for spacing

#### `circle(drones)`
Arranges drones in a circle.
- **Parameters**: drones (dict) - {uri → connected_bool}
- **Returns**: {uri → (x, y, z)} positions
- **Layout Logic**:
  - Calculates radius from arena dimensions minus spacing
  - Places drones at equal angular intervals around center
  - All drones at mid-height Z
- **Center**: Arena center (average of X and Y bounds)

#### `tilted_plane(drones, angle_x=45°, angle_y=45°)`
Arranges drones in a tilted plane.
- **Parameters**:
  - drones (dict) - {uri → connected_bool}
  - angle_x, angle_y (float) - tilt angles in degrees
- **Returns**: {uri → (x, y, z)} positions
- **Logic**:
  - Starts with flat_square layout
  - Tilts Z position based on (x, y) coordinates using tangent
  - Clamps Z to stay within boundaries with margins
- **Formula**: z_tilted = z_base + x·tan(angle_x) + y·tan(angle_y)

---

### Dynamic Formation Methods

#### `moving_circle(drones, period=circle_rotation_period)`
Generates circular rotation trajectory.
- **Parameters**:
  - drones (dict) - {uri → connected_bool}
  - period (float) - time for one complete rotation (seconds)
- **Returns**: (start_positions, trajectories) tuple
- **Logic**:
  - Starting positions: Same as static circle()
  - Each drone maintains altitude but rotates around center
  - Generates `num_points = period / dynamic_waypoint_dt` waypoints
  - Each waypoint includes yaw pointing toward center
- **Synchronization**: All drones complete one rotation in same time

#### `sin_wave(drones, amplitude=0.533m, period=8.0s)`
Generates vertical sine wave oscillation.
- **Parameters**:
  - drones (dict) - {uri → connected_bool}
  - amplitude (float) - height oscillation (meters)
  - period (float) - time for one complete cycle (seconds)
- **Returns**: (start_positions, trajectories) tuple
- **Layout Logic**:
  - Drones distributed along X axis
  - All at Y center
  - X position determines initial phase in sine wave
- **Z Motion Logic**:
  - Base Z: center of safe altitude range (0.2m to 1.8m for standard config)
  - Amplitude: clamped to fit within boundaries (no clipping)
  - Each waypoint: z = z_base + amplitude·sin(normalized_x + phase_increment)
  - Generates `num_points = period / dynamic_waypoint_dt` waypoints
- **Smooth Motion**: Amplitude pre-constrained so no boundary clipping occurs
  - `safe_amplitude = min(amplitude, (z_max_safe - z_min_safe) / 2)`

---

### Utility Methods

#### `_distance_between_lines(p1, p2, p3, p4)`
Calculates minimum distance between two 3D line segments.
- **Parameters**: Four 3D points defining two line segments
  - p1→p2: First line segment
  - p3→p4: Second line segment
- **Returns**: float - minimum distance
- **Handles**: Parallel lines, nearly-parallel lines, intersection cases
- **Used By**: positions_intersect()

#### `positions_intersect(pos_set1, pos_set2, threshold=0.15m)`
Checks if drone trajectories between two position sets would collide.
- **Parameters**:
  - pos_set1 (dict): {uri → (x, y, z)} start positions
  - pos_set2 (dict): {uri → (x, y, z)} end positions
  - threshold (float): minimum safe separation (meters)
- **Returns**: bool - True if any trajectory pair is closer than threshold
- **Tolerance**: Handles different numbers of drones
  - If new drones in pos_set2: returns False with warning (missing estimations)
  - If drones missing from pos_set2: ignores them (silently)
- **Logic**: Checks all pairs of trajectories using `_distance_between_lines()`
- **Used By**: Swarm to decide if multi-step transition needed

#### `transition_positions(start_positions, end_positions)`
Generates safe multi-step transition path.
- **Parameters**:
  - start_positions (dict): current positions
  - end_positions (dict): desired positions
- **Returns**: list of position dicts
  - [elevated_positions, horizontal_positions, final_positions]
- **Lift Phase**: Elevates drones based on their current height order
  - Sorts drones by Z coordinate
  - Spaces vertically across arena Z range
  - Ensures no collision during lift
- **Permute Phase**: Moves drones horizontally while elevated
  - Maintains elevated Z from lift phase
  - Allows X,Y repositioning without collision
- **Drop Phase**: Descends to final positions
  - Drones settle to target Z positions
- **Used By**: Swarm when `positions_intersect()` detects collision risk

---

## Interaction Flow

```
GUI
  ↓ (user clicks formation button)
  
Swarm.flat_square() / circle() / etc.
  ├→ (for static formations)
  │   FormationManager.get_formation_positions("flat_square")
  │     └→ FormationCalculator.flat_square(connected_to_formation)
  │           └→ returns {uri → (x,y,z)}
  │   Swarm.send_formation(positions)
  │
  └→ (for dynamic formations)
      FormationManager.get_dynamic_formation_positions("moving_circle", period)
        └→ FormationCalculator.moving_circle(connected_to_formation, period)
              └→ returns ({uri → (x,y,z)}, {uri → waypoints})
      Swarm.send_formation(start_positions)
      Swarm.send_dynamic_formation(trajectories, waypoint_dt)
```

## Formation Types Summary

| Formation | Type | Description | Motion |
|-----------|------|-------------|--------|
| Flat Square | Static | 2D grid pattern | None |
| Circle | Static | Circular arrangement | None |
| Tilted Plane | Static | Grid tilted on X/Y axes | None |
| Moving Circle | Dynamic | Drones orbit center point | Circular rotation |
| Sine Wave | Dynamic | Drones oscillate vertically | Vertical oscillation |

## Key Design Features

1. **Stateless Calculator**: FormationCalculator has no state, enabling reuse and testing
2. **Pluggable Boundaries**: Calculator accepts custom arena dimensions
3. **Safe Amplitudes**: Dynamic formations pre-clamp amplitudes to prevent boundary violations
4. **Collision Detection**: Can detect risky transitions and generate safe multi-step paths
5. **Tolerance for Variable Drones**: Handles formations with different numbers of drones
6. **Shared Clock Ready**: Trajectory format supports synchronized execution via shared clock
7. **Smooth Sine Waves**: Sine wave motion truly smooth, never clips at boundaries
