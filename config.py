# This manages the config.json file

import json
import os
import datetime
from bcolors import bcolors #used for console messages color

#defining the default config values

default_config = {
    "server": {
        "port": "8080",
    },
    "ffplayout": {
        "base_url": "http://192.168.1.X:8787", # Change this with your server IP
        "channel_id": "1",
        "overlay_id": "3",
        "private_key" : "GENERATED_WHEN_SETUP",
    },
    "media": {
        "assets_dir": "/var/lib/ffplayout/tv-media/00-assets",
    },
    "db": {
        "auth_path": "databases/auth.db",
    },
}

def config_soft(): #function to verify if config.json exists, and generates it if not

    os.makedirs('settings', exist_ok=True) #verify if the settings folder exists
    file_path = 'settings/config.json' #defines the config.json path
    file_missing = not os.path.exists(file_path) #defines if the file is missing
    file_empty = not file_missing and os.path.getsize(file_path) == 0 #defines if the file ils empty

    if file_missing or file_empty : #if the file is missing or empty
        print(bcolors.FAIL + datetime.datetime.now().strftime("%H:%M:%S") + " [ERROR] The configuration file does not exist" + bcolors.ENDC)
        print(bcolors.WARNING + datetime.datetime.now().strftime("%H:%M:%S") + " [WARN] Creating the configuration file..." + bcolors.ENDC)

        config_json = json.dumps(default_config, indent=4)#we write previous parameters in "config_json"

        print(config_json) #just displaying the result

        with open('settings/config.json', 'w', encoding='utf-8') as fichier: #opening config.json and writing in it
            json.dump(default_config, fichier, indent=4, ensure_ascii=False)

        print(bcolors.OKGREEN + datetime.datetime.now().strftime("%H:%M:%S") + " [INFO] The configuration was successfully created" + bcolors.ENDC)

        with open('settings/config.json', 'r', encoding='utf-8') as config_load: #loading the config file
            config_loaded = json.load(config_load)

        print(bcolors.OKGREEN + datetime.datetime.now().strftime("%H:%M:%S") + " [INFO] The configuration was successfully loaded" + bcolors.ENDC)
        print(" ")
        print(config_loaded)
    
    with open(file_path, "r", encoding='utf-8') as config_load:
        config_loaded = json.load(config_load)

    print(bcolors.OKGREEN + datetime.datetime.now().strftime("%H:%M:%S") + " [INFO] The configuration was successfully loaded" + bcolors.ENDC)
    print(" ")
    print(config_loaded)

    return config_loaded
