The idea of this project plan is to set clear requirements and objective, to set a clear path to follow during the development of the project, and to serve as a guide for future developers to understand the decisions taken in the project.

## Analisis
The Swarming Lab is a research space for TU Delft student and staff. It serves as an accessible space for anyone to come test out algothims or other types of protocols. The swarming lab belongs to the Science Centre, and has stakeholders from several faculties. One of the tasks of the lab, is to serve to the science centre as an exposition or showcase of the science and research being developed at TU Delft. The materialization of this, are dmeos that can be taken by the Science Centre on Tour, or run in the lab, so it can be shown to the general public.

For this the Swamring Lab has developed a demo with Cazyflies drones using the Ligthhouse positioning system. However, this system has proven to be unreliable in uncontrolled enviroments, that is, outside of the lab. The drones have also shown behavioral issues when operating with low batteries, and interference with common wifi and bluetooth signals, that cause issues in communication. On top of that, the current demo operates in a "complicated" way. It is using local ports for communication among 3 different programs, a python UI, a C++ program and a unity engine collision avoidance. We believe this solution makes this program very scalable, but not very reliable, since it is hard to develop on and debug.

Therefore, this projects aims to solve this situation, by:
- Changing to an UWB system instead of the sensitive lighthouse infrared system
- Solve communication interference and battery issues as much as possible
- Make the program simple to read an understand, using a single script demo

We believe that this can help sole the proposed problem, and give outreach and visibility to the lab and the Science Centre.

## Requirements
The requirements will be split into the most criticial funcitonalities hat will need to be implemented, and more optional functionalities that will make the program more attractive.
Must haves:
- Must connect and maintain the communication with the drones
- Must be able to fly 8 drones simultaneously
- Must be able to put the drones in a given formation from take off
- Must be able to keep the drones in a given formation
- Must use UWB system (loco positioning) for positioning
- Must have a user interface that allows the operator to start and stop the demo
- Must application must land the drones in case of communication loss or sudden stop of the program
Should have:
- Should perform stationary check to validate convergence of position
- Should allow to change among different formations
- Should have dynamic formations
Could have:
- Could log measured flight estimations for post-flight debugging
- Could allow the operator or visitors to create custom trayectories
- Could take controller inputs to move the static formations

## Feasibililty
This project is in principle going ot be developed by a single person. The time extension is estimated to be between 3 to 6 months, depending on issues encountered on the development. All the must haves and should haves are completely reasonable and done before. The could haves have not all been integrated at the same time, but similar projects already exist with that type of features. The biggest challenge of this project is to keep the program simple while funtional, and able to implement all funtionalities while keeping a low latency.

In case that we realise it is completely immposible to develop such a project, there is the possiblity to change to a 2 script program, making them communicate through local ports. This way, a fast C file could do the math operations and the pytohn can do the GUI and send the radio packages. This will try to be avoided as it would bring a new layer of complexity into the project that is one of the main problems we are trying to tackle.

## Technical preparation
The main package needed to develop this project is the cflib library. Inside it, there are several options possible, although the Swarm class seems to be the most benefitial for it's very high level structure.
On top of that, it is important to familiarise ourselves with the UWB ecosystem and hardware, since it has an established set up procedure.

On top of that, the package that will support the GUI will be Tkinter because of it's simplicity and simple integration.

To keep the program as simple as possible, we are going to make a single script program, that handles the GUI and the comminucation with the drones. The drones will only recieve high level orders and they will be in charge of all the stabilization and control.
