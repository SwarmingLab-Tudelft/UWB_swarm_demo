from config import absolute_boundaries, drone_spacing
import matplotlib.pyplot as plt
import math

from config import *
from cflib.crazyflie.mem.trajectory_memory import Poly4D

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

    def _distance_between_lines(self, p1: tuple[float, float, float], p2: tuple[float, float, float], 
                                        p3: tuple[float, float, float], p4: tuple[float, float, float]) -> float:
        """
        Calculate the minimum distance between two 3D line segments.
        
        Line segment 1: from p1 to p2
        Line segment 2: from p3 to p4
        """
        def vector_subtract(a, b):
            return tuple(a[i] - b[i] for i in range(3))
        
        def vector_dot(a, b):
            return sum(a[i] * b[i] for i in range(3))
        
        def vector_length(v):
            return math.sqrt(sum(x**2 for x in v))
        
        # Direction vectors
        d1 = vector_subtract(p2, p1)  # Direction of line 1
        d2 = vector_subtract(p4, p3)  # Direction of line 2
        w0 = vector_subtract(p1, p3)  # Vector from p3 to p1
        
        a = vector_dot(d1, d1)  # |d1|²
        b = vector_dot(d1, d2)
        c = vector_dot(d2, d2)  # |d2|²
        d = vector_dot(d1, w0)
        e = vector_dot(d2, w0)
        
        denom = a * c - b * b
        
        # Handle parallel or nearly parallel lines
        if abs(denom) < 1e-10:
            # Lines are parallel, find closest point on line 1 to line 2
            t = 0
            if a > 1e-10:
                t = max(0, min(1, d / a))
            closest_p1 = tuple(p1[i] + t * d1[i] for i in range(3))
            
            # Find closest point on line 2 to this point
            s = 0
            if c > 1e-10:
                s_param = vector_dot(d2, vector_subtract(closest_p1, p3)) / c
                s = max(0, min(1, s_param))
            closest_p2 = tuple(p3[i] + s * d2[i] for i in range(3))
        else:
            # Find parameters for closest points
            t = max(0, min(1, (b * e - c * d) / denom))
            s = max(0, min(1, (a * e - b * d) / denom))
            
            # Calculate closest points
            closest_p1 = tuple(p1[i] + t * d1[i] for i in range(3))
            closest_p2 = tuple(p3[i] + s * d2[i] for i in range(3))
        
        # Return distance between closest points
        diff = vector_subtract(closest_p1, closest_p2)
        return vector_length(diff)

    def positions_intersect(self, pos_set1: dict[str, tuple[float, float, float]], pos_set2: dict[str, tuple[float, float, float]], threshold=collision_threshold) -> bool:
        """
        Check if trajectories from start to end positions intersect.
        True if any two trajectories are closer than the threshold, False otherwise
        """
        if len(pos_set1) != len(pos_set2):
            raise ValueError("Start and end position sets must have the same number of drones.")
        
        drones = list(pos_set1.keys())
        n_drones = len(drones)
        
        # Check all pairs of drone trajectories
        for i in range(n_drones):
            for j in range(i + 1, n_drones):
                drone_i = drones[i]
                drone_j = drones[j]
                
                # Get start and end points for each drone
                p1_start = pos_set1[drone_i]
                p1_end = pos_set2[drone_i]
                p2_start = pos_set1[drone_j]
                p2_end = pos_set2[drone_j]
                
                # Calculate minimum distance between the two line segments
                min_distance = self._distance_between_lines(p1_start, p1_end, p2_start, p2_end)
                
                # If distance is below threshold, trajectories intersect/collide
                if min_distance < threshold:
                    return True
        
        return False   

    def available_drones(self, drones: dict[str, bool]):
        available = [uri for uri, connected in drones.items() if connected]
        if not available:
            raise ValueError("No drones available for formation.")
        return available

    def flat_square(self, drones: dict[str, bool]): #{uris: connected (T/F)}
        available = self.available_drones(drones)
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

    def tilted_plane(self, drones: dict[str, bool], angle_x=default_tilt_plane_angle_x, angle_y=default_tilt_plane_angle_y):
        flat = self.flat_square(drones)
        positions = dict()
        angle_x_rad = math.radians(angle_x)
        angle_y_rad = math.radians(angle_y)
        for drone, (x, y, z) in flat.items():
            z_tilted = z + x * math.tan(angle_x_rad) + y * math.tan(angle_y_rad)
            z_tilted = max(self.boundaries["z"][0] + boundary_margins, min(self.boundaries["z"][1] - boundary_margins, z_tilted))
            positions[drone] = (x, y, z_tilted)
        return positions
    
    def circle(self, drones: dict[str, bool]):
        radius = min((self.boundaries["x"][1] - self.boundaries["x"][0]), (self.boundaries["y"][1] - self.boundaries["y"][0])) / 2 - self.min_spacing * 2
        available = self.available_drones(drones)
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
    
    def moving_circle(self, drones: dict[str, bool],  
                      period: float = circle_rotation_period, 
                      num_points: int = dynamic_formation_points):
        """Generate circular trajectory segments for each drone.
        
        Args:
            drones: dict {uri: connected_bool} - available drones
            period: time for one full rotation (seconds)
            num_points: number of waypoints around the circle
            
        Returns:
            tuple: (start_positions_dict, trajectories_dict)
                - start_positions_dict: {uri: (x, y, z)} for first waypoint
                - trajectories_dict: {uri: waypoints} ready for sending to drones
        """
        # Get initial circle positions (starting points)
        start_positions = self.circle(drones)
        
        # Calculate radius same way as circle()
        radius = min((self.boundaries["x"][1] - self.boundaries["x"][0]), (self.boundaries["y"][1] - self.boundaries["y"][0])) / 2 - self.min_spacing * 2
        
        # Arena center
        center = (
            (self.boundaries["x"][0] + self.boundaries["x"][1]) / 2,
            (self.boundaries["y"][0] + self.boundaries["y"][1]) / 2,
            (self.boundaries["z"][0] + self.boundaries["z"][1]) / 2
        )
        
        trajectories = {}
        
        for uri, (start_x, start_y, start_z) in start_positions.items():
            # Calculate this drone's starting angle on the circle
            start_angle = math.atan2(start_y - center[1], start_x - center[0])
            
            # Generate waypoints around the circle for this drone
            waypoints = []
            for k in range(num_points):
                angle = start_angle + 2 * math.pi * k / num_points
                x = center[0] + radius * math.cos(angle)
                y = center[1] + radius * math.sin(angle)
                z = start_z  # Keep each drone's altitude
                yaw = math.atan2(center[1] - y, center[0] - x) # Yaw pointing at center
                waypoints.append((x, y, z, yaw))  # (x, y, z, yaw pointing at center)
            
            
            trajectories[uri] = waypoints
        
        return start_positions, trajectories

    def sin_wave(self, drones: dict[str, bool], amplitude=dynamic_sine_wave_amplitude, period=dynamic_sine_wave_period, num_points=dynamic_formation_points):
        """Generate sine wave trajectory segments for each drone.
        
        Args:
            drones: dict {uri: connected_bool} - available drones
            amplitude: height of the sine wave (meters)
            period: time for one complete wave cycle (seconds)
            num_points: number of waypoints in one wave cycle
            
        Returns:
            tuple: (start_positions_dict, trajectories_dict)
                - start_positions_dict: {uri: (x, y, z)} for first waypoint
                - trajectories_dict: {uri: waypoints} ready for sending to drones
        """
        available = self.available_drones(drones)
        n_drones = len(available)
        
        # Middle Y position (arena center)
        y_middle = (self.boundaries["y"][0] + self.boundaries["y"][1]) / 2
        
        # Distribute drones evenly along X axis
        x_spacing = (self.boundaries["x"][1] - self.boundaries["x"][0]) / (n_drones + 1)
        x_min = self.boundaries["x"][0]
        x_max = self.boundaries["x"][1]
        
        # Base Z position (middle height)
        z_base = (self.boundaries["z"][0] + self.boundaries["z"][1]) / 2
        
        start_positions = dict()
        for i, uri in enumerate(available):
            x = self.boundaries["x"][0] + (i + 1) * x_spacing
            # Normalize x position to [0, 2π] range to create one complete wave cycle
            normalized_x = 2 * math.pi * (x - x_min) / (x_max - x_min)
            z = z_base + amplitude * math.sin(normalized_x)
            # Ensure Z stays within boundaries
            z = max(self.boundaries["z"][0] + boundary_margins, 
                    min(self.boundaries["z"][1] - boundary_margins, z))
            start_positions[uri] = (x, y_middle, z)
        
        # Generate trajectories with sine wave motion in Z
        trajectories = {}
        
        for uri, (start_x, start_y, start_z) in start_positions.items():
            waypoints = []
            for k in range(num_points):  # +1 to close the loop
                # X and Y remain constant (drone's position)
                x = start_x
                y = start_y
                
                # Z follows a sine wave pattern
                # Initial phase based on x position
                normalized_x = 2 * math.pi * (x - x_min) / (x_max - x_min)
                # Add phase increment for each waypoint k
                phase_increment = 2 * math.pi * k / num_points
                z = z_base + amplitude * math.sin(normalized_x + phase_increment)
                
                # Ensure Z stays within boundaries
                z = max(self.boundaries["z"][0] + boundary_margins, 
                        min(self.boundaries["z"][1] - boundary_margins, z))
                
                yaw = 0.0  # Neutral yaw since drone isn't moving horizontally
                waypoints.append((x, y, z, yaw))
            
            trajectories[uri] = waypoints
        
        return start_positions, trajectories

    def transition_positions(self, start_positions: dict[str, tuple[float, float, float]], end_positions: dict[str, tuple[float, float, float]]):
        '''
        Returns the intermediate positions for a lift-permute-drop transition
        as a list of position dictionaries: [elevated positions, horizontal shift positions, final
        Args:
            start_positions (dict): Starting positions of the drones.
            end_positions (dict): Target positions of the drones.
        Returns:
            list: A list of dictionaries representing intermediate positions.
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
        self.connected_to_formation = {uri : False for uri in uris}
        self.n_connected_drones = 0

    def connect_to_formation(self, uri):
        if uri in self.uris:
            self.connected_to_formation[uri] = True
            self.n_connected_drones += 1
            print(f"Drone {uri} connected to formation.")
        else:
            print(f"Drone {uri} not recognized.")

    def disconnect_from_formation(self, uri):
        if uri in self.uris and self.connected_to_formation[uri]:
            self.connected_to_formation[uri] = False
            self.n_connected_drones -= 1
            print(f"Drone {uri} disconnected from formation.")
        elif uri in self.uris:
            print(f"Drone {uri} is already disconnected from formation.")
        else:
            print(f"Drone {uri} not recognized.")

    def get_formation_positions(self, formation_type):
        if formation_type == "flat_square":
            positions = FormationCalculator().flat_square(self.connected_to_formation)
        elif formation_type == "tilted_plane":
            positions = FormationCalculator().tilted_plane(self.connected_to_formation)
        elif formation_type == "circle":
            positions = FormationCalculator().circle(self.connected_to_formation)
        else:
            raise ValueError("Unknown formation type.")
        return positions
    
    def get_dynamic_formation_positions(self, formation_type):
        '''
        Given the formation type, return the movements to get to a starting position and the trajectories to follow.
        Args:
            formation_type (str): Type of dynamic formation (e.g., "moving_circle", "sin_wave")
        '''
        if formation_type == "moving_circle":
            start_positions, trajectories = FormationCalculator().moving_circle(self.connected_to_formation)
        elif formation_type == "sin_wave":
            start_positions, trajectories = FormationCalculator().sin_wave(self.connected_to_formation)
        else:
            raise ValueError("Unknown dynamic formation type.")
        return start_positions, trajectories
    
    def positions_intersect(self, start_positions, end_positions, threshold=collision_threshold):
        return FormationCalculator().positions_intersect(start_positions, end_positions, collision_threshold)

    def get_transition_positions(self, start_positions, end_positions):
        return FormationCalculator().transition_positions(start_positions, end_positions)
