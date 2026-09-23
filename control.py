from flask import Flask, render_template, request, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import os
from bcolors import bcolors
import datetime
import sqlite3
import json

app = Flask(__name__)

def webserver():

    @app.route('/setup', methods=['GET', 'POST'])
    def setup_page():
        if request.method == 'POST':
            ffuser = request.form['ffuser']
            ffpassword_plain = request.form['ffpassword']
            ffpassword_hashed = generate_password_hash(ffpassword_plain, method="pbkdf2:sha256")
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
                data['base_url'] = ffaddress
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

                check_pass = check_password_hash(result[0], loginpassword)
                return check_pass

            read_db()
            check_pass = read_db()
            if check_pass == True:
                return redirect("/dashboard", code=302)
        return render_template('login.html')

    print(bcolors.OKGREEN + datetime.datetime.now().strftime("%H:%M:%S") + " [INFO] The webserver was successfully loaded" + bcolors.ENDC)
    app.run(debug=True, port=8080)

if __name__ == '__main__':
    webserver()