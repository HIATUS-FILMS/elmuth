# This is the scheduler of elmuth, letting you create playlists with your medias

import datetime
import json

import flask_login
import requests
from flask import Response, jsonify, redirect, render_template, request, session

from bcolors import bcolors
from ffplayout import ffheaders, getinfo_current_media, readaddress, readconfig, readid
from media import connect_db

STORAGE_ROOT = "/var/lib/ffplayout/tv-media"


def get_media_row(filename):
    connect = connect_db()
    row = connect.execute(
        "SELECT filepath, length, duration FROM media WHERE filename = ?", (filename,)
    ).fetchone()
    connect.close()
    return row


def length_to_seconds(text):
    seconds = 0
    for part in text.split(":"):
        seconds = seconds * 60 + int(part)
    return seconds


def format_duration(item):
    total_seconds = int(round(get_item_length(item)))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if hours > 0:
        item["formatted_duration"] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        item["formatted_duration"] = f"{minutes:02d}:{seconds:02d}"


def fetch_api_items(date):
    try:
        response = requests.get(
            f"{readaddress()}/api/playlist/{readid()}?date={date}", headers=ffheaders()
        )
        if response.status_code == 200:
            return response.json().get("program", [])
    except Exception as e:
        print(
            bcolors.FAIL
            + datetime.datetime.now().strftime("%H:%M:%S")
            + f" [ERROR] Error retrieving the playlist for {date} : {e}"
            + bcolors.ENDC
        )
    return []


def get_deleted(date):
    data = session.get("draft_deleted", {})
    if data.get("date") == date:
        return data.get("indices", [])
    return []


def add_media_info(items):

    connect = connect_db()
    for item in items:
        filename = item["source"].split("/")[-1]
        row = connect.execute(
            "SELECT type, fam, description FROM media WHERE filename = ?", (filename,)
        ).fetchone()
        if row:
            item["type"] = row["type"]
            item["fam"] = row["fam"]
            item["description"] = row["description"]
    connect.close()


def get_day_start_seconds():  # gets the start of the playlist from the config, ffplayout starts its playlists at day_start
    try:
        day_start = readconfig().get("ffplayout", {}).get("day_start", "00:00:00")
        hours, minutes, seconds = [float(part) for part in day_start.split(":")]
        return hours * 3600 + minutes * 60 + seconds
    except Exception as e:
        print(
            bcolors.FAIL
            + datetime.datetime.now().strftime("%H:%M:%S")
            + f" [ERROR] Error reading day_start : {e}"
            + bcolors.ENDC
        )
        return 0


def get_item_length(
    item,
):  # real airing length of an item, a cut or stretched item is not as long as its file
    if "out" in item:
        return float(item["out"]) - float(item.get("in", 0))
    return float(item.get("duration", 0))


def get_playing_seconds():  # where "now" is on the clock of the playlist, which starts at day_start
    now = datetime.datetime.now()
    seconds_now = now.hour * 3600 + now.minute * 60 + now.second
    if (
        seconds_now < get_day_start_seconds()
    ):  # after midnight, but still in the playlist of yesterday
        seconds_now += 86400
    return seconds_now


