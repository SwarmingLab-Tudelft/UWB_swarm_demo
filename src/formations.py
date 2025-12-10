from dataclasses import dataclass
from config import absolute_boundaries, drone_spacing
import math

class FormationCalculator:
    def __init__(self, name, spacing=drone_spacing, x_boundaries=absolute_boundaries["x"], y_boundaries=absolute_boundaries["y"], z_boundaries=absolute_boundaries["z"]):
        self.name = name
        self.spacing = spacing
        self.boundaries = {
            "x": x_boundaries,
            "y": y_boundaries,
            "z": z_boundaries
        }
    def flat_square(self, n_drones):
        positions = []
        n_side = math.ceil(math.sqrt(n_drones))
        for i in range(n_drones):
            row = i // n_side
            col = i % n_side
            x = col * self.spacing
            y = row * self.spacing
            z = 1.0  # flat formation at z=1
            positions.append((x, y, z))
        return positions



class FormationManager:
    def __init__(self, uris):
        self.uris = uris
        # Additional formation parameters can be initialized here
        self.states = {uri : "disconnected" for uri in uris}  # Example state tracking
        self.n_connected_drones = 0

    def connect_to_formation(self, uri):
        if uri in self.uris:
            self.states[uri] = "connected"
            self.n_connected_drones += 1
            print(f"Drone {uri} connected to formation.")
        else:
            print(f"Drone {uri} not recognized.")

    def disconnect_from_formation(self, uri):
        if uri in self.uris and self.states[uri] != "disconnected":
            self.states[uri] = "disconnected"
            self.n_connected_drones -= 1
            print(f"Drone {uri} disconnected from formation.")
        else:
            print(f"Drone {uri} not recognized or already disconnected.")

    def get_formation_positions(self):
        formation = FormationCalculator("flat_square")
        connected_uris = [u for u, s in self.states.items() if s != "disconnected"]
        positions = formation.flat_square(len(connected_uris))
        return dict(zip(connected_uris, positions))