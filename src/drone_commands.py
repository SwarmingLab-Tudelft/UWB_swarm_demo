from logging import info
import logging
import threading
import time

from formations import FormationManager
from config import *

from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.log import LogConfig

# Suppress verbose cflib logging (link errors, packet loss messages)
logging.getLogger('cflib').setLevel(logging.ERROR)

class CrazyflieSwarm:
    '''Handles connections and commands to a swarm of crazyflies. Reads information from logs'''
    def __init__(self, uris):
        self.uris = uris
        self.scfs = {}     # {uri: SyncCrazyflie}
        self.link_threads = {}  # {uri: Thread}
        ## When modifying a dict, a lock is needed. It works like a mutex
        self.lock = threading.Lock()
        self.running = False
        ## Drone information, polled in the update loop with certain frequency
        self.battery_cache = {uri: default_battery_voltage for uri in uris}
        # options are: idle, connecting, connected, disconnected, flying, hovering, landing, and error
        self.state_cache = {uri: "disconnected" for uri in uris}
        self._last_state_update_time = {uri: time.time() for uri in uris}
        self.current_positions = dict() # {uri: (x, y, z)}
        ## Logging
        self._log_configs = {}
        ## Formation parameters
        self.formations = FormationManager(uris)


    # ---------------------------
    # CONNECT ALL DRONES
    # ---------------------------
    def _setup_logging(self, uri, scf):
        """Create Crazyflie log block."""
        cf = scf.cf

        log_low_freq = LogConfig(name=f'bat_{uri}', period_in_ms=low_frequency_update_interval*1000)
        log_low_freq.add_variable('pm.vbat', 'float') # Voltage
        log_low_freq.add_variable('supervisor.info', 'uint16_t') # State

        log_high_freq = LogConfig(name=f'pos_{uri}', period_in_ms=high_frequency_update_interval*1000)
        log_high_freq.add_variable('kalman.stateX', 'float')  # X position
        log_high_freq.add_variable('kalman.stateY', 'float')  # Y position
        log_high_freq.add_variable('kalman.stateZ', 'float')  # Altitude

        # Callbacks
        def _supervisor_cb(data):
            info = data.get('supervisor.info')  # raw uint16
            state = self.get_drone_state(uri)  # default state
            if info is None:
                pass
            else:
                # decode bits
                self._last_state_update_time[uri] = time.time()
                states = {
                    'can_be_armed': bool(info & (1 << 0)),
                    'is_armed': bool(info & (1 << 1)),
                    'auto_arm': bool(info & (1 << 2)),
                    'can_fly': bool(info & (1 << 3)),
                    'is_flying': bool(info & (1 << 4)),
                    'is_tumbled': bool(info & (1 << 5)),
                    'is_locked': bool(info & (1 << 6)),
                    'is_crashed': bool(info & (1 << 7)),
                    'hlc_active': bool(info & (1 << 8)),
                    'hlc_trajectory_finished': bool(info & (1 << 9)),
                    'hlc_disabled': bool(info & (1 << 10))
                }
                if states['is_flying']:
                    state = "flying"
                elif states['can_fly']:
                    state = "idle"
                elif states['is_crashed'] or states['is_tumbled']:
                    state = "crashed"
                else:
                    state = "connected"  # connected but not flying/can_fly/crashed
            with self.lock:
                self.state_cache[uri] = state

        def _battery_cb(data):
            voltage = data.get('pm.vbat')
            if voltage is None:
                return default_battery_voltage
            with self.lock:
                self.battery_cache[uri] = voltage

        def _position_cb(data):
            x = data.get('kalman.stateX')
            y = data.get('kalman.stateY')
            z = data.get('kalman.stateZ')
            if x is None or y is None or z is None:
                return
            self.current_positions[uri] = (x, y, z)

        def _low_freq_callback(ts, data, logconf):
            _supervisor_cb(data)
            _battery_cb(data)

        def _high_freq_callback(ts, data, logconf):
            _position_cb(data)     

        try:
            # Low freq log
            cf.log.add_config(log_low_freq)
            log_low_freq.data_received_cb.add_callback(_low_freq_callback)
            log_low_freq.start()
            # High freq log
            cf.log.add_config(log_high_freq)
            log_high_freq.data_received_cb.add_callback(_high_freq_callback)
            log_high_freq.start()
            self._log_configs[uri] = (log_low_freq, log_high_freq)
            print(f"[OK] Logging started for {uri}")
        except Exception as e:
            print(f"[ERROR] Failed to start logging for {uri}: {e}")

    def connect_one(self, uri):
        try:
            scf = SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache'))
            scf.open_link()

            with self.lock:
                self.scfs[uri] = scf

            # Start telemetry
            self._setup_logging(uri, scf)

            print(f"[OK] Connected to {uri}")
        except Exception as e:
            with self.lock:
                self.scfs[uri] = None

    def connect_all(self):
        for uri in self.uris:
            t = threading.Thread(target=self.connect_one, args=(uri,))
            t.start()
            self.link_threads[uri] = t

        # Wait for all connections
        for t in self.link_threads.values():
            t.join()
    def close_links(self):
        for uri, scf in self.scfs.items():
            try:
                if scf and hasattr(scf, "close_link"):
                    scf.close_link()
            except Exception as e:
                print(f"[ERROR] Could not close link to {uri}: {e}")
        print("[INFO] Links closed")
    # ---------------------------
    # GET DRONE STATES
    # ---------------------------
    def get_drone_state(self, uri):
        return self.state_cache.get(uri, "disconnected")
    
    def get_drone_battery(self, uri):
        return self.battery_cache.get(uri, default_battery_voltage)

    # ---------------------------
    # TAKE OFF
    # ---------------------------
    def takeoff_one(self, uri, scf, height, duration):
        try:
            if self.get_drone_battery(uri) < low_battery_on_ground:
                print(f"[WARNING] Battery too low for takeoff: {uri}")
                return
            if self.get_drone_state(uri) == "flying":
                print(f"[INFO] Drone already flying: {uri}")
                return
            hlc = scf.cf.high_level_commander
            hlc.takeoff(height, duration)
            self.formations.connect_to_formation(uri)
            print(f"[TAKEOFF] {uri}")
        except Exception as e:
            print(f"[ERROR] Takeoff failed for {uri}: {e}")

    def takeoff(self, height=takeoff_height, duration=takeoff_duration):
        for uri, scf in self.scfs.items():
            if scf is None:
                continue
            threading.Thread(target=self.takeoff_one, args=(uri, scf, height, duration)).start()

    # ---------------------------
    # LAND
    # ---------------------------
    def land_one(self, uri, scf, duration):
        try:
            if self.get_drone_state(uri) == "flying":
                hlc = scf.cf.high_level_commander
                hlc.land(0.0, duration)
                self.formations.disconnect_from_formation(uri)
                print(f"[LAND] {uri}")
        except Exception as e:
            print(f"[ERROR] Land failed for {uri}: {e}")

    def land(self, duration=landing_duration):
        for uri, scf in self.scfs.items():
            if scf is None:
                continue
            threading.Thread(target=self.land_one, args=(uri, scf, duration)).start()

    # ---------------------------
    # EMERGENCY LAND (MOTOR KILL)
    # ---------------------------
    def emergency_one(self, uri, scf):
        if scf is None:
            return
        try:
            print(f"[EMERGENCY] Stopping motors for {uri}")
            scf.cf.commander.send_stop_setpoint()  # immediate motor stop
        except Exception as e:
            print(f"[ERROR] Emergency stop failed for {uri}: {e}")

    def emergency_land(self):
        for uri, scf in self.scfs.items():
            threading.Thread(target=self.emergency_one, args=(uri, scf)).start()

    ## ---------------------------
    # SAFE SHUTDOWN
    ## ---------------------------
    def stop_background(self, timeout=closing_threads_timeout):
        """Stop update loop, stop and remove any active LogConfig callbacks and join threads.
        This will stop logging callbacks from running.
        """
        # stop main update loop
        self.running = False
        try:
            if getattr(self, "thread", None) is not None and self.thread.is_alive():
                self.thread.join(timeout=timeout)
        except Exception:
            pass

        # stop and remove any LogConfig objects (stop callbacks/background logging)
        with self.lock:
            for uri, log in list(self._log_configs.items()):
                try:
                    # stop the LogConfig's internal timer/worker
                    try:
                        log.stop()
                    except Exception:
                        pass
                    # if we still have an open SyncCrazyflie for this uri, remove the config
                    scf = self.scfs.get(uri)
                    if scf and hasattr(scf, "cf") and hasattr(scf.cf, "log"):
                        try:
                            scf.cf.log.remove_config(log)
                        except Exception:
                            pass
                except Exception:
                    pass
            # clear references so callbacks can be GC'd
            self._log_configs.clear()

        # join any connection threads
        for uri, t in list(self.link_threads.items()):
            try:
                if t is not None and t.is_alive():
                    t.join(timeout=closing_threads_timeout)
            except Exception:
                pass

        print("[INFO] Swarm background stopped and logging disabled")
    
    def forced_stop_flying(self):
        """Lands all drones that are currently flying, then issues emergency stop if they have not landed."""
        self.land(duration=landing_duration)
        time.sleep(3.0)  # wait a moment before emergency stop
        if any(self.scfs.state_cache[uri] == "flying" for uri in self.uris):
            self.emergency_land()

    ## ---------------------------
    # FORMATION COMMANDS
    ## ---------------------------
    def send_formation(self, target_formation, duration=formation_transition_duration):
        """Sends position commands to all drones to move to the specified positions over the given duration."""
        if self.current_positions is not None:
            # Check for potential collisions
            if self.formations.positions_intersect(self.current_positions, target_formation, threshold=collision_threshold):
                transition_positions = self.formations.get_transition_positions(self.current_positions, target_formation, threshold=collision_threshold)
            else:
                transition_positions = [target_formation]
        else:
            transition_positions = [target_formation]
        for transition_step in transition_positions:
            for uri, scf in self.scfs.items():
                if scf is None or uri not in transition_step:
                    continue
                x, y, z = transition_step[uri]
                try:
                    hlc = scf.cf.high_level_commander
                    hlc.go_to(x, y, z, 0.0, duration)
                    print(f"[FORMATION] {uri} moving to ({x}, {y}, {z})")
                except Exception as e:
                    print(f"[ERROR] Formation command failed for {uri}: {e}")
            # Wait for this transition to complete before moving to the next one
            time.sleep(duration)

    def flat_square(self):
        print("[FORMATION] Issuing Flat Square formation")
        new_formation = self.formations.get_formation_positions("flat_square")
        self.send_formation(new_formation)
    def circle(self):
        print("[FORMATION] Circle command issued")
        new_formation = self.formations.get_formation_positions("circle")
        self.send_formation(new_formation)
    def tilted_plane(self):
        print("[FORMATION] Tilted Plane command issued")
        new_formation = self.formations.get_formation_positions("tilted_plane")
        self.send_formation(new_formation)
    ## ---------------------------
    # MAIN UPDATE LOOP
    ## ---------------------------
    def run(self):
        """Starts the swarm update loop in a separate thread."""
        self.running = True
        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()
        print("[INFO] Swarm update loop started")

    def _update_loop(self):
        # Periodic data update
        last_connection_check = time.time()
        connection_check_interval = reconnect_attempt_interval  # seconds
        while self.running:
            # For all drones, perform manager checks
            for uri in self.uris:
                state = self.get_drone_state(uri)
                if state != "disconnected": # If connected, monitor connection state
                    current_time = time.time()
                    if current_time - self._last_state_update_time[uri] > factor_connection_lost * low_frequency_update_interval:
                        with self.lock:
                            self.state_cache[uri] = "disconnected"
                            self.scfs[uri] = None
                            self.formations.disconnect_from_formation(uri)
                            self.battery_cache[uri] = default_battery_voltage
                    if state == "flying" and self.battery_cache[uri] < low_battery_in_flight and self.formations.states[uri] == "in_formation":
                        print(f"[WARNING] Low battery detected during flight for {uri}. Initiating landing.")
                        self.land_one(uri, self.scfs[uri], duration=landing_duration)
                else: # Disconnected drone, attempt reconnection periodically
                    if time.time() - last_connection_check > connection_check_interval:
                        self.connect_one(uri)
                        last_connection_check = time.time()
            time.sleep(swarm_loop_interval)  # avoid busy-waiting