# This is the scheduler of elmuth, letting you create playlists with your medias

import requests
import datetime
import json
from bcolors import bcolors
from flask import render_template, request, jsonify, session, Response
from ffplayout import readaddress, readid, ffheaders
import flask_login
from media import connect_db
from markupsafe import escape

STORAGE_ROOT = "/var/lib/ffplayout/tv-media"

def get_media_row(filename):
    connect = connect_db()
    row = connect.execute(
        "SELECT filepath, length FROM media WHERE filename = ?", (filename,)
    ).fetchone()
    connect.close()
    return row

def length_to_seconds(text):
    seconds = 0
    for part in text.split(":"):
        seconds = seconds * 60 + int(part)
    return seconds

def format_duration(item):
    total_seconds = int(item.get("duration", 0))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if hours > 0:
        item["formatted_duration"] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        item["formatted_duration"] = f"{minutes:02d}:{seconds:02d}"

def fetch_api_items(date):
    try:
        response = requests.get(f"{readaddress()}/api/playlist/{readid()}?date={date}", headers=ffheaders())
        if response.status_code == 200:
            return response.json().get("program", [])
    except Exception as e:
        print(bcolors.FAIL + datetime.datetime.now().strftime("%H:%M:%S") + f" [ERROR] Error retrieving the playlist for {date} : {e}" + bcolors.ENDC)
    return []

def get_deleted(date):
    data = session.get('draft_deleted', {})
    if data.get("date") == date:
        return data.get("indices", [])
    return []

def prepare_items(api_items, date):
    deleted = get_deleted(date)
    items = []
    for i, item in enumerate(api_items):
        item["pending_delete"] = (i in deleted)
        items.append(item)
    items = items + session.get('draft_playlist', [])
    for item in items:
        format_duration(item)
    return items

