# This is the settings manager of elmuth, it reads and writes the config of elmuth and a part of the config of ffplayout

import copy
import datetime
import json
import os
import re
import sqlite3
import time

import flask_login
import requests
from cryptography.fernet import Fernet
from flask import redirect, render_template, request, session

import engine
import ffplayout
from bcolors import bcolors
from config import default_config
from ffplayout import ffheaders, readaddress, readid, readkey

CONFIG_PATH = "settings/config.json"
BACKUP_PATH = "settings/ffplayout_config_backup.json"  # the config of ffplayout as it was before elmuth changed it, it contains secrets like the stream keys


def settings_log(color, level, message):  # prints a message like the rest of elmuth
    print(color + datetime.datetime.now().strftime("%H:%M:%S") + f" [{level}] " + message + bcolors.ENDC)


def merge_defaults(defaults, loaded):  # adds the missing keys of a config file, without touching what is already set
    merged = copy.deepcopy(defaults)
    for key, value in loaded.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_defaults(merged[key], value)
        else:
            merged[key] = value
    return merged


def config_load():  # loads config.json with every default value, even the ones that were added after its creation
    with open(CONFIG_PATH, "r", encoding="utf-8") as config_file:
        config_loaded = json.load(config_file)

    config_defaults = copy.deepcopy(default_config)
    config_defaults["ffplayout"]["day_start"] = ""  # local copy of the day start of ffplayout
    config_defaults["engine"] = {**engine.default_config, **default_config.get("engine", {})}
    return merge_defaults(config_defaults, config_loaded)


def config_write(config_data):  # writes config.json without ever leaving a half written file
    temp_path = CONFIG_PATH + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as temp_file:
        json.dump(config_data, temp_file, indent=4, ensure_ascii=False)

    for attempt in range(5):  # on windows, the file can be open for a few milliseconds
        try:
            os.replace(temp_path, CONFIG_PATH)
            return
        except PermissionError:
            time.sleep(0.1)
    os.replace(temp_path, CONFIG_PATH)


def normalize_time(time_text):  # returns HH:MM:SS, an empty text if it is empty, or None if it is not a time
    time_text = (time_text or "").strip()
    if time_text == "":
        return ""
    time_match = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$", time_text)
    if not time_match:
        return None
    hours = int(time_match.group(1))
    minutes = int(time_match.group(2))
    seconds = int(time_match.group(3) or 0)
    if hours > 23 or minutes > 59 or seconds > 59:
        return None
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def to_number(number_text, minimum=0):  # returns the number of a text, or None if it is not a number or is too small
    try:
        number = float(str(number_text).strip().replace(",", "."))
    except ValueError:
        return None
    if number < minimum:
        return None
    return number


