# This manages the config.json file

import json
import os
import datetime
from bcolors import bcolors

def config_soft():

    os.makedirs('settings', exist_ok=True)
    file_path = 'settings/config.json'

    if os.path.exists(file_path):
        config_size = os.path.getsize('settings/config.json')
        if config_size == 0:
            print(bcolors.FAIL + datetime.datetime.now().strftime("%H:%M:%S") + datetime.datetime.now().strftime("%H:%M:%S") + "  [ERROR] The configuration file does not exist" + bcolors.ENDC)
            print(bcolors.WARNING + datetime.datetime.now().strftime("%H:%M:%S") + datetime.datetime.now().strftime("%H:%M:%S") + " [WARN] Creating the configuration file..." + bcolors.ENDC)
            config = {
                "server": {
                    "port": "8080",
                },
                "ffplayout": {
                    "base_url": "http://192.168.1.X:8787", # Change this with your server IP
                    "channel_id": "1",
                    "overlay_id": "3",
                },
                "media": {
                    "assets_dir": "/var/lib/ffplayout/tv-media/00-assets",
                },
                "db": {
                    "auth_path": "databases/auth.db",
                },
        }
            config_json = json.dumps(config, indent=4)

            print(config_json)

            with open('settings/config.json', 'w', encoding='utf-8') as fichier:
                json.dump(config, fichier, indent=4, ensure_ascii=False)

            print(bcolors.OKGREEN + datetime.datetime.now().strftime("%H:%M:%S") + datetime.datetime.now().strftime("%H:%M:%S") + "  [INFO] The configuration was successfully created" + bcolors.ENDC)

            with open('settings/config.json', 'r', encoding='utf-8') as config_load:
                config_loaded = json.load(config_load)

            print(bcolors.OKGREEN + datetime.datetime.now().strftime("%H:%M:%S") + " [INFO] The configuration was successfully loaded" + bcolors.ENDC)
            print(" ")
            print(config_loaded)
        else:
            with open('settings/config.json', 'r', encoding='utf-8') as config_load:
                config_loaded = json.load(config_load)

            print(bcolors.OKGREEN + datetime.datetime.now().strftime("%H:%M:%S") + " [INFO] The configuration was successfully loaded" + bcolors.ENDC)
            print(" ")
            print(config_loaded)
            
    else:
        print(bcolors.FAIL + datetime.datetime.now().strftime("%H:%M:%S") + " [ERROR] The configuration file does not exist" + bcolors.ENDC)
        print(bcolors.WARNING + datetime.datetime.now().strftime("%H:%M:%S") + " [WARN] Creating the configuration file..." + bcolors.ENDC)
        config = {
            "server": {
                "port": "8080",
                "username": "CHANGE_ME",
                "password": "CHANGE_ME",
            },
            "ffplayout": {
                "base_url": "http://192.168.1.X:8787", # Change this with your server IP too
                "channel_id": "1",
                "ffusername": "CHANGE_ME",
                "ffpassword": "CHANGE_ME",
                "overlay_id": "3",
            },
            "media": {
                "assets_dir": "/var/lib/ffplayout/tv-media/00-assets",
            },
            "db": {
                "auth_path": "databases/auth.db",
            },
        }
        config_json = json.dumps(config, indent=4)

        print(config_json)

        with open('settings/config.json', 'w', encoding='utf-8') as fichier:
            json.dump(config, fichier, indent=4, ensure_ascii=False)

        print(bcolors.OKGREEN + datetime.datetime.now().strftime("%H:%M:%S") + " [INFO] The configuration was successfully created" + bcolors.ENDC)

        with open('settings/config.json', 'r', encoding='utf-8') as config_load:
            config_loaded = json.load(config_load)

        print(bcolors.OKGREEN + datetime.datetime.now().strftime("%H:%M:%S") + " [INFO] The configuration was successfully loaded" + bcolors.ENDC)
        print(" ")
        print(config_loaded)
