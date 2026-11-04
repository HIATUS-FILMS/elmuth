# Playlist templates manager

import os
import requests
import datetime
import json
import sqlite3
from bcolors import bcolors
from flask import render_template, request, jsonify, session, Response, redirect, Blueprint
from ffplayout import readaddress, readid, ffheaders
import flask_login
from media import connect_db
from markupsafe import escape

#defining the templates values

default_templates = {
    "example": {
        "name": "Example template",
        "color": "bg-rose-500",
        "description": "This is an example template",
        "preferred_days": ["Mo", "Tu", "We", "Th", "Fr"],
        "first_aired": "N/A",
        "last_aired": "N/A",
        "blocks": [
            {
            "description": "This is an example block",
            "family": "N/A",
            "type": "N/A",
            "time_start": "00:00:00",
            "time_end": "06:00:00",
            "options": {
                "shuffle": True,
                "prefer_recent": True,
                "hard_cut": False,
                "loop": False,
                "fillers": True,
                "strict_order": False
            }
            }
        ]
    }
}

def templates_soft(): #function to verify if templates.json exists, and generates it if not

    os.makedirs('programs', exist_ok=True) #verify if the programs folder exists
    file_path = 'programs/templates.json' #defines the templates.json path
    file_missing = not os.path.exists(file_path) #defines if the file is missing
    file_empty = not file_missing and os.path.getsize(file_path) == 0 #defines if the file ils empty

    if file_missing or file_empty : #if the file is missing or empty
        print(bcolors.FAIL + datetime.datetime.now().strftime("%H:%M:%S") + " [ERROR] The templates file does not exist" + bcolors.ENDC)
        print(bcolors.WARNING + datetime.datetime.now().strftime("%H:%M:%S") + " [WARN] Creating the templates file..." + bcolors.ENDC)

        templates_json = json.dumps(default_templates, indent=4)#we write previous parameters in "templates_json"

        print(templates_json) #just displaying the result

        with open('programs/templates.json', 'w', encoding='utf-8') as fichier: #opening templates.json and writing in it
            json.dump(default_templates, fichier, indent=4, ensure_ascii=False)

        print(bcolors.OKGREEN + datetime.datetime.now().strftime("%H:%M:%S") + " [INFO] The templates was successfully created" + bcolors.ENDC)

        with open('programs/templates.json', 'r', encoding='utf-8') as templates_load: #loading the templates file
            templates_loaded = json.load(templates_load)

        print(bcolors.OKGREEN + datetime.datetime.now().strftime("%H:%M:%S") + " [INFO] The templates was successfully loaded" + bcolors.ENDC)
        print(" ")
        print(templates_loaded)
    
    with open(file_path, "r", encoding='utf-8') as templates_load:
        templates_loaded = json.load(templates_load)

    print(bcolors.OKGREEN + datetime.datetime.now().strftime("%H:%M:%S") + " [INFO] The templates was successfully loaded" + bcolors.ENDC)
    print(" ")
    print(templates_loaded)

    return templates_loaded

def template_create_new():
    file_path = 'programs/templates.json'
    templates = templates_soft()
    
    default_name = "new_template"
    new_key = default_name
    counter = 1
    while new_key in templates:
        new_key = f"{default_name}_{counter}"
        counter += 1
        
    templates[new_key] = {
        "name": f"New Template {counter}",
        "color": "bg-violet-800",
        "description": "Description of the new template",
        "preferred_days": [],
        "first_aired": "N/A",
        "last_aired": "N/A",
        "blocks": []
    }
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(templates, f, indent=4, ensure_ascii=False)
        
    return templates

def template_save_data(form_data, template_key):
    file_path = 'programs/templates.json'
    templates = templates_soft()
    
    if template_key in templates:
        templates[template_key]["name"] = form_data.get("name", templates[template_key]["name"])
        templates[template_key]["description"] = form_data.get("description", "")
        templates[template_key]["preferred_days"] = form_data.getlist("days")
        templates[template_key]["first_aired"] = form_data.get("first") or "N/A"
        templates[template_key]["last_aired"] = form_data.get("last") or "N/A"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(templates, f, indent=4, ensure_ascii=False)
            
    return templates

def template_delete(template_key):
    file_path = 'programs/templates.json'
    templates = templates_soft()
    
    if template_key in templates:
        del templates[template_key]
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(templates, f, indent=4, ensure_ascii=False)
            
    return templates

def template_add_block(template_key, form_data):
    file_path = 'programs/templates.json'
    templates = templates_soft()
    
    if template_key in templates:
        criteria_type = form_data.get("criteria_type", "family")
        criteria_value = form_data.get("criteria_value", "N/A")
        
        family = criteria_value if criteria_type == "family" else "N/A"
        b_type = criteria_value if criteria_type == "type" else "N/A"
        
        new_block = {
            "description": form_data.get("block-description", ""),
            "family": family,
            "type": b_type,
            "time_start": form_data.get("start", "00:00:00"),
            "time_end": form_data.get("end", "00:00:00"),
            "color": form_data.get("color", "bg-rose-500"),
            "intro_media": form_data.get("intro_media", ""),
            "outro_media": form_data.get("outro_media", ""),
            "options": {
                "playback_mode": form_data.get("playback_mode", "shuffle"),
                "recent_policy": form_data.get("recent_policy", "exclude_recent"),
                "transition_mode": form_data.get("transition_mode", "hard"),
                "loop": 'loop' in form_data
            }
        }
        
        templates[template_key]["blocks"].append(new_block)
        templates[template_key]["blocks"].sort(key=lambda x: x.get("time_start", "00:00:00"))
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(templates, f, indent=4, ensure_ascii=False)
            
    return templates

def template_delete_block(template_key, block_index):
    file_path = 'programs/templates.json'
    templates = templates_soft()
    
    if template_key in templates:
        blocks = templates[template_key].get("blocks", [])
        if 0 <= block_index < len(blocks):
            blocks.pop(block_index)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(templates, f, indent=4, ensure_ascii=False)
                
    return templates

def get_media_list_by_family(fam_name):
    medias = []
    try:
        with sqlite3.connect("databases/medias.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT filename FROM media WHERE fam = ?", (fam_name,))
            medias = [row["filename"] for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error reading media database for family {fam_name}: {e}")
    return medias