# This is the media asset manager part of elmuth

import sqlite3
import os
import datetime
import json
import requests
from bcolors import bcolors
from ffplayout import get_access_token, get_new_access_token, ffplayout_token, pass_decrypt, readid, readaddress, ffheaders



db = "databases/medias.db"

def connect_db():
    connect = sqlite3.connect(db)
    connect.row_factory = sqlite3.Row
    print(bcolors.OKGREEN + datetime.datetime.now().strftime("%H:%M:%S") + " [INFO] The media database was successfully loaded" + bcolors.ENDC)
    return connect

def init_db():
    os.makedirs(os.path.dirname(db), exist_ok=True)
    connect = connect_db()
    connect.execute('''
        CREATE TABLE IF NOT EXISTS media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE NOT NULL,
            filepath TEXT NOT NULL,
            type TEXT,
            fam TEXT,
            season TEXT,
            length TEXT,
            description TEXT,
            storage TEXT,
            present INTEGER DEFAULT 1
            )
    ''')
    connect.commit()
    connect.close()

def write_db(name, path):

    try:
        with connect_db() as authdb:
            cursor_auth = authdb.cursor()
            cursor_auth.execute(("INSERT OR IGNORE INTO media (filename, filepath) values (?, ?)"), (name, path))
            authdb.commit()
    except Exception as e:
        print(f"An error occured while creating the table:{e}")


def media_agent():

    headers = ffheaders()

    url = readaddress() + '/api/file/' + readid() + '/browse'
    getinfo = requests.post(url, headers=headers)
    print(getinfo.status_code)



    if getinfo.status_code == 200:

        data = getinfo.json()

        files = data.get("files", [])

        for file in files:
            name = file.get("name")
            path = file.get("path")
            print(bcolors.OKBLUE + datetime.datetime.now().strftime("%H:%M:%S") + f" [INFO] The file {name} has been found in {path}" + bcolors.ENDC)
            write_db(name, path)
        return getinfo.json()
