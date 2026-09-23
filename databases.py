# This manages elmuth databases

import sqlite3
import os
import datetime
import json
from bcolors import bcolors

def init_db():

    with open('settings/config.json', 'r', encoding='utf-8') as db_scan:
        db_read = json.load(db_scan)

    os.makedirs('databases', exist_ok=True)
    auth_path = db_read["db"]["auth_path"]
    authdb = sqlite3.connect(auth_path)
    print(bcolors.OKGREEN + datetime.datetime.now().strftime("%H:%M:%S") + " [INFO] The database was successfully loaded" + bcolors.ENDC)

    try:
        with authdb:
            cursor_auth = authdb.cursor()
            sql = '''CREATE TABLE IF NOT EXISTS el_ffplayout (
                        username TEXT,
                        password TEXT
            );'''
            cursor_auth.execute(sql)
            authdb.commit()
    except Exception as e:
        print(f"An error occured while creating the table:{e}")

    try:
        with authdb:
            cursor_auth = authdb.cursor()
            sql = '''CREATE TABLE IF NOT EXISTS el_credentials (
                        id_client INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT,
                        password TEXT
            );'''
            cursor_auth.execute(sql)
            authdb.commit()
    except Exception as e:
        print(f"An error occured while creating the table:{e}")
    authdb.close()