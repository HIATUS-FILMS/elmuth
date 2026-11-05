# This is the engine that magically turns templates into playlists

# The engine never talks to flask or to ffplayout : it receives a template, a date and the medias, and returns the playlist items
# Media conventions (see the wiki) :
# type Filler = fillers, families listed in "stretch_families" (Still by default) are short clips that can be stretched
# type Jingle = jingles, the families Intro and Outro are chosen in the block settings
# any other type = programs
# Every duration is calculated in integer milliseconds, so a block always ends exactly on its time_end

import datetime
import random
import re
import sqlite3
from bcolors import bcolors

DAY_MS = 86400000 #milliseconds in a day
DAY_CODES = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"] #same codes as the preferred days of the templates

#defining the engine values (in seconds, can be overridden by the "engine" part of config.json)

default_config = {
    "filler_type": "Filler",
    "jingle_type": "Jingle",
    "stretch_families": ["Still"],
    "recent_days": 15, #a media aired during the last X days is recent
    "gap_min": 4.0, #shortest filler gap between two programs
    "gap_target": 30.0, #wanted filler gap between two programs
    "gap_max": 180.0, #above this, a warning is raised
    "hold": 3.0, #fixed logo at the start and at the end of a gap
    "body_max": 120.0, #longest chain of moving fillers inside a gap
    "min_cut": 60.0, #a program is never hard cut below this length
    "min_tail": 1.0, #avoids ending a gap with a tiny truncated filler
    "tries": 60, #random orders tested in shuffle mode
    "storage_root": "/var/lib/ffplayout/tv-media",
}

#defining the generation options (the checkboxes of "Generate from template")

default_options = {
    "force": False, #ignores the preferred days and the first / last aired of the template
    "no_repeat_day": True, #a program is only aired once a day
    "fill_gaps": True, #fills the time between two blocks with fillers
    "seed": None, #same seed = same playlist
}

def engine_log(color, level, message): #prints a message like the rest of elmuth
    print(color + datetime.datetime.now().strftime("%H:%M:%S") + f" [{level}] " + message + bcolors.ENDC)

def engine_warn(state, block_label, message): #saves a warning for the playlist and prints it
    if block_label:
        message = f"[{block_label}] {message}"
    state["warnings"].append(message)
    engine_log(bcolors.WARNING, "WARN", message)

def time_to_ms(time_text): #converts HH:MM:SS (or HH:MM) to milliseconds
    time_parts = [int(part) for part in str(time_text).split(":")]
    while len(time_parts) < 3: #adds the missing minutes and seconds
        time_parts.append(0)
    hours, minutes, seconds = time_parts[:3]
    return ((hours * 60 + minutes) * 60 + seconds) * 1000

def ms_to_time(milliseconds): #converts milliseconds to HH:MM:SS
    total_seconds = int(round(milliseconds / 1000))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def ms_to_seconds(milliseconds): #ffplayout wants seconds
    return round(milliseconds / 1000, 3)

def length_to_ms(length_text): #converts the MM:SS or HH:MM:SS length of the database to milliseconds
    seconds = 0
    for part in str(length_text).split(":"):
        seconds = seconds * 60 + int(part)
    return seconds * 1000

def natural_sort_key(text): #sorts episode2 before episode10
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", text or "")]

