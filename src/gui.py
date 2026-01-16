from tkinter import Label, HORIZONTAL
import tkinter
import tkinter.ttk as ttk
import threading

class Crazyflie_report(ttk.Frame):
    def __init__(self, parent, uri, swarm, ident=None):
        ttk.Frame.__init__(self, parent)

        # space among elements
        self['padding'] = 10

        self.uri = uri
        self.swarm = swarm
        num = uri[-2:]

        self._name = Label(self, text="Crazyflie #{}".format(num))
        self._name.grid(row=0, column=0)

        # show uri below name
        self._uri_label = Label(self, text=uri, fg='grey', font=("ubuntu", 9))
        self._uri_label.grid(row=1, column=0)

        self._status = Label(self, text="idle", fg='grey', font=("ubuntu", 33), width=13)
        self._status.grid(row=2, column=0)

        self._battery_label = Label(self, text="Battery:")
        self._battery_label.grid(row=3, column=0)

        self._battery_frame = ttk.Frame(self)
        self._battery_frame.grid(row=4, column=0, sticky="ew")
        self._battery_frame.columnconfigure(1, weight=2)

        self._battery_voltage = ttk.Label(self._battery_frame, text="3.0V", padding=(0,0,10,0))
        self._battery_voltage.grid(row=0, column=0)
        
        self._battery_bar = ttk.Progressbar(self._battery_frame, orient=HORIZONTAL)
        self._battery_bar['value'] = 50
        self._battery_bar.grid(row=0, column=1, sticky="ew")

        # Individual drone control buttons
        self._buttons_frame = ttk.Frame(self)
        self._buttons_frame.grid(row=5, column=0, sticky="ew", pady=(5, 0))
        self._buttons_frame.columnconfigure(0, weight=1)
        self._buttons_frame.columnconfigure(1, weight=1)

        self._takeoff_btn = tkinter.Button(self._buttons_frame, text="Takeoff One", bg="#90EE90", fg="black",
                                          command=self._on_takeoff)
        self._takeoff_btn.grid(row=0, column=0, sticky="ew", padx=(0, 2))

        self._land_btn = tkinter.Button(self._buttons_frame, text="Land One", bg="#87CEEB", fg="black",
                                       command=self._on_land)
        self._land_btn.grid(row=0, column=1, sticky="ew", padx=(2, 0))

    def _on_takeoff(self):
        """Callback for individual takeoff button"""
        scf = self.swarm.scfs.get(self.uri)
        if scf is not None:
            import threading
            threading.Thread(target=self.swarm.takeoff_one, args=(self.uri, scf, 0.8, 1.0)).start()

    def _on_land(self):
        """Callback for individual land button"""
        scf = self.swarm.scfs.get(self.uri)
        if scf is not None:
            import threading
            threading.Thread(target=self.swarm.land_one, args=(self.uri, scf, 3.0)).start()

    
    def set_state(self, state):
        if state == "idle":
            self._status.config(text="IDLE", fg="grey")
        elif state == "connecting":
            self._status.config(text="Connecting", fg="orange")
        elif state == "connected":
            self._status.config(text="Connected", fg="blue")
        elif state == "disconnected":
            self._status.config(text="Disconnected", fg="grey")
        elif state == "crashed":
            self._status.config(text="Crashed", fg="red")
        elif state == "charging":
            self._status.config(text="Charging", fg="purple")
        elif state == "flying":
            self._status.config(text="Flying", fg="green")
        elif state == "landing":
            self._status.config(text="Landing", fg="green")
        else:
            self._status.config(text="ERROR", fg="purple")
            print("Error, state", state, "not handled")

    def set_battery(self, voltage):
        if voltage is None:
            voltage = 3.0
        self._battery_voltage['text'] = "{:.2f}V".format(voltage)

        percent = (voltage - 3.0)*100.0/1.1

        self._battery_bar['value'] = percent
    
    def set_uptime(self, ms):
        seconds = int(ms/1000) % 60
        minutes = int((ms/1000)/60) % 60
        hours = int((ms/1000)/3600)
        self._up_time_label['text'] = "{}:{:02}:{:02}".format(hours, minutes, seconds)
        if ms == 0:
            self._up_time_label['fg'] = "grey"
        else:
            self._up_time_label['fg'] = "black"
    
    def set_flighttime(self, ms):
        seconds = int(ms/1000) % 60
        minutes = int((ms/1000)/60) % 60
        hours = int((ms/1000)/3600)
        self._flight_time_label['text'] = "{}:{:02}:{:02}".format(hours, minutes, seconds)
        if ms == 0:
            self._flight_time_label['fg'] = "grey"
        else:
            self._flight_time_label['fg'] = "black"
        pass


