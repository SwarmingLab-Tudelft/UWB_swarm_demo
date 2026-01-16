# Radio URIs for the drones
uris = ['radio://0/100/2M/247E000001', 
        'radio://0/100/2M/247E000002', 
        'radio://0/100/2M/247E000003', 
        'radio://0/100/2M/247E000004']

# Boundary variables
absolute_boundaries = {
    "x": (-1.0, 1.0),
    "y": (-1.0, 1.0),
    "z": (0.0, 2.0)
}
drone_spacing = 0.2  # meters
boundary_margins = 0.2 # meters

# Formation variables
collision_threshold = 0.15  # meters
default_tilt_plane_angle_x = 45  # degrees
default_tilt_plane_angle_y = 45  # degrees

# Flight variables
takeoff_height = 0.8  # meters
takeoff_duration = 1.5  # seconds
landing_duration = 2.5  # seconds
position_convergence_time = 4.0  # seconds
position_convergence_distance = 0.2  # meters

# Formation variables
formation_transition_duration = 3.0  # seconds
circle_rotation_period = 12.0 # seconds
sin_wave_period = 12.0 # seconds
dynamic_sine_wave_amplitude = (absolute_boundaries['z'][1] - absolute_boundaries['z'][0] - 2 * boundary_margins) / 3 # meters
dynamic_sine_wave_period = 8.0  # seconds
dynamic_formation_points = 30  # number of waypoints in dynamic formation trajectories
dynamic_minus_dt = 0.15  # seconds to subtract from waypoint dt to ensure smoothness

# Communication variables
high_frequency_update_interval = 0.25 # seconds
low_frequency_update_interval = 1.0 # seconds
factor_connection_lost = 3.0 # multiplier for low frequency update interval to determine connection lost
reconnect_attempt_interval = 5.0 # seconds
position_cache_size = int(position_convergence_time / high_frequency_update_interval) # number of recent positions to store for smoothing

# Battery variables
default_battery_voltage = 3.0 # volts
low_battery_in_flight = 3.1 # volts
low_battery_on_ground = 3.6 # volts

# Closing variables
closing_threads_timeout = 4.0 # seconds

# Loop variables
swarm_loop_interval = 0.1 # seconds
dynamic_formation_polling_interval = 0.1 # seconds