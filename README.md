 This is the initiative to make an UWB demo for the swamring lab.
 The idea behind this project is to change the current demo that utilises lighthouse system with an UWB positioning system.
 The project will have it's focus on simplicity and reliability.

Instructions for operators:

This demo works with all crazyflie positioning systems, as long as the drone is able to estimate it's own state in the global frame. The systems that support this are lighthouse, loco (UWB) and infrared cameras.

To run the demo, first you will need to know the drone's addresses, and add them in the src/config.py. Prepare the drones with whichever setup you will use for positioning, and place them in the flying are.

To run the demo, it is recommended to use a virtual enviroment. In this project we are using uv. In VS Code, it will automatically detect it and you don't need to do anything else, just run main.py. To run it from the terminal, run 
uv sync
uv run src/main.py