class ControlTowerGUI:
    def __init__(self, swarm):
        self.swarm = swarm
        self.uris = list(swarm.uris)
        self.root = tkinter.Tk()
        self.root.title("Control Tower")

        # Main container frame
        self.content = ttk.Frame(self.root)
        self.content.grid(column=0, row=0, sticky="nsew")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.cfs = dict()
        self._create_cf_grid()
        self._create_controls()
        self._configure_close_action()

        self.update_gui_loop()

    # ------------------------------------------------------
    # GUI creation methods
    # ------------------------------------------------------
    def _create_cf_grid(self):
        """Create grid of drone widgets based on provided URIs (3 columns)."""
        for i, uri in enumerate(self.uris):
            r = i // 3
            c = i % 3

            cf_widget = Crazyflie_report(self.content, uri, self.swarm, i)
            cf_widget.grid(column=c, row=r)
            self.cfs[uri] = cf_widget

            # default values
            cf_widget.set_state("disconnected")
            cf_widget.set_battery(3.0)

        # make grid expandable for up to 3 columns
        for col in range(3):
            self.content.columnconfigure(col, weight=1)

    def _create_controls(self):
        """Create the bottom control panel inline (three buttons)."""
        rows_used = ((len(self.uris) - 1) // 3) + 1 if self.uris else 1

        # Ensure the content has three columns configured
        for col in range(3):
            self.content.columnconfigure(col, weight=1)

        btn_width = 25
        padx = 6
        pady = 10

        btn_takeoff = tkinter.Button(self.content, text="Take off", bg="green", fg="white",
                                     command=self.swarm.takeoff, width=btn_width)
        btn_takeoff.grid(column=0, row=rows_used, sticky="ew", padx=padx, pady=pady)
        btn_land = tkinter.Button(self.content, text="Land", bg="blue", fg="white",
                                  command=self.swarm.land, width=btn_width)
        btn_land.grid(column=1, row=rows_used, sticky="ew", padx=padx, pady=pady)
        btn_emergency = tkinter.Button(self.content, text="Emergency land", bg="red", fg="white",
                                       command=self.swarm.emergency_land, width=btn_width)
        btn_emergency.grid(column=2, row=rows_used, sticky="ew", padx=padx, pady=pady)
        ## Formations buttons
        btn_flat_square = tkinter.Button(self.content, text="Flat Square", bg="orange", fg="white",
                                       command=self.swarm.flat_square, width=btn_width)
        btn_flat_square.grid(column=0, row=rows_used+1, sticky="ew", padx=padx, pady=pady)
        btn_circle = tkinter.Button(self.content, text="Circle", bg="orange", fg="white",
                                       command=self.swarm.circle, width=btn_width)  
        btn_circle.grid(column=1, row=rows_used+1, sticky="ew", padx=padx, pady=pady)
        btn_tilted_plane = tkinter.Button(self.content, text="Tilted Plane", bg="orange", fg="white",
                                       command=self.swarm.tilted_plane, width=btn_width)
        btn_tilted_plane.grid(column=2, row=rows_used+1, sticky="ew", padx=padx, pady=pady)

        btn_moving_circle = tkinter.Button(self.content, text="Moving Circle", bg="purple", fg="white",
                           command=self.swarm.moving_circle, width=btn_width)
        btn_moving_circle.grid(column=0, row=rows_used+2, sticky="ew", padx=padx, pady=pady)
        btn_sin_wave = tkinter.Button(self.content, text="Sine Wave", bg="purple", fg="white",
                           command=self.swarm.sin_wave, width=btn_width)
        btn_sin_wave.grid(column=1, row=rows_used+2, sticky="ew", padx=padx, pady=pady)

    ## Safe shutdown on window close
    def _configure_close_action(self):
        """Ensure safe shutdown of threads, drones, etc."""
        def fail_safe():
           
            # After GUI destroyed, stop swarm background threads but keep links open
            try:
                self.swarm.stop_background(timeout=5.0)
            except Exception:
                pass
            # Add motor kill or landing
            try:
                self.swarm.force_stop_flying()
            except Exception:
                pass
            # Close links and clean up remaining resources
            try:
                self.swarm.close_links()
            except Exception:
                pass
            try:
                # destroy the Tk root (ends mainloop). After this call the GUI is gone.
                self.root.destroy()
            except Exception:
                pass
        self.root.protocol("WM_DELETE_WINDOW", fail_safe)

    # ------------------------------------------------------
    # Public methods
    # ------------------------------------------------------
    # More work needed to update the loop correctly
    def update_gui_loop(self):
        for uri, cf_widget in self.cfs.items():
            # If we are succesfully connected to the drone
            if self.swarm.scfs.get(uri, False):
                cf_widget.set_state(self.swarm.get_drone_state(uri))
                cf_widget.set_battery(self.swarm.get_drone_battery(uri))
            else:
                # If not connected, try to connect every 10 seconds
                cf_widget.set_state("disconnected")

        self.root.after(200, self.update_gui_loop)

    def run(self):
        self.root.mainloop()