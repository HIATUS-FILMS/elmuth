from flask import Flask, render_template,request
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
        return render_template('setup.html')

    print(bcolors.OKGREEN + datetime.datetime.now().strftime("%H:%M:%S") + " [INFO] The webserver was successfully loaded" + bcolors.ENDC)
    app.run(debug=True, port=8080)

if __name__ == '__main__':
    webserver()