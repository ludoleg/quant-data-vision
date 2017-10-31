# Copyright 2015 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# [START app]
import logging

import numpy as np

import os
import phaselist

import StringIO
import csv

from flask import Flask, request, render_template, session, make_response

#Application modules
import qxrd
import qxrdtools

UPLOAD_DIR = 'uploads'
UPLOAD_FOLDER = UPLOAD_DIR

if not os.path.isdir(UPLOAD_DIR):
    os.mkdir(UPLOAD_DIR)

ALLOWED_EXTENSIONS = set(['txt', 'plv'])

    # [start config]
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'Ludo'

app.config['DEBUG'] = True

@app.route('/')
def hello():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/odr_demo')
def odr_demo():
    return render_template('odr_demo.html')

# [START process]
@app.route('/process', methods=['POST'])
def process():
    uploaded_file = request.files.get('file')
    if not uploaded_file:
        return 'No file uploaded.', 400

    # Load the sample data file in userData
    # parse sample data file wrt format

    filename = uploaded_file.filename
    XRDdata = uploaded_file
    userData = qxrdtools.openXRD(XRDdata, filename)
    # print userData
    DBname ='difdata_CheMin.txt'
    
    Lambda = 0.0
    Target = 'Co'
    FWHMa = 0.0
    FWHMb = 0.35

    # Boundaries check
    if(Lambda > 2.2 or Lambda == 0):
        Lambda = ''
    if(FWHMa > 0.01):
        FWHMa = 0.01
    if(FWHMa < -0.01):
        FWHMa = -0.01
    if(FWHMb > 1.0):
        FWHMb = 1.0
    if(FWHMb < 0.01):
        FWHMb = 0.01    

    InstrParams = {"Lambda": Lambda, "Target": Target, "FWHMa": FWHMa, "FWHMb": FWHMb}

    # Phase selection
    #    selectedPhases = session['selected']
    selectedPhases = phaselist.defaultPhases
    # print selectedPhases
    # print(selectedPhases, file=sys.stderr)

    # Dif data captures all cristallographic data
    selectedphases = []
    for i in range (len(selectedPhases)):
        name, code = selectedPhases[i].split('\t')
        code = int(code)
        selectedphases.append((name,code))

    # print selectedphases
        
    # Load in the DB file
    difdata = open(DBname, 'r').readlines()

    results, BG, calcdiff = qxrd.Qanalyze(userData, difdata, selectedphases, InstrParams)

    # print(twoT.tolist(), file=sys.stderr)
    # print(userData, file=sys.stderr)

    twoT = userData[0]
    diff = userData[1]

    # logging.debug(results)
    # logging.info("Done with processing")

    angle = twoT
    # diff = diff
    bgpoly = BG
    #calcdiff = calcdiff
    # csv = session_data_key.urlsafe()
    csv = 'ODR'
    session['results'] = results
    session['filename'] = filename
    
    template_vars = {
        'phaselist': results,
        'angle': angle.tolist(),
        'diff': diff.tolist(),
        'bgpoly': bgpoly.tolist(),
        'sum': calcdiff.tolist(),
        'url_text': csv,
        'key': 'ludo',
        'samplename': filename,
        'mode': 'Chemin-ODR'
    }
    return render_template('chart.html', **template_vars)
# [END process]

# [START ODR service]
@app.route('/odr', methods=['GET','POST'])
def odr():
    if request.method == 'POST':
        #L oad data from request
        json_data = request.get_json()
        
        data = json_data
        sample = data['sample']
        filename = sample['name']
        array = sample['data']

        x = [li['x'] for li in array]
        y = [li['y'] for li in array]

        angle = np.asfarray(np.array(x))
        diff = np.asfarray(np.array(y))

        phasearray = data['phases']
        selectedphases = [(d['name'], d['AMCSD_code']) for d in phasearray]
        InstrParams = {"Lambda": 0, "Target": 'Co', "FWHMa": 0.00, "FWHMb": 0.35}
        DBname ='difdata_CheMin.txt'
        # Dif data captures all cristallographic data
        # Load in the DB file
        difdata = open(DBname, 'r').readlines()
        userData = (angle, diff)
        # print(userData)
        results, BG, calcdiff = qxrd.Qanalyze(userData, difdata, selectedphases, InstrParams)

        twoT = userData[0]
        diff = userData[1]

        # logging.debug(results)
        # logging.info("Done with processing")

        angle = twoT
        # diff = diff
        bgpoly = BG
        #calcdiff = calcdiff

        # csv = session_data_key.urlsafe()
        csv = 'ODR'
        session['results'] = results
        session['filename'] = filename
        
        template_vars = {
            'phaselist': results,
            'angle': angle.tolist(),
            'diff': diff.tolist(),
            'bgpoly': bgpoly.tolist(),
            'sum': calcdiff.tolist(),
            'url_text': csv,
            'key': 'ludo',
            'samplename': filename,
            'mode': 'Chemin-ODR'
        }
        return render_template('chart.html', **template_vars)
    else:
        return '''<html><body><h1>Did not get a post!</h1></body></html>'''
# [END ODR service]

# [START CVS]
@app.route('/csvDownload', methods=['GET'])
def csvDownload():
    line = StringIO.StringIO()
    cw = csv.writer(line)
    cw.writerow(['Mineral', 'AMCSD', 'Mass %'])
    cw.writerows(session['results'])
    output = make_response(line.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename={}.csv".format(session['filename'])
    output.headers["Content-type"] = "text/csv"
    return output
# [END CVS]

@app.errorhandler(500)
def server_error(e):
    logging.exception('An error occurred during a request.')
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500

if __name__ == '__main__':
    # This is used when running locally. Gunicorn is used to run the
    # application on Google App Engine. See entrypoint in app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)
# [END app]


