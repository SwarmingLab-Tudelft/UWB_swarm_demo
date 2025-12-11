'''
This is the file for testing without using the hardware
'''
from formations import FormationCalculator

drones = {
    "radio://0/80/2M/E7E7E7E701": "flying",
    "radio://0/80/2M/E7E7E7E702": "flying",
    "radio://0/80/2M/E7E7E7E703": "flying",
    "radio://0/80/2M/E7E7E7E704": "flying",
    "radio://0/80/2M/E7E7E7E705": "flying",
    "radio://0/80/2M/E7E7E7E706": "flying", 
    "radio://0/80/2M/E7E7E7E707": "flying",
    "radio://0/80/2M/E7E7E7E708": "flying",
    "radio://0/80/2M/E7E7E7E709": "flying"
}

formation = FormationCalculator()
formation1 = formation.tilted_plane(drones, angle_x=45, angle_y=45)
formation2 = formation.circle(drones)
steps = formation.transition_positions(formation1, formation2)
steps = [formation1] + steps
formation.plot_formation(steps)