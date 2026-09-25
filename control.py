from flask import Flask, render_template, request, redirect, url_for
import flask_login
from flask_login import UserMixin, LoginManager, login_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from bcolors import bcolors
import datetime
import sqlite3
import json
from cryptography.fernet import Fernet

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

    @app.route('/dashboard', methods=['GET', 'POST'])
    @flask_login.login_required
    def dashboard_page():
        return render_template('dashboard.html')

    print(bcolors.OKGREEN + datetime.datetime.now().strftime("%H:%M:%S") + " [INFO] The webserver was successfully loaded" + bcolors.ENDC)
    app.run(debug=True, port=8080)

if __name__ == '__main__':
    webserver()