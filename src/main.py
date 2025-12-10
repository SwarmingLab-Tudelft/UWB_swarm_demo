from gui import ControlTowerGUI
from drone_commands import CrazyflieSwarm

import cflib.crtp
cflib.crtp.init_drivers(enable_debug_driver=False)

from config import uris, absolute_boundaries, drone_spacing

if __name__ == "__main__":
    swarm = CrazyflieSwarm(uris)
    app = ControlTowerGUI(swarm)
    swarm.connect_all()
    swarm.run()
    app.run()