def load_medias(db_path="databases/medias.db"): #reads the media table, works with or without the duration column
    medias = []
    try:
        with sqlite3.connect(db_path) as connect:
            connect.row_factory = sqlite3.Row
            table_columns = [column["name"] for column in connect.execute("PRAGMA table_info(media)")] #checks which columns exist

            for row in connect.execute("SELECT * FROM media"):
                if "present" in table_columns and row["present"] == 0: #the file is not in the storage anymore
                    continue

                duration_ms = 0
                approximate = False
                if "duration" in table_columns and row["duration"]: #exact duration
                    duration_ms = int(round(float(row["duration"]) * 1000))
                elif row["length"]: #old rounded length
                    try:
                        duration_ms = length_to_ms(row["length"])
                        approximate = True
                    except ValueError:
                        duration_ms = 0

                medias.append({
                    "id": row["id"],
                    "filename": row["filename"],
                    "filepath": row["filepath"] or "",
                    "type": row["type"] or "",
                    "fam": row["fam"] or "",
                    "season": row["season"] or "",
                    "lastaired": (row["lastaired"] if "lastaired" in table_columns else "") or "",
                    "duration_ms": duration_ms,
                    "approximate": approximate
                })
    except Exception as e:
        engine_log(bcolors.FAIL, "ERROR", f"Error reading the media database : {e}")
    return medias

def is_recent(media, selected_day, recent_days): #true if the media was aired during the days BEFORE the selected day
    if not media["lastaired"]:
        return False
    try:
        aired_day = datetime.date.fromisoformat(media["lastaired"][:10])
    except ValueError:
        return False
    days_since = (selected_day - aired_day).days
    return 0 < days_since <= recent_days #same day or future airings are ignored, so a day can be generated again

def template_not_applicable(template, selected_day): #returns why the template can't be used this day, or None
    preferred_days = template.get("preferred_days") or []
    day_code = DAY_CODES[selected_day.weekday()]
    if preferred_days and day_code not in preferred_days:
        return f"template is meant for {', '.join(preferred_days)}, not {day_code}"

    first_aired = template.get("first_aired")
    if first_aired and first_aired != "N/A":
        try:
            if selected_day < datetime.date.fromisoformat(first_aired):
                return f"template starts on {first_aired}"
        except ValueError:
            pass

    last_aired = template.get("last_aired")
    if last_aired and last_aired != "N/A":
        try:
            if selected_day > datetime.date.fromisoformat(last_aired):
                return f"template ended on {last_aired}"
        except ValueError:
            pass
    return None

def add_playlist_item(state, media, out_ms): #adds a media to the playlist, the same way playlist_draft_add does
    folder = media["filepath"]
    storage_root = state["settings"]["storage_root"]
    full_path = f"{storage_root}/{folder}/{media['filename']}" if folder else f"{storage_root}/{media['filename']}"

    state["items"].append({
        "source": full_path,
        "title": media["filename"],
        "in": 0,
        "out": ms_to_seconds(out_ms),
        "duration": ms_to_seconds(media["duration_ms"])
    })
    state["clock"] += out_ms #the clock is the real time of the playlist
    if media["approximate"]:
        state["approximate_filenames"].add(media["filename"])

def filler_chain(state, total_ms, exact): #random chain of moving fillers, exact = fills total_ms to the millisecond
    settings = state["settings"]
    chain = []
    time_left = total_ms
    previous_filler = None

    while time_left > 0:
        if exact: #exact leaves nothing, or at least min_tail
            fitting_fillers = [filler for filler in state["moving_fillers"] if filler["duration_ms"] == time_left or filler["duration_ms"] <= time_left - settings["min_tail"]]
        else:
            fitting_fillers = [filler for filler in state["moving_fillers"] if filler["duration_ms"] <= time_left]

        if fitting_fillers:
            different_fillers = [filler for filler in fitting_fillers if filler is not previous_filler] #avoids the same filler twice in a row
            filler = state["random_generator"].choice(different_fillers or fitting_fillers)
            chain.append({"media": filler, "out_ms": filler["duration_ms"]})
            time_left -= filler["duration_ms"]
            previous_filler = filler
        elif exact: #nothing fits, so the last filler is truncated
            different_fillers = [filler for filler in state["moving_fillers"] if filler is not previous_filler]
            filler = state["random_generator"].choice(different_fillers or state["moving_fillers"])
            out_ms = min(filler["duration_ms"], time_left)
            chain.append({"media": filler, "out_ms": out_ms})
            time_left -= out_ms
            previous_filler = filler
        else:
            break
    return chain, time_left

