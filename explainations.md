# How the code works
This file is meant to explain vertain Crazyflie concepts, and why the cose is structured as it is.
## Code structure
The code consists of 2 main object, a ControlTowerGUI and a CrazyflieSwarm. Each of this objects use other object to help organise their functionalities.
Both objects are initialised in main.py, the swarm CrazyflieSwarm is launched on a thread (and running on the back) While the GUI, made with Tkinter runs in the main thread. The GUI was adopted from Bitcraze swarm example, and becuase it's simple to edit.
Now we will go in depth on both main parts, that interact with eachoter
## GUI
The CrazyflieReport object is the simple box of indormation that corresponds for each Crazyflie. Is shows several information that was there by default, the most relevants are probably status and battery.
CrazyflieReport objects are created by the main GUI object, ControlTowerGUI. One Crazyflie report per drone. This creation happens at inialization of the object, calling self._create_cf_grid(). Also, the buttons are created with self._create_controls() and the closing protocol (still to be done) by  self.configure_close_action(). 
In Tkinter everything happens in the tkinter.Tk(), initialised as sef.root. That is, to make things happen in the GUI they need to be added into that loop. The information update loop is started when initialised, and then it calls itself infinitely. This function is called update_gui_loop(). All logic that the GUI has to do should be added in this loop. Preferably, by making functions and calling them in the loop. Right now, this funtion only calls the swarm to ask for the state and the battery to update it into the GUI. In the future we will also try to reconnect if the connection was not succesful in the first place.
## Swarm
The Swarm objec tis possibly the most complex one, it does 4 things. 
1. Communicates with the drones by opening the links and sending high level commands.
2. Polls the drone information with certain frequency by using logs. More on this later
3. Has a formation class, that does the calcualtions nedded for the formation control
4. Keeps the information for the GUI to access and update
All of this information is accessed concurrently, so it uses a Lock to keep the information consistet. It works like mautex, blocking the access to memory while reading it or modifying it.
For task 1: For storing comunication info it uses, uris, a dict of scfs = {uri: SyncCrazyflie} and a threads dict {uri: Thread} to keep them organised. The "id" od the drones is the radio address.
For tasks 2 and 4: The information recieved on the communication packages recieves is stored into cache to access it later by the GUI.
For task 3: The formation class is still in development. The intention of that class is to keep track of how make drones are available at any time, and design a formation from several options (still to be determined). Then it will return to the swarm the positions that need to be sent to every drone. It will also do the planning for avoiding collisions between formations.
## Logging
As promised before, we will go into logging, as it is rather strange if it's not been used before.
When a link is "opened" by using scf.open_link() (used by the connect_one()), internally the program is opening a link connection on a background python thread. A few lines later, we call _setup_logging(uri, scf). This funtion will make a LogConfig object. This object sill be transformed into a package and be sent only once to the crazyflie. This object contains information of what informations needs to be transmited an how often. The crazyflie will take this information and incorporate it into it's own firmware, and do that reporting automatically.
Then, we manufacture a function to happen every time this reporting reaches us, this is the function _callback. This is, what to do every time we recieve a package, in our case updating the cache. In case we want new information we need to make a new LogConfig, set the variables to call and then make a function to process that info. Another option is to add more variables on the already existing battery report.
We looked into it, and there is no simple cf.read_battery() function, so this is the method to obtaining iformation from the drones.