def settings_validate(form):  # checks the form, returns the errors and the clean values
    errors = []
    cleaned = {}

    server_port = form.get("server_port", "").strip()
    if not server_port.isdigit() or not 1 <= int(server_port) <= 65535:
        errors.append("Elmuth port must be a number between 1 and 65535")
    cleaned["server_port"] = server_port

    ff_base_url = form.get("ff_base_url", "").strip().rstrip("/")
    if not re.match(r"^https?://[^\s/]+(/\S*)?$", ff_base_url):
        errors.append("Server address must start with http:// or https://")
    cleaned["ff_base_url"] = ff_base_url

    ff_user = form.get("ff_user", "").strip()
    if ff_user == "":
        errors.append("Ffplayout user can't be empty")
    cleaned["ff_user"] = ff_user
    cleaned["ff_password"] = form.get("ff_password", "")  # empty means unchanged

    ff_channel_id = form.get("ff_channel_id", "").strip()
    if not ff_channel_id.isdigit() or int(ff_channel_id) < 1:
        errors.append("Channel ID must be a number")
    cleaned["ff_channel_id"] = ff_channel_id

    ff_day_start = normalize_time(form.get("ff_day_start", ""))
    if ff_day_start is None:
        errors.append("Day start must be a time like 00:00:00")
        ff_day_start = ""
    cleaned["ff_day_start"] = ff_day_start

    ff_overlay_preset = form.get("ff_overlay_preset", "").strip()
    if ff_overlay_preset != "" and not ff_overlay_preset.isdigit():
        errors.append("Overlay preset is not valid")
        ff_overlay_preset = ""
    cleaned["ff_overlay_preset"] = int(ff_overlay_preset) if ff_overlay_preset != "" else None

    engine_values = {}
    for engine_key in ["filler_type", "jingle_type"]:
        engine_text = form.get(f"engine_{engine_key}", "").strip()
        if engine_text == "":
            errors.append(f"Engine {engine_key.replace('_', ' ')} can't be empty")
        engine_values[engine_key] = engine_text

    stretch_families = [family.strip() for family in form.get("engine_stretch_families", "").split(",") if family.strip()]
    engine_values["stretch_families"] = stretch_families

    recent_days = to_number(form.get("engine_recent_days", ""))
    if recent_days is None:
        errors.append("Recent media must be a number of days")
    engine_values["recent_days"] = int(recent_days) if recent_days is not None else None

    for engine_key, engine_label in [("hold", "Logo hold"), ("gap_target", "Wanted gap"), ("gap_max", "Longest gap")]:
        engine_number = to_number(form.get(f"engine_{engine_key}", ""))
        if engine_number is None:
            errors.append(f"{engine_label} must be a number of seconds")
        engine_values[engine_key] = engine_number
    if engine_values["gap_target"] is not None and engine_values["gap_max"] is not None and engine_values["gap_max"] < engine_values["gap_target"]:
        errors.append("Longest gap can't be shorter than the wanted gap")
    cleaned["engine"] = engine_values

    return errors, cleaned


def ffplayout_user():  # the user of ffplayout, it is stored in the database and not in config.json
    try:
        user_row = ffplayout.read_db()
        return user_row[0] if user_row else ""
    except Exception as e:
        settings_log(bcolors.FAIL, "ERROR", f"Error reading the ffplayout user : {e}")
        return ""


def ffplayout_read():  # reads the config, the channel and the presets of ffplayout, returns the data and an error text
    try:
        headers = ffheaders()
        base = readaddress() + "/api"
        config_response = requests.get(f"{base}/playout/config/{readid()}", headers=headers, timeout=10)
        channel_response = requests.get(f"{base}/channel/{readid()}", headers=headers, timeout=10)
        presets_response = requests.get(f"{base}/presets/{readid()}", headers=headers, timeout=10)
    except Exception as e:
        settings_log(bcolors.FAIL, "ERROR", f"ffplayout can't be reached : {e}")
        return None, f"ffplayout can't be reached ({e})"

    for response, name in [(config_response, "config"), (channel_response, "channel"), (presets_response, "presets")]:
        if response.status_code != 200:
            settings_log(bcolors.FAIL, "ERROR", f"ffplayout refused to give its {name} : {response.status_code}")
            return None, f"ffplayout refused to give its {name} (error {response.status_code})"

    try:
        return {"config": config_response.json(), "channel": channel_response.json(), "presets": presets_response.json()}, ""
    except ValueError:
        return None, "ffplayout gave an answer that elmuth can't read"