def filler_sequence(state, gap_ms): #fillers adding up to exactly gap_ms, or None if there is no filler
    settings = state["settings"]

    if state["still_fillers"]:
        still_filler = state["random_generator"].choice(state["still_fillers"])
        moving_durations = [filler["duration_ms"] for filler in state["moving_fillers"]]

        if moving_durations and gap_ms >= 2 * settings["hold"] + min(moving_durations): #logo, moving fillers, logo
            chain, time_left = filler_chain(state, min(gap_ms - 2 * settings["hold"], settings["body_max"]), False)
            chain_total = sum(filler["out_ms"] for filler in chain)
            end_logo_ms = gap_ms - settings["hold"] - chain_total #the end logo takes everything that is left
            return [{"media": still_filler, "out_ms": settings["hold"]}] + chain + [{"media": still_filler, "out_ms": end_logo_ms}]
        return [{"media": still_filler, "out_ms": gap_ms}] #only the logo, stretched

    if state["moving_fillers"]:
        chain, time_left = filler_chain(state, gap_ms, True)
        return chain
    return None

def fill_gap(state, gap_ms, block_label): #fills a gap with fillers, returns false if it can't
    if gap_ms <= 0:
        return True

    sequence = filler_sequence(state, gap_ms)
    if sequence is None:
        if not state["no_filler_warned"]: #only warns once
            engine_warn(state, block_label, "no filler available (type Filler), time cannot be filled")
            state["no_filler_warned"] = True
        return False

    for sequence_item in sequence:
        add_playlist_item(state, sequence_item["media"], sequence_item["out_ms"])
    return True

def block_criteria(block): #returns the column and the value used by the block, family or type
    block_family = block.get("family", "N/A")
    block_type = block.get("type", "N/A")
    if block_family and block_family != "N/A":
        return "fam", block_family
    if block_type and block_type != "N/A":
        return "type", block_type
    return None, None

def order_candidates(state, candidate_programs, playback_mode): #returns the orders to test for the block
    if playback_mode == "strict": #season, then name
        return [sorted(candidate_programs, key=lambda program: (natural_sort_key(program["season"]), natural_sort_key(program["filename"])))]
    if playback_mode == "recent": #last added first
        return [sorted(candidate_programs, key=lambda program: -program["id"])]

    orders = []
    for attempt in range(max(1, int(state["settings"]["tries"]))): #shuffle, tests many orders to keep the best one
        shuffled_programs = candidate_programs[:]
        state["random_generator"].shuffle(shuffled_programs)
        orders.append(shuffled_programs)
    return orders

def fit_programs(state, ordered_programs, available_ms, strict_order, hard_cut): #chooses the programs of a block for one order
    settings = state["settings"]
    programs_chosen = []
    chosen_total = 0
    programs_left = []

    for program_index, program in enumerate(ordered_programs):
        if chosen_total + program["duration_ms"] + (len(programs_chosen) + 1) * settings["gap_min"] <= available_ms: #the program fits with its gap
            programs_chosen.append({"media": program, "out_ms": program["duration_ms"]})
            chosen_total += program["duration_ms"]
        else:
            programs_left.append(program)
            if strict_order: #strict order never skips a program
                programs_left.extend(ordered_programs[program_index + 1:])
                break

    cut_media = None
    if hard_cut and programs_left:
        gap_slots = len(programs_chosen) + 1
        cut_length = available_ms - chosen_total - gap_slots * settings["gap_target"]
        current_gap = (available_ms - chosen_total) / max(len(programs_chosen), 1)
        if cut_length >= settings["min_cut"] and current_gap > settings["gap_target"]: #the gaps would be too long, so the next program is cut
            cut_media = programs_left[0]
            cut_length = min(cut_length, cut_media["duration_ms"])
            programs_chosen.append({"media": cut_media, "out_ms": cut_length})
            chosen_total += cut_length

    gap_total = available_ms - chosen_total
    gap_each = gap_total / len(programs_chosen) if programs_chosen else available_ms
    score = int(abs(gap_each - settings["gap_target"]) + (10000 if cut_media else 0)) #the closest to the wanted gap wins, a cut costs a bit

    return {
        "programs_chosen": programs_chosen,
        "cut_media": cut_media,
        "gap_total": gap_total,
        "programs_left": len(programs_left),
        "score": score
    }

