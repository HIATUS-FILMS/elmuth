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
            medianame TEXT UNIQUE,
            filepath TEXT NOT NULL,
            type TEXT,
            fam TEXT,
            season TEXT,
            length TEXT,
            description TEXT,
            storage TEXT,
            firstaired TEXT,
            lastaired TEXT,
            present INTEGER DEFAULT 1
            )
    ''')
    connect.commit()
    connect.close()
    migrate_db()

def migrate_db():
    connect = connect_db()
    cols = {r["name"] for r in connect.execute("PRAGMA table_info(media)")}
    if "duration" not in cols:
        connect.execute("ALTER TABLE media ADD COLUMN duration REAL")
    connect.commit()
    connect.close()

def write_db(name, path, length, duration):
    try:
        with connect_db() as authdb:
            authdb.execute(
                """INSERT INTO media (filename, filepath, length, duration) VALUES (?, ?, ?, ?)
                   ON CONFLICT(filename) DO UPDATE SET
                       filepath = excluded.filepath,
                       length = excluded.length,
                       duration = excluded.duration""",
                (name, path, length, float(duration)))
    except Exception as e:
        print(f"An error occured while writing the media:{e}")

def get_data(source_path):
    headers = ffheaders()
    headers['Content-Type'] = 'application/json'
    
    url = readaddress() + '/api/file/' + readid() + '/browse'
    
    payload = {
        "source": source_path,
        "folders_only": False
    }
    
    data = requests.post(url, headers=headers, data=json.dumps(payload))
    
    if data.status_code == 200:
        return data.json()
    else:
        print(bcolors.FAIL + datetime.datetime.now().strftime("%H:%M:%S") + f" [ERROR] API error {data.status_code} for the path {source_path}" + bcolors.ENDC)
        return {}

def media_agent(path_current=""):
    call_api = get_data(path_current)

    files = call_api.get("files", [])
    folders = call_api.get("folders", [])

    for file in files:
        name = file.get("name")

        if name.endswith((".mp4", ".mkv", ".avi")):
            print(bcolors.OKBLUE + datetime.datetime.now().strftime("%H:%M:%S") + f" [INFO] The file {name} has been found in {path_current}" + bcolors.ENDC)

            duration_sec = file.get("duration", 0)

            total_seconds = int(duration_sec)
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            if hours > 0:
                length_formatted = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                length_formatted = f"{minutes:02d}:{seconds:02d}"

            write_db(name, path_current, length_formatted, duration_sec)

        else:
            print(bcolors.FAIL + datetime.datetime.now().strftime("%H:%M:%S") + f" [INFO] The file {name} is not compatible (Wrong file extension)" + bcolors.ENDC)

    for folder in folders:
        if path_current:
            path_new = f"{path_current}/{folder}"
        
        else:
            path_new = folder

        print(bcolors.OKGREEN + datetime.datetime.now().strftime("%H:%M:%S") + f" [INFO] Scanning {path_new}" + bcolors.ENDC)

        media_agent(path_new)