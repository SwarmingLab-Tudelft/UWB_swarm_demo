from config import absolute_boundaries, drone_spacing
import matplotlib.pyplot as plt
import math

class FormationCalculator:
    def __init__(self, spacing=drone_spacing, x_boundaries=absolute_boundaries["x"], y_boundaries=absolute_boundaries["y"], z_boundaries=absolute_boundaries["z"]):
        self.min_spacing = spacing
        self.boundaries = {
            "x": x_boundaries,
            "y": y_boundaries,
            "z": z_boundaries
        }

    def plot_formation(self, position_sets: list[dict[str, tuple[float, float, float]]]):
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        sets = []
        for i, positions in enumerate(position_sets):
            xs = [pos[0] for pos in positions.values()]
            ys = [pos[1] for pos in positions.values()]
            zs = [pos[2] for pos in positions.values()]
            scatter = ax.scatter(xs, ys, zs, label=f'Set {i+1}')
            sets.append(scatter)

        ax.set_xlim(self.boundaries["x"])
        ax.set_ylim(self.boundaries["y"])
        ax.set_zlim(self.boundaries["z"])
        ax.set_xlabel("X Axis")
        ax.set_ylabel("Y Axis")
        ax.set_zlabel("Z Axis")
        if len(sets) > 1:
            ax.legend()

        plt.show()

    def flat_square(self, drones: dict[str, str]): #{uris: states}
        available = [uri for uri, state in drones.items() if state == "charging" or state == "connected" or state == "idle" or state == "flying"]
        n_drones = len(available)
        positions = dict()
        n_side = math.ceil(math.sqrt(n_drones))
        x_spacing = (self.boundaries["x"][1] - self.boundaries["x"][0]) / (n_side + 1)
        y_spacing = (self.boundaries["y"][1] - self.boundaries["y"][0]) / (n_side + 1)
        if x_spacing < self.min_spacing or y_spacing < self.min_spacing:
            raise ValueError("Not enough space to arrange drones with the given spacing.")
        i = 0
        for drone in available:
            row = i // n_side
            col = i % n_side
            x = self.boundaries["x"][0] + (col + 1) * x_spacing
            y = self.boundaries["y"][0] + (row + 1) * y_spacing
            z = (self.boundaries["z"][1] - self.boundaries["z"][0]) / 2 # flat formation at the middle of the z boundaries
            positions[drone] = (x, y, z)
            i += 1
        return positions

    def tilted_plane(self, drones: dict[str, str], angle_x=45, angle_y=45):
        flat = self.flat_square(drones)
        positions = dict()
        angle_x_rad = math.radians(angle_x)
        angle_y_rad = math.radians(angle_y)
        for drone, (x, y, z) in flat.items():
            z_tilted = z + x * math.tan(angle_x_rad) + y * math.tan(angle_y_rad)
            z_tilted = max(self.boundaries["z"][0] + 0.2, min(self.boundaries["z"][1] - 0.2, z_tilted))
            positions[drone] = (x, y, z_tilted)
        return positions
    
    def circle(self, drones: dict[str, str]):
        radius = min((self.boundaries["x"][1] - self.boundaries["x"][0]), (self.boundaries["y"][1] - self.boundaries["y"][0])) / 2 - self.min_spacing * 2
        available = [uri for uri, state in drones.items() if state == "charging" or state == "connected" or state == "idle" or state == "flying"]
        n_drones = len(available)
        positions = dict()
        angle_increment = 2 * math.pi / n_drones
        for i, drone in enumerate(available):
            angle = i * angle_increment
            x = (self.boundaries["x"][0] + self.boundaries["x"][1]) / 2 + radius * math.cos(angle)
            y = (self.boundaries["y"][0] + self.boundaries["y"][1]) / 2 + radius * math.sin(angle)
            z = (self.boundaries["z"][1] - self.boundaries["z"][0]) / 2 # circle formation at the middle of the z boundaries
            positions[drone] = (x, y, z)
        return positions
    
    def transition_positions(self, start_positions: dict[str, tuple[float, float, float]], end_positions: dict[str, tuple[float, float, float]]):
        '''
        We will implement lift–permute–drop strategy to avoid collisions during transitions.
        '''
        if len(start_positions) != len(end_positions):
            raise ValueError("Start and end positions must have the same number of drones.")
        # Sort them by height, distribute vertically respecting that order
        sorted_start_height = sorted(start_positions.keys(), key=lambda uri: start_positions[uri][2])
        n_levels = len(sorted_start_height)
        z_sapacing = (self.boundaries["z"][1] - self.boundaries["z"][0]) / (n_levels + 1)
        if z_sapacing < self.min_spacing:
            raise ValueError("Not enough vertical space to arrange drones for transition.")
        vertical_shift = dict()
        intermediate_positions = []
        for i, uri in enumerate(sorted_start_height):
            z = self.boundaries["z"][0] + (i + 1) * z_sapacing
            vertical_shift[uri] = (start_positions[uri][0], start_positions[uri][1], z)
        intermediate_positions.append(vertical_shift)
        # Move horizontally to the target x,y while maintaining the elevated z
        sorted_end_height = sorted(end_positions.keys(), key=lambda uri: end_positions[uri][2])
        horizontal_shift = dict()
        for uri in sorted_end_height:
            x = end_positions[uri][0]
            y = end_positions[uri][1]
            z = vertical_shift[uri][2]
            horizontal_shift[uri] = (x, y, z)
        intermediate_positions.append(horizontal_shift)
        # Descend to the target z
        final_positions = end_positions
        intermediate_positions.append(final_positions)
        return intermediate_positions


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