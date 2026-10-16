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

def readconfig():
    with open('settings/config.json', 'r', encoding='utf-8') as config_scan:
        return json.load(config_scan)

def readaddress():
    return readconfig()["ffplayout"]["base_url"]

def readkey():
    return readconfig()["ffplayout"]["private_key"]

def readid():
    return readconfig()["ffplayout"]["channel_id"]

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

def ffheaders():
    return {
        'Authorization': f'Bearer {get_access_token()}',
        'Content-Type': 'application/json',
    }

def getinfo_current_media():

    headers = ffheaders()

    url = readaddress() + '/api/control/' + readid() + '/media/current'
    getinfo = requests.get(url, headers=headers)
    print(getinfo.status_code)
    if getinfo.status_code == 200:
        return getinfo.json()

def getinfo_current_playlist():

    headers = ffheaders()

    today = datetime.date.today().strftime('%Y-%m-%d')
    url = readaddress() + '/api/playlist/' + readid() + '?date=' + today
    getinfo = requests.get(url, headers=headers)
    print(getinfo.status_code)
    if getinfo.status_code == 200:
        return getinfo.json()

def sendinfo_overlay():

    headers = ffheaders()

    url = readaddress() + '/api/control/' + readid() + '/text'
    sendinfo = requests.post(url, headers=headers)
    print(sendinfo.status_code)
    if sendinfo.status_code == 200:
        return sendinfo.json()

def sendinfo_prev():

    headers = ffheaders()

    url = readaddress() + '/api/control/' + readid() + '/playout'
    data = {
        "control":"back"
    }
    sendinfo = requests.post(url, headers=headers, json=data)
    print(sendinfo.status_code)
    if sendinfo.status_code == 200:
        return sendinfo.json()

def sendinfo_play():

    headers = ffheaders()

    url = readaddress() + '/api/control/' + readid() + '/process'
    data = {
        "command":"start"
    }
    sendinfo = requests.post(url, headers=headers, json=data)
    print(sendinfo.status_code)
    if sendinfo.status_code == 200:
        return sendinfo.json()

def sendinfo_stop():

    headers = ffheaders()

    url = readaddress() + '/api/control/' + readid() + '/process'
    data = {
        "command":"stop"
    }
    sendinfo = requests.post(url, headers=headers, json=data)
    print(sendinfo.status_code)
    if sendinfo.status_code == 200:
        return sendinfo.json()

def sendinfo_next():

    headers = ffheaders()

    url = readaddress() + '/api/control/' + readid() + '/playout'
    data = {
        "control":"next"
    }
    sendinfo = requests.post(url, headers=headers, json=data)
    print(sendinfo.status_code)
    if sendinfo.status_code == 200:
        return sendinfo.json()