from flask import Flask, render_template, request, redirect, url_for, jsonify
import flask_login
from flask_login import UserMixin, LoginManager, login_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from bcolors import bcolors
import datetime
import sqlite3
import json
from cryptography.fernet import Fernet
from ffplayout import getinfo_current_media, getinfo_current_playlist

app = Flask(__name__)

app.secret_key = os.urandom(24).hex()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'

class User(UserMixin):
    def __init__(self, username):
        self.id = username

@login_manager.user_loader
def load_user(username):

    with open('settings/config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    auth_path = config["db"]["auth_path"]
    authdb = sqlite3.connect(auth_path)
    cursor = authdb.cursor()

    cursor.execute("SELECT username FROM el_credentials WHERE username = ?", (username,))
    result = cursor.fetchone()
    authdb.close()

    if result:
        return User(result[0])

    return None

def setup_status():
    os.makedirs('databases', exist_ok=True) #verify if the folder exists
    db_path = 'databases/auth.db' #defines the auth.db path

    if not os.path.exists(db_path) or os.path.getsize(db_path) == 0: #file does not exists or 0b in size
            return False

    try:
        authdb = sqlite3.connect(db_path)
        cursor = authdb.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='el_credentials';")
        if not cursor.fetchone():
            authdb.close()
            return False

        cursor.execute("SELECT COUNT(*) FROM el_credentials")
        count = cursor.fetchone()[0]
        authdb.close()

        if count == 0:
            return False

    except Exception:
        return False

    return True


def webserver():
    @app.route('/setup', methods=['GET', 'POST'])
    def setup_page():
        if setup_status():
            return redirect("/login", code=302)

        if request.method == 'POST':
            ffuser = request.form['ffuser']
            ffkey = Fernet.generate_key().decode('utf-8')
            cipher_suite = Fernet(ffkey.encode('utf-8'))
            ffpassword_plain = request.form['ffpassword']
            ffpassword_hashed = cipher_suite.encrypt(ffpassword_plain.encode('utf-8'))
            ffaddress = request.form['ffaddress']
            eluser = request.form['eluser']
            elpassword_plain = request.form['elpassword']
            elpassword_hashed = generate_password_hash(elpassword_plain, method="pbkdf2:sha256")

            def write_db():

                with open('settings/config.json', 'r', encoding='utf-8') as db_scan:
                    db_read = json.load(db_scan)

                os.makedirs('databases', exist_ok=True)
                auth_path = db_read["db"]["auth_path"]
                authdb = sqlite3.connect(auth_path)
                print(bcolors.OKGREEN + datetime.datetime.now().strftime("%H:%M:%S") + " [INFO] The database was successfully loaded" + bcolors.ENDC)

                try:
                    with authdb:
                        cursor_auth = authdb.cursor()
                        cursor_auth.execute(("INSERT INTO el_ffplayout (username, password) values (?, ?)"), (ffuser, ffpassword_hashed))
                        authdb.commit()
                except Exception as e:
                    print(f"An error occured while creating the table:{e}")

                try:
                    with authdb:
                        cursor_auth = authdb.cursor()
                        cursor_auth.execute(("INSERT INTO el_credentials (username, password) values (?, ?)"), (eluser, elpassword_hashed))
                        authdb.commit()
                except Exception as e:
                    print(f"An error occured while creating the table:{e}")
                authdb.close()
            write_db()
            with open('settings/config.json', 'r+') as f:
                data = json.load(f)
                data['ffplayout']['base_url'] = ffaddress
                data['ffplayout']['private_key'] = ffkey
                f.seek(0)
                json.dump(data, f, indent=4)
                f.truncate()
            return redirect("/login", code=302)
        return render_template('setup.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login_page():
        if request.method == 'POST':
            loginuser = request.form['loginuser']
            loginpassword = request.form['loginpassword']

            def read_db():

                with open('settings/config.json', 'r', encoding='utf-8') as db_scan:
                    db_read = json.load(db_scan)

                os.makedirs('databases', exist_ok=True)
                auth_path = db_read["db"]["auth_path"]
                authdb = sqlite3.connect(auth_path)
                print(bcolors.OKGREEN + datetime.datetime.now().strftime("%H:%M:%S") + " [INFO] The database was successfully loaded" + bcolors.ENDC)

                
                with authdb:
                    cursor_auth = authdb.cursor()
                    cursor_auth.execute("SELECT password FROM el_credentials WHERE username = ?", (loginuser,))
                    authdb.commit()

                result = cursor_auth.fetchone()
                authdb.close()

                if result is None:
                    return False

                check_pass = check_password_hash(result[0], loginpassword)
                return check_pass

            check_pass = read_db()
            if check_pass == True:
                user_obj = User(loginuser)
                login_user(user_obj)
                return redirect("/dashboard", code=302)
        return render_template('login.html')

    
    @app.route('/')
    @app.route('/dashboard', methods=['GET', 'POST'])
    @flask_login.login_required
    def dashboard_page():
        return render_template('dashboard.html', media=getinfo_current_media())

    @app.route('/dashboard/status')
    @flask_login.login_required
    def dashboard_status():
        media_data = getinfo_current_media()
        if media_data:
            if "media" in media_data and "source" in media_data["media"]:
                file_path = media_data["media"]["source"]
                file_name = os.path.splitext(os.path.basename(file_path))[0]
                media_data["media"]["title"] = file_name
                return jsonify(media_data)
        return jsonify({"error": "Unable to fetch your data"}), 500

    @app.route('/dashboard/status/current_media')
    @flask_login.login_required
    def dashboard_status_curmed():
        media_data = getinfo_current_media()

        title = "Nothing is playing"

        if media_data:
            if "media" in media_data and "source" in media_data["media"]:
                file_path = media_data["media"]["source"]
                file_name = os.path.splitext(os.path.basename(file_path))[0]
                title = file_name

        media_name = {
            "title": title
        }

        return title

    @app.route('/dashboard/status/current_elapsed')
    @flask_login.login_required
    def dashboard_status_curelap():
        media_data = getinfo_current_media()

        elapsed = "00:00"

        if media_data:
            if media_data and "elapsed" in media_data:
                elapsed = media_data["elapsed"]

        media_elapsed = {
            "elapsed": elapsed
        }

        minutes = int(elapsed / 60)
        seconds = int(elapsed % 60)
        elapsed_post = f"{minutes}:{seconds}"

        return elapsed_post

    @app.route('/dashboard/status/current_duration')
    @flask_login.login_required
    def dashboard_status_curdur():
        media_data = getinfo_current_media()

        duration = "00:00"

        if media_data:
            if "media" in media_data and "duration" in media_data["media"]:
                duration = media_data["media"]["duration"]

        media_duration = {
            "duration": duration
        }

        minutes = int(duration / 60)
        seconds = int(duration % 60)
        duration_post = f"{minutes}:{seconds}"

        return duration_post

    @app.route('/dashboard/status/progress')
    @flask_login.login_required
    def dashboard_status_progress():
        media_data = getinfo_current_media()

        duration = 0
        elapsed = 0

        if media_data:
            if "media" in media_data and "duration" in media_data["media"]:
                duration = media_data["media"]["duration"]
            if media_data and "elapsed" in media_data:
                elapsed = media_data["elapsed"]

        if duration > 0:
            progress = int((elapsed / duration) * 100)
        else:
            progress = 0
        progress_post = f"width: {progress}%;"

        return f'<div class="bg-emerald-500 h-full transition-all duration-500" style="width: {progress}%;" hx-get="/dashboard/status/progress" hx-trigger="every 0.5s" hx-swap="outerHTML"></div>'

    @app.route('/dashboard/running')
    @flask_login.login_required
    def dashboard_running():
        playlist_data = getinfo_current_playlist()
        if playlist_data:
            items = playlist_data.get("program", [])
            
            for item in items:
                if "source" in item:
                    file_path = item["source"]
                    file_name = os.path.splitext(os.path.basename(file_path))[0]
                    item["title"] = file_name
                    
            return jsonify(playlist_data)
            
        return jsonify({"error": "Unable to fetch your data"}), 500

    print(bcolors.OKGREEN + datetime.datetime.now().strftime("%H:%M:%S") + " [INFO] The webserver was successfully loaded" + bcolors.ENDC)
    app.run(debug=True, port=8080)

if __name__ == '__main__':
    webserver()