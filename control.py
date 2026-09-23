from flask import Flask, render_template
import os
from bcolors import bcolors
import datetime

app = Flask(__name__)

def webserver():

    @app.route('/setup', methods=['GET', 'POST'])
    def setup_page():
        return render_template('setup.html')

    print(bcolors.OKGREEN + datetime.datetime.now().strftime("%H:%M:%S") + " [INFO] The webserver was successfully loaded" + bcolors.ENDC)
    app.run(debug=True, port=8080)

if __name__ == '__main__':
    webserver()
