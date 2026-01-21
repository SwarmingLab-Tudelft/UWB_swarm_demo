# GUI Documentation

## Overview
The GUI provides a user interface for controlling a swarm of Crazyflie drones. It displays real-time status information for each drone and provides buttons to control flight and formations.

Inside the GUI file there are 2 classes. The `Crazyflie_report` is the basic building block for giving information about one drone. This class is then used by `ControlTowerGUI` to generate the GUI.

This GUI is done with Tkinter, a Python GUI library that comes built-in with Python.

## Crazyflie_report Class
This class represents a single drone widget displayed in the GUI. Each widget shows:
- **Drone Name & URI**: Displays the drone's identifier and radio URI
- **Status Display**: Shows the drone state (idle, connecting, connected, disconnected, crashed, flying, landing) with color coding:
  - Grey: idle/disconnected
  - Orange: connecting
  - Blue: connected
  - Red: crashed
  - Green: flying/landing
  - Purple: error/charging
- **Battery Information**: Shows voltage and a progress bar indicating battery level
- **Individual Controls**: 
  - "Takeoff One" button: Launches individual drone
  - "Land One" button: Lands individual drone

The widget updates in real-time by querying the swarm object for the drone's state and battery voltage in the swarm caches (more on the swarm caches later).

## ControlTowerGUI Class
This is the main GUI window that orchestrates the entire interface. It:

### Creates the Grid Layout:
- Arranges drone widgets in a 3-column grid layout
- Creates one `Crazyflie_report` widget per connected drone
- Scales automatically based on number of drones

### Provides Swarm Controls (Bottom Panel):

When pressing a button, a swarm command is issued. This is configured in `_create_controls()`

**Flight Control Row:**
- "Take off" (green): Commands all drones to takeoff
- "Land" (blue): Commands all drones to land
- "Emergency land" (red): Forces immediate landing by stopping the motors

**Static Formation Row:**
- "Flat Square" (orange): Arranges drones in a 2D grid pattern
- "Circle" (orange): Arranges drones in a circular pattern
- "Tilted Plane" (orange): Arranges drones in a tilted plane formation

**Dynamic Formation Row:**
- "Moving Circle" (purple): Drones rotate in a circle
- "Sine Wave" (purple): Drones oscillate in height following a sine wave

### Updates Display:
- Runs `update_gui_loop()` every 200ms. This is the GUI refresh rate.
- In that principal loop:
  - Queries swarm for current drone states and battery levels
  - Updates widget displays in real-time

### Manages Safe Shutdown:
- Implements `_configure_close_action()` to ensure clean shutdown. This is called when the window is closed.
- Stops background threads
- Forces drones to land if still flying
- Closes all communication links
- Destroys the GUI window gracefully

## Button Callbacks
When a user clicks a button, it calls the corresponding method on the swarm object:
- `self.swarm.takeoff()`, `self.swarm.land()`, `self.swarm.emergency_land()`
- `self.swarm.flat_square()`, `self.swarm.circle()`, `self.swarm.tilted_plane()`
- `self.swarm.moving_circle()`, `self.swarm.sin_wave()`

The individual drone takeoff/land buttons run in separate threads to prevent GUI freezing.