def settings_build(config, ffplayout_data):  # builds the values shown in the page
    settings = {
        "server_port": config["server"]["port"],
        "ff_base_url": config["ffplayout"]["base_url"],
        "ff_user": ffplayout_user(),
        "ff_channel_id": config["ffplayout"]["channel_id"],
        "ff_day_start": config["ffplayout"].get("day_start", ""),
        "ff_overlay_preset": None,
        "ff_storage": "",
        "presets": [],
        "engine_filler_type": config["engine"]["filler_type"],
        "engine_jingle_type": config["engine"]["jingle_type"],
        "engine_stretch_families": ", ".join(config["engine"]["stretch_families"]),
        "engine_recent_days": config["engine"]["recent_days"],
        "engine_hold": config["engine"]["hold"],
        "engine_gap_target": config["engine"]["gap_target"],
        "engine_gap_max": config["engine"]["gap_max"],
    }

    if ffplayout_data:  # the values of ffplayout are the ones that count
        day_start = ffplayout_data["config"].get("playlist", {}).get("day_start") or ""
        settings["ff_day_start"] = normalize_time(day_start) or ""  # something that is not a time, like "now", is shown empty
        settings["ff_overlay_preset"] = ffplayout_data["config"].get("text", {}).get("preset_id")
        settings["ff_storage"] = ffplayout_data["channel"].get("storage", "")
        settings["presets"] = ffplayout_data["presets"]
    return settings


def credentials_update(auth_path, ff_user, ff_password, private_key):  # updates the ffplayout user and password in the database
    authdb = sqlite3.connect(auth_path)
    try:
        with authdb:
            if ff_password:  # an empty password means unchanged
                password_encrypted = Fernet(private_key.encode("utf-8")).encrypt(ff_password.encode("utf-8"))
                update = authdb.execute("UPDATE el_ffplayout SET username = ?, password = ?", (ff_user, password_encrypted))
                if update.rowcount == 0:  # nothing was stored yet
                    authdb.execute("INSERT INTO el_ffplayout (username, password) VALUES (?, ?)", (ff_user, password_encrypted))
            else:
                authdb.execute("UPDATE el_ffplayout SET username = ?", (ff_user,))
    finally:
        authdb.close()


def forget_ffplayout_token():  # elmuth has to login again after a change of address, user or password
    ffplayout.cached_token = None
    ffplayout.token_expiration_time = None
    ffplayout.login_blocked_until = 0


def ffplayout_write(playout_config, changes):  # sends the complete config of ffplayout, with only the changed values different
    new_config = copy.deepcopy(playout_config)
    if "day_start" in changes:
        new_config.setdefault("playlist", {})["day_start"] = changes["day_start"]
    if "preset_id" in changes:
        new_config.setdefault("text", {})["preset_id"] = changes["preset_id"]

    with open(BACKUP_PATH, "w", encoding="utf-8") as backup_file:  # a copy of what ffplayout had, in case something goes wrong
        json.dump(playout_config, backup_file, indent=4, ensure_ascii=False)

    try:
        response = requests.put(f"{readaddress()}/api/playout/config/{readid()}", headers=ffheaders(), json=new_config, timeout=15)
    except Exception as e:
        settings_log(bcolors.FAIL, "ERROR", f"Error while sending the config to ffplayout : {e}")
        return False, f"ffplayout can't be reached ({e})", False

    if response.status_code == 200:
        try:
            requires_restart = bool(response.json().get("requires_restart"))
        except (ValueError, AttributeError):
            requires_restart = False
        return True, "", requires_restart

    settings_log(bcolors.FAIL, "ERROR", f"ffplayout refused the config : {response.status_code} {response.text}")
    if response.status_code == 403:
        return False, "your ffplayout user is not allowed to change the config of ffplayout", False
    return False, f"ffplayout refused the change (error {response.status_code})", False


