# This manages the config.json file

import json
import os
import datetime
from bcolors import bcolors #used for console messages color

def config_soft(): #function to verify if config.json exists, and generates it if not

    os.makedirs('settings', exist_ok=True) #verify if the settings folder exists
    file_path = 'settings/config.json' #defines the config.json path

    if os.path.exists(file_path): #config.json exists
        config_size = os.path.getsize('settings/config.json') #so we verify if it's not empty
        if config_size == 0: #config.json is empty, but less empty than me coding that
            print(bcolors.FAIL + datetime.datetime.now().strftime("%H:%M:%S") + "  [ERROR] The configuration file does not exist" + bcolors.ENDC)
            print(bcolors.WARNING + datetime.datetime.now().strftime("%H:%M:%S") + " [WARN] Creating the configuration file..." + bcolors.ENDC)
            config = {
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
        } #we define in json format what will be present in the config file
            config_json = json.dumps(config, indent=4) #we write previous parameters in "config_json"

            print(config_json) #just displaying the result

            with open('settings/config.json', 'w', encoding='utf-8') as fichier: #opening config.json and writing in it
                json.dump(config, fichier, indent=4, ensure_ascii=False)

            print(bcolors.OKGREEN + datetime.datetime.now().strftime("%H:%M:%S") + datetime.datetime.now().strftime("%H:%M:%S") + "  [INFO] The configuration was successfully created" + bcolors.ENDC)

            with open('settings/config.json', 'r', encoding='utf-8') as config_load: #loading the config file
                config_loaded = json.load(config_load)

            print(bcolors.OKGREEN + datetime.datetime.now().strftime("%H:%M:%S") + " [INFO] The configuration was successfully loaded" + bcolors.ENDC)
            print(" ")
            print(config_loaded)
        else:
            with open('settings/config.json', 'r', encoding='utf-8') as config_load: #config.json is not empty, so loading the config file
                config_loaded = json.load(config_load)

            print(bcolors.OKGREEN + datetime.datetime.now().strftime("%H:%M:%S") + " [INFO] The configuration was successfully loaded" + bcolors.ENDC)
            print(" ")
            print(config_loaded)
            
    else: #config file does not exists
        print(bcolors.FAIL + datetime.datetime.now().strftime("%H:%M:%S") + " [ERROR] The configuration file does not exist" + bcolors.ENDC)
        print(bcolors.WARNING + datetime.datetime.now().strftime("%H:%M:%S") + " [WARN] Creating the configuration file..." + bcolors.ENDC)
        config = {
            "server": {
                "port": "8080",
            },
            "ffplayout": {
                "base_url": "http://192.168.1.X:8787", # Change this with your server IP too
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
        } #we define in json format what will be present in the config file
        config_json = json.dumps(config, indent=4)#we write previous parameters in "config_json"

        print(config_json) #just displaying the result

        with open('settings/config.json', 'w', encoding='utf-8') as fichier: #opening config.json and writing in it
            json.dump(config, fichier, indent=4, ensure_ascii=False)

        print(bcolors.OKGREEN + datetime.datetime.now().strftime("%H:%M:%S") + " [INFO] The configuration was successfully created" + bcolors.ENDC)

        with open('settings/config.json', 'r', encoding='utf-8') as config_load: #loading the config file
            config_loaded = json.load(config_load)

        print(bcolors.OKGREEN + datetime.datetime.now().strftime("%H:%M:%S") + " [INFO] The configuration was successfully loaded" + bcolors.ENDC)
        print(" ")
        print(config_loaded)

#this could be optimized later I guess
