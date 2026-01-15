# Radio URIs for the drones
uris = ['radio://0/100/2M/247E000001', 
        'radio://0/100/2M/247E000002', 
        'radio://0/100/2M/247E000003']

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
formation_transition_duration = 3.0  # seconds

# Communication variables
high_frequency_update_interval = 0.25 # seconds
low_frequency_update_interval = 1.0 # seconds
factor_connection_lost = 3.0 # multiplier for low frequency update interval to determine connection lost
reconnect_attempt_interval = 5.0 # seconds

# Battery variables
default_battery_voltage = 3.0 # volts
low_battery_in_flight = 3.2 # volts
low_battery_on_ground = 3.6 # volts

# Closing variables
closing_threads_timeout = 4.0 # seconds

# Loop variables
swarm_loop_interval = 0.1 # seconds