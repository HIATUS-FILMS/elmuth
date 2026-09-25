# Sorry for the messy code without comments, I'm adding this a little bit later (config.py is a nightmare rn)

import config
import databases
import control
import ffplayout
from bcolors import bcolors

config.config_soft()
databases.init_db()
control.webserver()
