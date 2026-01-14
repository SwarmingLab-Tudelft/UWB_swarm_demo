from logging import info
import threading
import time

from formations import FormationManager

from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.log import LogConfig

data_update_interval = 1.0  # seconds

class CrazyflieSwarm:
    '''Handles connections and commands to a swarm of crazyflies. Reads information from logs'''
    def __init__(self, uris):
        self.uris = uris
        self.scfs = {}     # {uri: SyncCrazyflie}
        self.threads = {}  # {uri: Thread}
        ## When modifying a dict, a lock is needed. It works like a mutex
        self.lock = threading.Lock()
        self.running = False
        ## Drone information, polled in the update loop with certain frequency
        self.battery_cache = {uri: 3.3 for uri in uris}
        # options are: idle, connecting, connected, disconnected, flying, hovering, landing, and error
        self.state_cache = {uri: "disconnected" for uri in uris}
        self._last_state_update_time = {uri: time.time() for uri in uris}
        ## Logging
        self._log_configs = {}
        ## Formation parameters
        self.formations = FormationManager(uris)
        self.formation_positions = None


    # ---------------------------
    # CONNECT ALL DRONES
    # ---------------------------
    def _setup_logging(self, uri, scf):
        """Create Crazyflie log block."""
        cf = scf.cf

        log = LogConfig(name=f'bat_{uri}', period_in_ms=data_update_interval*1000)
        log.add_variable('pm.vbat', 'float') # Voltage
        log.add_variable('supervisor.info', 'uint16_t') # State

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
                return 3.0
            with self.lock:
                self.battery_cache[uri] = voltage
        def _callback(ts, data, logconf):
            _supervisor_cb(data)
            _battery_cb(data)           

        try:
            cf.log.add_config(log)
            log.data_received_cb.add_callback(_callback)
            log.start()
            self._log_configs[uri] = log
            print(f"[OK] Battery logging started for {uri}")
        except Exception as e:
            print(f"[ERROR] Failed to start logging for {uri}: {e}")

    def connect_one(self, uri):
        try:
            scf = SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache'))
            scf.open_link()

            with self.lock:
                self.scfs[uri] = scf

            # Formation manager
            self.formations.connect_to_formation(uri)

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
            self.threads[uri] = t

        # Wait for all connections
        for t in self.threads.values():
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
        # Placeholder for actual state retrieval logic
        return self.state_cache.get(uri, "disconnected")
    
    def get_drone_battery(self, uri):
        # Placeholder for actual battery retrieval logic
        return self.battery_cache.get(uri, 3.0)

    # ---------------------------
    # TAKE OFF
    # ---------------------------
    def takeoff_one(self, uri, scf, height, duration):
        try:
            if self.get_drone_battery(uri) < 3.7:
                print(f"[WARNING] Battery too low for takeoff: {uri}")
                self.formations.disconnect_from_formation(uri)
                return
            hlc = scf.cf.high_level_commander
            hlc.takeoff(height, duration)
            print(f"[TAKEOFF] {uri}")
        except Exception as e:
            print(f"[ERROR] Takeoff failed for {uri}: {e}")

    def takeoff(self, height=0.8, duration=3.0):
        for uri, scf in self.scfs.items():
            if scf is None:
                continue
            threading.Thread(target=self.takeoff_one, args=(uri, scf, height, duration)).start()

    # ---------------------------
    # LAND
    # ---------------------------
    # If it's already landed, dont do that again
    def land_one(self, uri, scf, duration):
        try:
            if self.get_drone_state(uri) == "flying":
                hlc = scf.cf.high_level_commander
                hlc.land(0.0, duration)
                self.formations.disconnect_from_formation(uri)
                print(f"[LAND] {uri}")
        except Exception as e:
            print(f"[ERROR] Land failed for {uri}: {e}")

    def land(self, duration=3.0):
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
    def stop_background(self, timeout=2.0):
        """Stop update loop, stop and remove any active LogConfig callbacks and join threads.
        This will stop logging callbacks from running.
        I did not write this code, but it works.
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
        for uri, t in list(self.threads.items()):
            try:
                if t is not None and t.is_alive():
                    t.join(timeout if timeout is not None else 0.1)
            except Exception:
                pass

        print("[INFO] Swarm background stopped and logging disabled")

    ## ---------------------------
    # FORMATION COMMANDS
    ## ---------------------------
    def send_formation(self, positions, duration=4.0):
        """Sends position commands to all drones to move to the specified positions over the given duration."""
        if self.formation_positions is not None:
            # Check for potential collisions
            if self.formations.positions_intersect(self.formation_positions, positions, threshold=0.3):
                transition_positions = self.formations.get_transition_positions(self.formation_positions, positions)
            else:
                transition_positions = [positions]
        else:
            transition_positions = [positions]
        for transition_pos in transition_positions:
            for uri, scf in self.scfs.items():
                if scf is None or uri not in transition_pos:
                    continue
                x, y, z = transition_pos[uri]
                try:
                    hlc = scf.cf.high_level_commander
                    hlc.go_to(x, y, z, 0.0, duration)
                    print(f"[FORMATION] {uri} moving to ({x}, {y}, {z})")
                except Exception as e:
                    print(f"[ERROR] Formation command failed for {uri}: {e}")
            # Wait for this transition to complete before moving to the next one
            time.sleep(duration)
        self.formation_positions = positions

    def flat_square(self):
        print("[FORMATION] Issuing Flat Square formation")
        positions = self.formations.get_formation_positions("flat_square")
        self.send_formation(positions)
    def circle(self):
        print("[FORMATION] Circle command issued")
        positions = self.formations.get_formation_positions("circle")
        self.send_formation(positions)
    def tilted_plane(self):
        print("[FORMATION] Tilted Plane command issued")
        positions = self.formations.get_formation_positions("tilted_plane")
        self.send_formation(positions)
    ## ---------------------------
    # MAIN UPDATE LOOP
    ## ---------------------------
    def run(self, update_hz=50):
        """Starts the swarm update loop in a separate thread."""
        self.running = True
        self.thread = threading.Thread(target=self._update_loop, args=(update_hz,), daemon=True)
        self.thread.start()
        print("[INFO] Swarm update loop started")

    def _update_loop(self, update_hz=50):
        # Periodic data update
        last_connection_check = time.time()
        connection_check_interval = 5.0  # seconds
        while self.running:
            # For all drones, perform manager checks
            for uri in self.uris:
                state = self.get_drone_state(uri)
                if state != "disconnected": # If connected, monitor connection state
                    current_time = time.time()
                    if current_time - self._last_state_update_time[uri] > 3 * data_update_interval:
                        with self.lock:
                            self.state_cache[uri] = "disconnected"
                            self.scfs[uri] = None
                            self.formations.disconnect_from_formation(uri)
                            self.battery_cache[uri] = 3.0 
                    if state == "flying" and self.battery_cache[uri] < 3.3 and self.formations.states[uri] == "in_formation":
                        self.land_one(uri, self.scfs[uri], duration=3.0)
                else: # Disconnected drone, attempt reconnection periodically
                    if time.time() - last_connection_check > connection_check_interval:
                        self.connect_one(uri)
                        last_connection_check = time.time()
            time.sleep(0.1)  # avoid busy-waiting