def get_playing_date():  # date of the playlist that is on air
    now = datetime.datetime.now()
    seconds_now = now.hour * 3600 + now.minute * 60 + now.second
    if seconds_now < get_day_start_seconds():
        return (now.date() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    return now.date().strftime("%Y-%m-%d")


def find_current_index(
    items, current_media, planned_starts
):  # finds which item of the playlist is on air
    index = current_media.get("index")
    if isinstance(index, int) and 0 <= index < len(
        items
    ):  # ffplayout gives the position
        return index

    source = current_media.get("media", {}).get("source")
    same_source = [
        position
        for position, item in enumerate(items)
        if item.get("source") == source and not item.get("pending_delete")
    ]
    if not same_source:
        return None
    # a repeated media (a logo for example) can be anywhere, so the closest to the planned time wins
    return min(
        same_source,
        key=lambda position: abs(planned_starts[position] - get_playing_seconds()),
    )


def get_planned_starts(
    items,
):  # planned start of every item, from the start of the playlist
    planned_clock = get_day_start_seconds()
    planned_starts = []
    for item in items:
        planned_starts.append(planned_clock)
        if not item.get("pending_delete"):  # an item about to be deleted takes no time
            planned_clock += get_item_length(item)
    return planned_starts


def add_airing_times(items, date):  # estimates the airing time of every item
    planned_clock = get_day_start_seconds()
    planned_starts = []
    for item in items:  # planned times, from the start of the playlist
        planned_starts.append(planned_clock)
        if not item.get("pending_delete"):
            planned_clock += get_item_length(item)
    start_times = list(planned_starts)

    if (
        date == get_playing_date()
    ):  # the playlist is on air, so the estimate starts from what is playing now
        try:
            current_media = getinfo_current_media()
            current_index = (
                find_current_index(items, current_media, planned_starts)
                if current_media
                else None
            )
            if current_index is not None and "elapsed" in current_media:
                elapsed = float(current_media["elapsed"])
                start_times[current_index] = get_playing_seconds() - elapsed
                clock = get_playing_seconds() + max(
                    get_item_length(items[current_index]) - elapsed, 0
                )
                for position in range(
                    current_index + 1, len(items)
                ):  # what comes after follows the real time
                    start_times[position] = clock
                    if not items[position].get("pending_delete"):
                        clock += get_item_length(items[position])
        except Exception as e:
            print(
                bcolors.FAIL
                + datetime.datetime.now().strftime("%H:%M:%S")
                + f" [ERROR] Error reading the current media : {e}"
                + bcolors.ENDC
            )

    for position, item in enumerate(items):
        if item.get(
            "pending_delete"
        ):  # the item is about to be deleted, so it takes no time
            item["start_time"] = "--:--:--"
            continue
        total_seconds = (
            int(start_times[position]) % 86400
        )  # after midnight, the clock starts again
        item["start_time"] = (
            f"{total_seconds // 3600:02d}:{(total_seconds % 3600) // 60:02d}:{total_seconds % 60:02d}"
        )


def get_distinct_values(column):
    connect = connect_db()
    rows = connect.execute(
        f"SELECT DISTINCT {column} FROM media WHERE {column} IS NOT NULL AND {column} != '' ORDER BY {column}"
    ).fetchall()
    connect.close()
    return [row[0] for row in rows]


def prepare_items(api_items, date):
    deleted = get_deleted(date)
    items = []
    for i, item in enumerate(api_items):
        item["pending_delete"] = i in deleted
        items.append(item)
    items = items + session.get("draft_playlist", [])
    add_airing_times(items, date)
    add_media_info(items)
    for item in items:
        format_duration(item)
    return items


def playlist_register(app):

    @app.route("/playout/playlist_load", methods=["GET"])
    @flask_login.login_required
    def playlist_load():
        select_date = request.args.get(
            "playlist_date", datetime.date.today().strftime("%Y-%m-%d")
        )
        playlist_items = prepare_items(fetch_api_items(select_date), select_date)

        if request.headers.get("HX-Request"):
            return render_template(
                "modules/playout_editor.html",
                playlist=playlist_items,
                selected_date=select_date,
            )

        return redirect(f"/playout?playlist_date={select_date}")

    @app.route("/playout/playlist_edit", methods=["POST"])
    @flask_login.login_required
    def playlist_edit():
        fetch = request.get_json()

        if not fetch:
            return jsonify({"status": "error", "message": "No data fetched"}), 400

        selected_date = fetch.get("date")
        new_order = fetch.get("order", [])

        if not new_order:  # never rewrites a playlist without a new order
            return jsonify({"status": "error", "message": "No order received"}), 400

        headers = ffheaders()
        url = f"{readaddress()}/api/playlist/{readid()}?date={selected_date}"

        try:

            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": "Could not fetch playlist from ffplayout",
                        }
                    ),
                    500,
                )

            data = response.json()
            api_items = data.get("program", [])

            reordered_program = [
                api_items[index] for index in new_order if 0 <= index < len(api_items)
            ]  # by position, so a repeated media keeps its own in and out
            if (
                not reordered_program
            ):  # nothing valid in the new order, so the playlist stays untouched
                return jsonify({"status": "error", "message": "Invalid order"}), 400

            data["program"] = reordered_program

            session.pop("draft_playlist", None)
            session.modified = True

            url_post = f"{readaddress()}/api/playlist/{readid()}"
            save_response = requests.post(url_post, headers=headers, json=data)

            if save_response.status_code in [200, 201]:
                print(
                    bcolors.OKGREEN
                    + datetime.datetime.now().strftime("%H:%M:%S")
                    + f" [SUCCESS] Playlist reordered for {selected_date}"
                    + bcolors.ENDC
                )
                return jsonify({"status": "success", "message": "Order updated"}), 200
            else:
                print(
                    bcolors.FAIL
                    + datetime.datetime.now().strftime("%H:%M:%S")
                    + f" [ERROR] Error response : {save_response.text}"
                    + bcolors.ENDC
                )
                return (
                    jsonify(
                        {"status": "error", "message": "Failed to update ffplayout"}
                    ),
                    500,
                )

        except Exception as e:
            print(
                bcolors.FAIL
                + datetime.datetime.now().strftime("%H:%M:%S")
                + f" [ERROR] Error editing the playlist for {selected_date} : {e}"
                + bcolors.ENDC
            )
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route("/playout/playlist_draft_add", methods=["POST"])
    @flask_login.login_required
    def playlist_draft_add():
        media_source = request.args.get("source")
        if not media_source:
            return "", 400

        if "draft_playlist" not in session:
            session["draft_playlist"] = []

        row = get_media_row(media_source)
        if row is None:
            return "", 404

        duration = row["duration"] or length_to_seconds(row["length"] or "00:00")
        folder = row["filepath"]
        full_path = (
            f"{STORAGE_ROOT}/{folder}/{media_source}"
            if folder
            else f"{STORAGE_ROOT}/{media_source}"
        )

        session["draft_playlist"].append(
            {
                "source": full_path,
                "title": media_source,
                "in": 0,
                "out": duration,
                "duration": duration,
            }
        )
        session.modified = True

        selected_date = (
            request.form.get("playlist_date")
            or request.args.get("date")
            or datetime.date.today().strftime("%Y-%m-%d")
        )

        return render_template(
            "modules/playout_editor.html",
            playlist=prepare_items(fetch_api_items(selected_date), selected_date),
            selected_date=selected_date,
        )

    @app.route("/playout/playlist_save_all", methods=["POST"])
    @flask_login.login_required
    def playlist_save_all():
        selected_date = request.form.get("playlist_date") or request.args.get("date")
        if not selected_date:
            return jsonify({"error": "Missing date"}), 400

        headers = ffheaders()
        url_get = f"{readaddress()}/api/playlist/{readid()}?date={selected_date}"

        try:
            response = requests.get(url_get, headers=headers)
            playlist_data = (
                response.json()
                if response.status_code == 200
                else {"date": selected_date, "program": []}
            )

            if "program" not in playlist_data:
                playlist_data["program"] = []

            deleted = get_deleted(selected_date)
            kept = [
                item
                for i, item in enumerate(playlist_data["program"])
                if i not in deleted
            ]
            playlist_data["program"] = kept + session.get("draft_playlist", [])

            url_post = f"{readaddress()}/api/playlist/{readid()}"
            save_response = requests.post(url_post, headers=headers, json=playlist_data)

            if save_response.status_code in [200, 201]:
                session.pop("draft_playlist", None)
                session.pop("draft_deleted", None)
                print(
                    bcolors.OKGREEN
                    + datetime.datetime.now().strftime("%H:%M:%S")
                    + f" [SUCCESS] Playlist saved for {selected_date}"
                    + bcolors.ENDC
                )
                return "", 204
            else:
                return jsonify({"error": "Failed to save"}), 500

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/playout/inspect", methods=["GET"])
    @flask_login.login_required
    def playout_inspect():
        name = request.args.get("name", "")
        media = None
        if name:
            with connect_db() as db:
                media = db.execute(
                    "SELECT * FROM media WHERE filename = ?", (name,)
                ).fetchone()

        return render_template(
            "modules/playout_inspector.html",
            media=media,
            types=get_distinct_values("type"),
            families=get_distinct_values("fam"),
        )

    @app.route("/playout/playlist_draft_delete", methods=["POST"])
    @flask_login.login_required
    def playlist_draft_delete():

        selected_date = request.form.get("playlist_date")
        selected = request.form.get("selected", "")

        # checking if we detele a playlist item properly
        if not selected.startswith("playlist:"):
            return "", 204

        # split the string to get index number
        split_select = selected.split(":")
        index = int(split_select[1])

        # fetching items from ffplayout api first
        api_items = []
        headers = ffheaders()
        url = f"{readaddress()}/api/playlist/{readid()}?date={selected_date}"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            api_items = response.json().get("program", [])

        # get session drafts
        drafts = session.get("draft_playlist", [])

        # if index is bigger than api items length,it is in the session draft
        if index >= len(api_items):
            draft_index = index - len(api_items)
            if 0 <= draft_index < len(drafts):
                drafts.pop(draft_index)
                session["draft_playlist"] = drafts
                session.modified = True
        else:
            # else, it is in the real api playlist, and we remove it there
            api_items.pop(index)
            playlist_data = {"date": selected_date, "program": api_items}
            url_post = f"{readaddress()}/api/playlist/{readid()}"
            requests.post(url_post, headers=headers, json=playlist_data)

        # mergeing everything
        full_items = api_items + session.get("draft_playlist", [])

        # recalculata durations like everywhere else
        for item in full_items:
            if "duration" in item:
                total_seconds = int(item["duration"])
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                if hours > 0:
                    item["formatted_duration"] = (
                        f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    )
                else:
                    item["formatted_duration"] = f"{minutes:02d}:{seconds:02d}"

        return render_template(
            "modules/playout_editor.html",
            playlist=prepare_items(api_items, selected_date),
            selected_date=selected_date,
        )

    @app.route("/playout/playlist_clear", methods=["POST"])
    @flask_login.login_required
    def playlist_clear():
        selected_date = request.form.get("playlist_date") or request.args.get("date")
        if not selected_date:
            return jsonify({"error": "Missing date"}), 400

        api_items = fetch_api_items(selected_date)

        session.pop("draft_playlist", None)
        session["draft_deleted"] = {
            "date": selected_date,
            "indices": list(range(len(api_items))),
        }
        session.modified = True

        return render_template(
            "modules/playout_editor.html",
            playlist=prepare_items(api_items, selected_date),
            selected_date=selected_date,
        )

    @app.route("/playout/playlist_download", methods=["GET"])
    @flask_login.login_required
    def playlist_download():
        selected_date = request.args.get(
            "playlist_date", datetime.date.today().strftime("%Y-%m-%d")
        )

        headers = ffheaders()
        url = f"{readaddress()}/api/playlist/{readid()}?date={selected_date}"

        try:
            response = requests.get(url, headers=headers)
            playlist_data = (
                response.json()
                if response.status_code == 200
                else {"date": selected_date, "program": []}
            )

            drafts = session.get("draft_playlist", [])
            if "program" in playlist_data:
                playlist_data["program"].extend(drafts)
            else:
                playlist_data["program"] = drafts

            json_str = json.dumps(playlist_data, indent=4, ensure_ascii=False)

            return Response(
                json_str,
                mimetype="application/json",
                headers={
                    "Content-Disposition": f"attachment;filename=playlist_{selected_date}.json"
                },
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/playout/edit", methods=["GET", "POST"])  # metadata editor
    @flask_login.login_required
    def edit_form():
        media = None
        target_filename = request.args.get("filename") or request.form.get("filename")

        if request.method == "POST":
            name = request.form.get("name", "") or None
            type = request.form.get("type", "")
            family = request.form.get("family", "")
            description = request.form.get("description", "")
            first = request.form.get("first", "") or None
            last = request.form.get("last", "") or None
            season = request.form.get("season", "")

            try:
                with connect_db() as authdb:
                    cursor_auth = authdb.cursor()
                    cursor_auth.execute(
                        """UPDATE media 
                        SET medianame = ?, type = ?, fam = ?, season = ?, description = ?, firstaired = ?, lastaired = ? 
                        WHERE filename = ?""",
                        (
                            name,
                            type,
                            family,
                            season,
                            description,
                            first,
                            last,
                            target_filename,
                        ),
                    )
                    authdb.commit()
            except Exception as e:
                print(f"An error occurred while updating the media: {e}")

        return redirect("/playout")
