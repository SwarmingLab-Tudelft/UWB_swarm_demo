# How the code works
This file is meant to explain vertain Crazyflie concepts. This is not meant to explain how the code itself works, but how the cflib fucntions work, so the code is easier to unserstand later. The developmetn readmes are in th readme folder

## Tkinter
In Tkinter everything happens in the tkinter.Tk(), initialised as sef.root. That is, to make things happen in the GUI they need to be added into that loop. The information update loop is started when initialised, and then it calls itself infinitely. This function is called update_gui_loop(). All logic that the GUI has to do should be added in this loop. Preferably, by making functions and calling them in the loop. Right now, this funtion calls the swarm to ask for the state and the battery to update it into the GUI. This should not include swarm logic itelf, but only GUI updates. The crazyflie swarm will have it's own loop to run that logic.
## Swarm
The Swarm object is possibly the most complex one, it does 4 things. 
1. Communicates with the drones by opening the links and sending high level commands.
2. Handles logs packages recieved by the drone by using logs. More on this on the logging chapter
3. Has a formation class, that does the calculations nedded for the formation control
4. Keeps the information for the GUI to access and update
All of this information is accessed concurrently, so it uses a Lock to keep the information consistent. It works like mutex, blocking the access to memory while reading it or modifying it.

## Logging
When a link is "opened" by using scf.open_link() (used by the connect_one()), internally the program is opening a link connection on a background python thread. A few lines later, we call _setup_logging(uri, scf). This funtion will make a LogConfig object. This object will be transformed into a package and be sent only once to the crazyflie. This object contains information of what informations needs to be transmited an how often. The crazyflie will take this information and incorporate it into it's own firmware, and do that reporting automatically.
Then, we manufacture a function to happen every time this reporting reaches us, this is the function _callback. This is, what to do every time we recieve a package, in our case updating the cache. In case we want new information we need to make a new LogConfig, set the variables to call and then make a function to process that info. Another option is to add more variables on the already existing battery report.
There is no simple cf.read_battery() function, so this is the method to obtaining information from the drones' state.
## Commander and High Level Commander
The Commander and high level commander are used throughout the project for similar purposes. The difference between them is that HLC sends a single setpoint and a duration, and the drone will be the one interpolating it's current posisiton to the final position to reach the destination at the required time. That is, internally the drone is craitng waypoints and followign them smoothly. The HLC send the information only once, and it is a longer to process package, that will take time to interpolate and create the different waypoints for the drone.
On the other hand, the Commander sends those waypoitns directly. That is, it sends the desired state of the drone, and the drone will include this desired location in it's control loop. When using the Commander, waypoints need to be sent very often (10-20Hz) for the trajectory to be smooth. On top of that, the waypoints sent are only valid for 500ms, so if the crazyflie has not recieved a new waypoint in that time will just mainain thrust and nothing else.

In this project, the static formations use the HLC since the position only needs to be sent once, and the dynamic formations use the Commander.

A relevant point of diffenence is that, in case of recieving setpoint from both the hlc and the commander, the drone will prioritise the commander, since it is more low-level, and it might be a manager taking over a drone. That is why, in this project, flags are used to mark when the commander needs to be deactivated to pass to use the hlc, the swarm store these flags.

## Dynamic formations
In the future there exists the possiblilty to upload Trajectory() to the drone's memory, that works in a similar way. From what we know now, the trajectories are loaded onto the memory, and the order sent is just to start them.


## In the future
Things to be implemented are:
- Takeoff and landing in known positions

In the firmware:
- Land when losing connection
- Perform ranging with other tags for higher accuracy

Testing:
- Flight time
- Number of drones max
- Unit tests for FormationManager

Code improvements:
- Add easier radio editing
- Code needs a lot of improvement in comments, docstrings, variable names, and factorisation

Known bugs:
- Reconnecition regulary fails when disconneced and trying to reconnect
- When doing an emergency landing, the drone needs to be restarted, becasue the connection is "blocked". Add in documentation