def find_block_media(state, media_name, media_kind, block_label): #finds the intro or the outro of a block
    if not media_name:
        return None
    media = state["medias_by_name"].get(media_name)
    if media is None:
        engine_warn(state, block_label, f"{media_kind} media '{media_name}' not found, ignored")
    return media

def bridge_to_block(state, gap_ms, block_label): #fills the time between the end of a block and the start of the next one
    gap_start = state["clock"]
    if state["options"]["fill_gaps"] and fill_gap(state, gap_ms, block_label):
        if gap_ms > 60000: #only warns for long gaps
            engine_warn(state, block_label, f"nothing scheduled from {ms_to_time(gap_start)} to {ms_to_time(gap_start + gap_ms)}, filled with fillers")
    else:
        engine_warn(state, block_label, f"nothing scheduled from {ms_to_time(gap_start)} to {ms_to_time(gap_start + gap_ms)} and not filled, the block starts earlier")

def run_block(state, block): #generates one block of the template
    settings = state["settings"]

    try:
        block_start = time_to_ms(block["time_start"])
        block_end = time_to_ms(block["time_end"])
    except (KeyError, ValueError):
        engine_warn(state, None, "block with an invalid time_start / time_end ignored")
        return
    if block_end == 0 and block_start > 0: #00:00:00 as an end means midnight
        block_end = DAY_MS
    block_label = f"{ms_to_time(block_start)}-{ms_to_time(block_end)}"
    if block_end <= block_start:
        engine_warn(state, block_label, "end is not after start, block ignored")
        return

    criteria_column, criteria_value = block_criteria(block)
    if criteria_column is None:
        engine_warn(state, block_label, "no family or type set, block ignored")
        return

    if state["clock"] < block_start: #time before the block
        bridge_to_block(state, block_start - state["clock"], block_label)
    elif state["clock"] > block_start:
        engine_warn(state, block_label, f"block starts at {ms_to_time(state['clock'])} instead of {ms_to_time(block_start)} (previous block too long)")
    if state["clock"] >= block_end:
        engine_warn(state, block_label, "no time left for this block, ignored")
        return
    block_window = block_end - state["clock"]

    block_options = block.get("options", {})
    playback_mode = block_options.get("playback_mode", "shuffle")
    hard_cut = block_options.get("transition_mode", "hard") == "hard"
    exclude_recent = block_options.get("recent_policy", "exclude_recent") == "exclude_recent"

    #candidates of the block
    candidate_programs = [program for program in state["programs"] if program[criteria_column].lower() == criteria_value.lower()]
    criteria_name = "family" if criteria_column == "fam" else "type"
    if not candidate_programs:
        other_column = "type" if criteria_column == "fam" else "fam"
        found_elsewhere = len([program for program in state["programs"] if program[other_column].lower() == criteria_value.lower()])
        hint = f" ({found_elsewhere} found with {other_column} = {criteria_value}, wrong criteria ?)" if found_elsewhere else ""
        engine_warn(state, block_label, f"no program found for {criteria_name} = {criteria_value}{hint}")

    programs_found = len(candidate_programs)
    if state["options"]["no_repeat_day"]: #removes what was already aired today
        candidate_programs = [program for program in candidate_programs if program["filename"] not in state["used_filenames"]]
    aired_today = programs_found - len(candidate_programs)

    recent_count = 0
    if exclude_recent: #removes what was aired during the last days
        not_recent_programs = [program for program in candidate_programs if not is_recent(program, state["selected_day"], int(settings["recent_days"]))]
        recent_count = len(candidate_programs) - len(not_recent_programs)
        candidate_programs = not_recent_programs
    if programs_found and (aired_today or recent_count):
        engine_warn(state, block_label, f"{programs_found} programs found, {aired_today} already aired today, {recent_count} aired during the last {settings['recent_days']} days, {len(candidate_programs)} left")

    #intro and outro of the block
    intro_media = find_block_media(state, block.get("intro_media"), "intro", block_label)
    outro_media = find_block_media(state, block.get("outro_media"), "outro", block_label)
    reserved_ms = sum(media["duration_ms"] for media in (intro_media, outro_media) if media)
    if reserved_ms >= block_window:
        engine_warn(state, block_label, "intro and outro are longer than the block, ignored")
        intro_media = None
        outro_media = None
        reserved_ms = 0
    available_ms = block_window - reserved_ms

    #the best plan among all the tested orders
    best_plan = None
    for ordered_programs in order_candidates(state, candidate_programs, playback_mode):
        plan = fit_programs(state, ordered_programs, available_ms, playback_mode == "strict", hard_cut)
        if best_plan is None or plan["score"] < best_plan["score"]:
            best_plan = plan

    #writing the block in the playlist
    block_started_at = state["clock"]
    if intro_media:
        add_playlist_item(state, intro_media, intro_media["duration_ms"])

    programs_chosen = best_plan["programs_chosen"]
    if not programs_chosen:
        if candidate_programs:
            engine_warn(state, block_label, "no program fits in this block (try hard cut), filled with fillers")
        fill_gap(state, available_ms, block_label)
    else:
        gap_each = best_plan["gap_total"] // len(programs_chosen)
        gap_remainder = best_plan["gap_total"] - gap_each * len(programs_chosen) #the last gap takes the remaining milliseconds
        for program_index, program_chosen in enumerate(programs_chosen):
            add_playlist_item(state, program_chosen["media"], program_chosen["out_ms"])
            state["used_filenames"].add(program_chosen["media"]["filename"])
            if program_index == len(programs_chosen) - 1:
                fill_gap(state, gap_each + gap_remainder, block_label)
            else:
                fill_gap(state, gap_each, block_label)

        if best_plan["gap_total"] / len(programs_chosen) > settings["gap_max"]: #gaps are too long
            reason = "programs too long to fit" if best_plan["programs_left"] else "not enough programs"
            engine_warn(state, block_label, f"{reason}, {int(best_plan['gap_total'] / len(programs_chosen) / 1000)}s of filler between the programs")

    if outro_media:
        add_playlist_item(state, outro_media, outro_media["duration_ms"])

    block_drift = block_end - state["clock"] #should always be 0
    if block_drift != 0:
        engine_warn(state, block_label, f"block ends at {ms_to_time(state['clock'])} instead of {ms_to_time(block_end)}")

    state["report"].append({
        "block": block_label,
        "criteria": f"{criteria_name} = {criteria_value}",
        "mode": playback_mode,
        "transition": "hard" if hard_cut else "smooth",
        "programs": [program_chosen["media"]["filename"] for program_chosen in programs_chosen],
        "cut": best_plan["cut_media"]["filename"] if best_plan["cut_media"] else None,
        "filler_seconds": ms_to_seconds(best_plan["gap_total"]),
        "drift_ms": block_drift,
        "started_at": ms_to_time(block_started_at)
    })

