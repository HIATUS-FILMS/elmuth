# This will send and recieve informations via the ffplayout API

from flask import Flask, render_template, request, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
from bcolors import bcolors
import os
import datetime
import sqlite3
import json
import requests
import time

cached_token = None
token_expiration_time = None

def readaddress():
    with open('settings/config.json', 'r', encoding='utf-8') as config_scan:
        config_read = json.load(config_scan)

        ffaddress_path = config_read["ffplayout"]["base_url"]
    return ffaddress_path

def readkey():
    with open('settings/config.json', 'r', encoding='utf-8') as config_scan:
        config_read = json.load(config_scan)

        private_key = config_read["ffplayout"]["private_key"]
    return private_key

def readid():
    with open('settings/config.json', 'r', encoding='utf-8') as config_scan:
        config_read = json.load(config_scan)

        channel_id = config_read["ffplayout"]["channel_id"]
    return channel_id

def read_db():

    with open('settings/config.json', 'r', encoding='utf-8') as db_scan:
        db_read = json.load(db_scan)

    auth_path = db_read["db"]["auth_path"]
    authdb = sqlite3.connect(auth_path)
    with authdb:
        cursor_auth = authdb.cursor()
        cursor_auth.execute("SELECT username, password FROM el_ffplayout LIMIT 1")

    result = cursor_auth.fetchone()
    authdb.close()
    return result

def pass_decrypt():
    cipher_suite = Fernet(readkey().encode('utf-8'))
    plain_text = cipher_suite.decrypt(read_db()[1])
    return plain_text.decode('utf-8')

def ffplayout_token():
    client_id = read_db()[0]
    client_secret = pass_decrypt()
    token_url = readaddress() + '/auth/login' #Returns tokens (Access) + (Refresh)
    verify_url = readaddress() + '/auth/verify' #Returns access and refresh tokens. Verification codes expire after five minutes
    refresh_url = readaddress() + '/auth/refresh' #Rotates it and returns a new token pairs

def get_new_access_token():
    global cached_token, token_expiration_time
    

    client_id = read_db()[0]
    client_secret = pass_decrypt()
    token_url = readaddress() + '/auth/login'

    body = {
        'username': client_id,
        'password': client_secret
    }

    response = requests.post(token_url, json=body)

    if response.status_code != 200:
        raise Exception(f'Failed auth to ffplayout : {response.text}')

    data = response.json()


    cached_token = data['access']

    token_expiration_time = time.time() + (45 * 60 - 60)  

    return cached_token

def get_access_token():
    global cached_token, token_expiration_time
    if cached_token and time.time() < token_expiration_time:
        return cached_token
    return get_new_access_token()

def getinfo_current_media():

    headers = {
        'Authorization': f'Bearer {get_access_token()}',
        'Content-Type': 'application/json',
        }

    url = readaddress() + '/api/control/' + readid() + '/media/current'
    getinfo = requests.get(url, headers=headers)
    print(getinfo.status_code)
    if getinfo.status_code == 200:
        return getinfo.json()