def playlist_register(app):

    @app.route('/playout/playlist_load', methods=['GET'])
    @flask_login.login_required
    def playlist_load():
        select_date = request.args.get('playlist_date', datetime.date.today().strftime('%Y-%m-%d'))
        playlist_items = prepare_items(fetch_api_items(select_date), select_date)

        if request.headers.get('HX-Request'):
            return render_template('modules/playlist_table.html', playlist=playlist_items, select_date=select_date)

        return render_template('playout.html', playlist=playlist_items, select_date=select_date)

    @app.route('/playout/playlist_edit', methods=['POST'])
    @flask_login.login_required
    def playlist_edit():
        fetch = request.get_json()

        if not fetch:
            return jsonify({"status": "error", "message": "No data fetched"}), 400

        selected_date = fetch.get("date")
        new_items = fetch.get("items", [])

        headers = ffheaders()
        url = f"{readaddress()}/api/playlist/{readid()}?date={selected_date}"

        try:
            
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                return jsonify({"status": "error", "message": "Could not fetch playlist from ffplayout"}), 500

            data = response.json()
            api_items = data.get("program", [])
            
            
            items_dict = {item["source"]: item for item in api_items}

            
            reordered_program = []
            for item in new_items:
                source = item.get("source")
                if source in items_dict:
                    reordered_program.append(items_dict[source])

            data["program"] = reordered_program

            
            session.pop('draft_playlist', None)
            session.modified = True

            
            url_post = f"{readaddress()}/api/playlist/{readid()}"
            save_response = requests.post(url_post, headers=headers, json=data)
            
            if save_response.status_code in [200, 201]:
                print(bcolors.OKGREEN + datetime.datetime.now().strftime("%H:%M:%S") + f" [SUCCESS] Playlist reordered for {selected_date}" + bcolors.ENDC)
                return jsonify({"status": "success", "message": "Order updated"}), 200
            else:
                print(bcolors.FAIL + f"FFPLAYOUT DEBUG: {save_response.text}" + bcolors.ENDC)
                return jsonify({"status": "error", "message": "Failed to update ffplayout"}), 500

        except Exception as e:
            print(bcolors.FAIL + datetime.datetime.now().strftime("%H:%M:%S") + f" [ERROR] Error editing the playlist for {selected_date} : {e}" + bcolors.ENDC)
            return jsonify({"status": "error", "message": str(e)}), 500


    @app.route('/playout/playlist_draft_add', methods=['POST'])
    @flask_login.login_required
    def playlist_draft_add():
        media_source = request.args.get("source")
        if not media_source:
            return "", 400

        if 'draft_playlist' not in session:
            session['draft_playlist'] = []

        row = get_media_row(media_source)
        if row is None:
            return "", 404

        duration = length_to_seconds(row["length"] or "00:00")
        folder = row["filepath"]
        full_path = f"{STORAGE_ROOT}/{folder}/{media_source}" if folder else f"{STORAGE_ROOT}/{media_source}"

        session['draft_playlist'].append({
            "source": full_path,
            "title": media_source,
            "in": 0,
            "out": duration,
            "duration": duration
        })
        session.modified = True

        selected_date = request.form.get("playlist_date") or request.args.get("date") or datetime.date.today().strftime('%Y-%m-%d')

        return render_template('modules/playlist_table.html',
                       playlist=prepare_items(fetch_api_items(selected_date), selected_date),
                       select_date=selected_date)

    @app.route('/playout/playlist_save_all', methods=['POST'])
    @flask_login.login_required
    def playlist_save_all():
        selected_date = request.form.get("playlist_date") or request.args.get("date")
        if not selected_date:
            return jsonify({"error": "Missing date"}), 400

        headers = ffheaders()
        url_get = f"{readaddress()}/api/playlist/{readid()}?date={selected_date}"

        try:
            response = requests.get(url_get, headers=headers)
            playlist_data = response.json() if response.status_code == 200 else {"date": selected_date, "program": []}

            if "program" not in playlist_data:
                playlist_data["program"] = []

            deleted = get_deleted(selected_date)
            kept = [item for i, item in enumerate(playlist_data["program"]) if i not in deleted]
            playlist_data["program"] = kept + session.get('draft_playlist', [])

            url_post = f"{readaddress()}/api/playlist/{readid()}"
            save_response = requests.post(url_post, headers=headers, json=playlist_data)

            if save_response.status_code in [200, 201]:
                session.pop('draft_playlist', None)
                session.pop('draft_deleted', None)
                print(bcolors.OKGREEN + datetime.datetime.now().strftime("%H:%M:%S") + f" [SUCCESS] Playlist saved for {selected_date}" + bcolors.ENDC)
                return "", 204
            else:
                return jsonify({"error": "Failed to save"}), 500

        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/playout/inspect', methods=['GET'])
    @flask_login.login_required
    def playout_inspect():
        name = request.args.get("name", "")
        inspect_name = escape(name)
        return inspect_name

    @app.route('/playout/playlist_draft_delete', methods=['POST'])
    @flask_login.login_required
    def playlist_draft_delete():
        print("DEBUG delete form :", dict(request.form))
        
        selected_date = request.form.get("playlist_date")
        selected = request.form.get("selected", "")
        
        #checking if we detele a playlist item properly
        if not selected.startswith("playlist:"):
            return "", 204

        #split the string to get index number
        split_select = selected.split(":")
        index = int(split_select[1])

        #fetching items from ffplayout api first
        api_items = []
        headers = ffheaders()
        url = f"{readaddress()}/api/playlist/{readid()}?date={selected_date}"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            api_items = response.json().get("program", [])

        #get session drafts
        drafts = session.get('draft_playlist', [])

        #if index is bigger than api items length,it is in the session draft
        if index >= len(api_items):
            draft_index = index - len(api_items)
            if 0 <= draft_index < len(drafts):
                drafts.pop(draft_index)
                session['draft_playlist'] = drafts
                session.modified = True
        else:
            #else, it is in the real api playlist, and we remove it there
            api_items.pop(index)
            playlist_data = {
                "date": selected_date,
                "program": api_items
            }
            url_post = f"{readaddress()}/api/playlist/{readid()}"
            requests.post(url_post, headers=headers, json=playlist_data)

        #mergeing everything
        full_items = api_items + session.get('draft_playlist', [])
        
        #recalculata durations like everywhere else
        for item in full_items:
            if "duration" in item:
                total_seconds = int(item["duration"])
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                if hours > 0:
                    item["formatted_duration"] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                else:
                    item["formatted_duration"] = f"{minutes:02d}:{seconds:02d}"
            
        return render_template('modules/playlist_table.html', playlist=full_items, select_date=selected_date)

    @app.route('/playout/playlist_clear', methods=['POST'])
    @flask_login.login_required
    def playlist_clear():
        selected_date = request.form.get("playlist_date") or request.args.get("date")
        if not selected_date:
            return jsonify({"error": "Missing date"}), 400

        api_items = fetch_api_items(selected_date)

        session.pop('draft_playlist', None)
        session['draft_deleted'] = {"date": selected_date, "indices": list(range(len(api_items)))}
        session.modified = True

        return render_template('modules/playlist_table.html',
                            playlist=prepare_items(api_items, selected_date),
                            select_date=selected_date)

    @app.route('/playout/playlist_download', methods=['GET'])
    @flask_login.login_required
    def playlist_download():
        selected_date = request.args.get('playlist_date', datetime.date.today().strftime('%Y-%m-%d'))
        
        headers = ffheaders()
        url = f"{readaddress()}/api/playlist/{readid()}?date={selected_date}"

        try:
            response = requests.get(url, headers=headers)
            playlist_data = response.json() if response.status_code == 200 else {"date": selected_date, "program": []}


            drafts = session.get('draft_playlist', [])
            if "program" in playlist_data:
                playlist_data["program"].extend(drafts)
            else:
                playlist_data["program"] = drafts

            json_str = json.dumps(playlist_data, indent=4, ensure_ascii=False)

            return Response(
                json_str,
                mimetype="application/json",
                headers={"Content-Disposition": f"attachment;filename=playlist_{selected_date}.json"}
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500