def generate_playlist(template, selected_date, medias, config=None, options=None): #turns a template into a playlist
    engine_config = {**default_config, **(config or {})}
    engine_options = {**default_options, **(options or {})}

    try:
        selected_day = selected_date if isinstance(selected_date, datetime.date) else datetime.date.fromisoformat(selected_date)
    except ValueError:
        engine_log(bcolors.FAIL, "ERROR", f"Invalid date for the generation : {selected_date}")
        return {"items": [], "warnings": [f"invalid date : {selected_date}"], "report": []}

    engine_log(bcolors.OKBLUE, "INFO", f"Generating the playlist of {selected_day.isoformat()} from the template {template.get('name', '')}")

    if not engine_options["force"]:
        not_applicable_reason = template_not_applicable(template, selected_day)
        if not_applicable_reason:
            engine_log(bcolors.WARNING, "WARN", f"{not_applicable_reason}, nothing generated")
            return {"items": [], "warnings": [f"{not_applicable_reason}, nothing generated (use force to ignore this)"], "report": []}

    #durations of the engine settings, converted to milliseconds
    settings = dict(engine_config)
    for setting_name in ["gap_min", "gap_target", "gap_max", "hold", "body_max", "min_cut", "min_tail"]:
        settings[setting_name] = int(round(float(engine_config[setting_name]) * 1000))

    seed = engine_options["seed"]
    if seed is None: #same template and same date always give the same playlist
        seed = f"{selected_day.isoformat()}|{template.get('name', '')}"

    state = {
        "settings": settings,
        "options": engine_options,
        "selected_day": selected_day,
        "random_generator": random.Random(seed),
        "items": [],
        "warnings": [],
        "report": [],
        "clock": 0, #real time of the playlist in milliseconds, starts at 00:00:00
        "used_filenames": set(),
        "approximate_filenames": set(),
        "no_filler_warned": False
    }

    usable_medias = [media for media in medias if media["duration_ms"] > 0]
    if len(usable_medias) < len(medias):
        engine_warn(state, None, f"{len(medias) - len(usable_medias)} media skipped (no duration, rescan the library)")

    filler_type = settings["filler_type"].lower()
    jingle_type = settings["jingle_type"].lower()
    stretch_families = [family.lower() for family in settings["stretch_families"]]
    fillers = [media for media in usable_medias if media["type"].lower() == filler_type]

    state["medias_by_name"] = {media["filename"]: media for media in usable_medias}
    state["programs"] = [media for media in usable_medias if media["type"].lower() not in (filler_type, jingle_type)]
    state["still_fillers"] = [media for media in fillers if media["fam"].lower() in stretch_families]
    state["moving_fillers"] = [media for media in fillers if media["fam"].lower() not in stretch_families]

    template_blocks = template.get("blocks", [])
    if not template_blocks:
        engine_warn(state, None, "the template has no block")
    for block in sorted(template_blocks, key=lambda block: block.get("time_start", "")):
        run_block(state, block)

    if state["items"] and state["clock"] < DAY_MS:
        engine_warn(state, None, f"playlist ends at {ms_to_time(state['clock'])}, nothing scheduled until 24:00:00")
    elif state["clock"] > DAY_MS:
        engine_warn(state, None, f"playlist is {ms_to_time(state['clock'] - DAY_MS)} longer than a day")
    if state["approximate_filenames"]:
        engine_warn(state, None, f"{len(state['approximate_filenames'])} media have durations rounded to the second, rescan the library for exact timing")

    engine_log(bcolors.OKGREEN, "INFO", f"The playlist was generated : {len(state['items'])} items, {len(state['warnings'])} warnings")
    return {"items": state["items"], "warnings": state["warnings"], "report": state["report"]}

if __name__ == '__main__': #python engine.py template_key YYYY-MM-DD, to test the engine without the webserver
    import json
    import sys

    if len(sys.argv) < 3:
        sys.exit("usage : python engine.py template_key YYYY-MM-DD [--force]")

    with open("programs/templates.json", "r", encoding="utf-8") as templates_load:
        templates_loaded = json.load(templates_load)

    playlist = generate_playlist(templates_loaded[sys.argv[1]], sys.argv[2], load_medias(), {}, {"force": "--force" in sys.argv})

    playlist_clock = 0.0
    for item in playlist["items"]:
        print(f"{ms_to_time(int(playlist_clock * 1000))}  {item['out'] - item['in']:>9.3f}s  {item['title']}")
        playlist_clock += item["out"] - item["in"]