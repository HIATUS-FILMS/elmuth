# This manages elmuth databases

import sqlite3
import os
import datetime
import json
from bcolors import bcolors
from config import config_soft

def init_db():

    config = config_soft()

    os.makedirs('databases', exist_ok=True)
    auth_path = config["db"]["auth_path"]
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

def db_connect():
    config = config_soft()
    auth_path = config["db"]["auth_path"]
    os.makedirs(os.path.dirname(auth_path), exist_ok=True)
    conn = sqlite3.connect(auth_path)
    conn.row_factory = sqlite3.Row
    return conn