def settings_register(app):
    @app.route("/settings", methods=["GET"])
    @flask_login.login_required
    def settings_page():
        config = config_load()
        ffplayout_data, ffplayout_error = ffplayout_read()

        messages = session.pop("settings_messages", [])
        if ffplayout_error:
            messages.append({"type": "error", "text": f"{ffplayout_error}. The settings of ffplayout can't be shown or saved."})

        return render_template("settings.html", settings=settings_build(config, ffplayout_data), messages=messages)

    @app.route("/settings/save", methods=["POST"])
    @flask_login.login_required
    def settings_save():
        config = config_load()
        errors, cleaned = settings_validate(request.form)

        if errors:  # nothing is saved, and the page is shown again with what was typed
            ffplayout_data, ffplayout_error = ffplayout_read()
            settings = settings_build(config, ffplayout_data)
            for form_key in request.form:
                if form_key in settings and form_key not in ("ff_overlay_preset", "presets"):
                    settings[form_key] = request.form[form_key]
            messages = [{"type": "error", "text": error} for error in errors]
            return render_template("settings.html", settings=settings, messages=messages)

        messages = []
        current_user = ffplayout_user()
        link_changed = (
            cleaned["ff_base_url"] != config["ffplayout"]["base_url"]
            or cleaned["ff_channel_id"] != str(config["ffplayout"]["channel_id"])
            or cleaned["ff_user"] != current_user
            or cleaned["ff_password"] != ""
        )

        # the config of elmuth
        new_config = copy.deepcopy(config)
        port_changed = cleaned["server_port"] != str(config["server"]["port"])
        new_config["server"]["port"] = cleaned["server_port"]
        new_config["ffplayout"]["base_url"] = cleaned["ff_base_url"]
        new_config["ffplayout"]["channel_id"] = cleaned["ff_channel_id"]
        new_config["engine"].update(cleaned["engine"])
        config_write(new_config)
        messages.append({"type": "success", "text": "Elmuth settings saved"})
        if port_changed:
            messages.append({"type": "warning", "text": "The new port is used after a restart of elmuth"})

        # the user and the password of ffplayout
        if cleaned["ff_user"] != current_user or cleaned["ff_password"] != "":
            try:
                credentials_update(new_config["db"]["auth_path"], cleaned["ff_user"], cleaned["ff_password"], readkey())
                messages.append({"type": "success", "text": "Ffplayout user and password saved"})
            except Exception as e:
                settings_log(bcolors.FAIL, "ERROR", f"Error while saving the ffplayout user : {e}")
                messages.append({"type": "error", "text": "The ffplayout user could not be saved, see the console"})
        if link_changed:
            forget_ffplayout_token()

        # the settings that are stored in ffplayout
        ffplayout_data, ffplayout_error = ffplayout_read()
        if ffplayout_error:
            messages.append({"type": "error", "text": f"{ffplayout_error}. The settings of ffplayout were not saved."})
        else:
            playout_config = ffplayout_data["config"]
            current_day_start = normalize_time(playout_config.get("playlist", {}).get("day_start") or "") or ""  # "now" counts as empty
            current_preset = playout_config.get("text", {}).get("preset_id")
            preset_ids = [preset.get("id") for preset in ffplayout_data["presets"]]

            changes = {}
            if cleaned["ff_day_start"] != current_day_start:
                changes["day_start"] = cleaned["ff_day_start"]
            if cleaned["ff_overlay_preset"] != current_preset:
                if cleaned["ff_overlay_preset"] is not None and cleaned["ff_overlay_preset"] not in preset_ids:
                    messages.append({"type": "error", "text": "This overlay preset does not exist in ffplayout"})
                else:
                    changes["preset_id"] = cleaned["ff_overlay_preset"]

            effective_day_start = current_day_start
            if changes:
                saved, error_text, requires_restart = ffplayout_write(playout_config, changes)
                if saved:
                    messages.append({"type": "success", "text": "Ffplayout settings saved"})
                    if requires_restart:
                        messages.append({"type": "warning", "text": "Ffplayout has to be restarted to use them. A restart interrupts the broadcast, do it when you can"})
                    effective_day_start = changes.get("day_start", current_day_start)
                else:
                    messages.append({"type": "error", "text": f"Ffplayout settings were not saved : {error_text}"})

            if effective_day_start not in ("", "00:00:00"):
                messages.append({"type": "warning", "text": "The playlist engine only plans blocks correctly when the day starts at 00:00:00"})

            if new_config["ffplayout"].get("day_start", "") != effective_day_start:  # keeps the local copy, used for the airing times
                new_config["ffplayout"]["day_start"] = effective_day_start
                config_write(new_config)

        session["settings_messages"] = messages
        return redirect("/settings")
