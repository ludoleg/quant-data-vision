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

from flask import Flask, request, render_template, session, make_response, redirect, flash
from werkzeug.utils import secure_filename

#Application modules
import qxrd
import qxrdtools

UPLOAD_DIR = 'uploads'
UPLOAD_FOLDER = UPLOAD_DIR

if not os.path.isdir(UPLOAD_DIR):
    os.mkdir(UPLOAD_DIR)

ALLOWED_EXTENSIONS = set(['txt', 'plv', 'csv', 'mdi', 'dif'])

    # [start config]
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'Ludo'

app.config['DEBUG'] = True

@app.route('/')
def hello():
    session['dbname'] = 'difdata-rockforming.txt'
    session['selected'] = phaselist.rockPhases
    session['available'] = phaselist.availablePhases
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/odr_demo')
def odr_demo():
    return render_template('odr_demo.html')

# [START process]
@app.route('/process', methods=['GET','POST'])
def process():
    if request.method == 'GET':
        inventory = request.args.get('dbinventory')
        # Unpack the selected inventory
        if inventory == "cement":
            # phaselistname = 'difdata_cement_inventory.csv'
            session['dbname'] ='difdata_cement.txt'
            session['selected'] = phaselist.cementPhases
            session['available'] = phaselist.availablePhases
        elif inventory == "pigment":
            # phaselistname = 'difdata_pigment_inventory.csv'
            session['dbname'] ='difdata_pigment.txt'
            session['selected'] = phaselist.pigmentPhases
            session['available'] = phaselist.availablePhases
        elif inventory == "rock":
            # phaselistname = 'difdata-rockforming_inventory.csv'
            session['dbname'] ='difdata-rockforming.txt'
            session['selected'] = phaselist.rockPhases
            session['available'] = phaselist.availablePhases
        elif inventory == "chemin":
            # phaselistname = 'difdata_CheMin_inventory.csv'
            session['dbname'] ='difdata_CheMin.txt'
            session['selected'] = phaselist.cheminPhases
            session['available'] = phaselist.availablePhases
        else:
            logging.critical("Can't find inventory")
        print session['dbname']

    if request.method == 'POST':
        uploaded_file = request.files['rockdatafile']
        if not uploaded_file:
            return 'No file uploaded.', 400

        # Load the sample data file in userData
        # parse sample data file wrt format
        filename = uploaded_file.filename
        session['filename'] = filename

        if uploaded_file and allowed_file(uploaded_file.filename):
            # Make a valid version of filename for any file ystem
            filename = secure_filename(uploaded_file.filename)
            uploaded_file.save(os.path.join(app.config['UPLOAD_FOLDER'],
                                   filename))
        else:
            return 'File not supported', 400

    # Load parameters for computation
    filename = session['filename']
    DBname = session['dbname']
    XRDdata = open(os.path.join('uploads', filename), 'r')
    # Phase selection
    selectedPhases = session['selected']
    # selectedPhases = phaselist.defaultPhases
    print selectedPhases
    # print(selectedPhases, file=sys.stderr)

    userData = qxrdtools.openXRD(XRDdata, filename)
    # print userData
    
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

    # Dif data captures all cristallographic data
    selectedphases = []
    for i in range (len(selectedPhases)):
        name, code = selectedPhases[i].split('\t')
        code = int(code)
        selectedphases.append((name,code))

    # Load in the DB file
    difdata = open(DBname, 'r').readlines()

    results, BG, calcdiff = qxrd.Qanalyze(userData, difdata, selectedphases, InstrParams)
    print results

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
    # session['results'] = results
    
    template_vars = {
        'phaselist': results,
        'angle': angle.tolist(),
        'diff': diff.tolist(),
        'bgpoly': bgpoly.tolist(),
        'sum': calcdiff.tolist(),
        'url_text': csv,
        'key': 'ludo',
        'samplename': filename,
        'mode': session['dbname']
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


# [START PHASE MANIP]
@app.route('/phaseAnalysis', methods=['GET'])
def phaseAnalysis():
    select = request.form.get('key')
    return select

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

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# def compute_mean_std(filename=None):
def compute_function(filename=None):
    data = np.loadtxt(os.path.join('uploads', filename))
    return """
Data from file <tt>%s</tt>:
<p>
<table border=1>
<tr><td> mean    </td><td> %.3g </td></tr>
<tr><td> st.dev. </td><td> %.3g </td></tr>
""" % (filename, np.mean(data), np.std(data))

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

# [START phase setting]
@app.route('/phase', methods=['GET', 'POST'])
def phase():
    if request.method == 'POST':
        selectedlist = request.form.getlist('selectedphase')
        availlist = request.form.getlist('availablephase')
        selectedlist.sort()
        availlist.sort()
        session['available'] = availlist
        session['selected'] = selectedlist
        return redirect('/process')
        # result = request.form.get()
        # return(str(selectedlist))
        # return render_template("result.html",result = result)
    else:
        # mode = QuantModeModel()
        # print(mode, file=sys.stderr)
        # session['mode'] = mode
        # session['selected'] = phaselist.defaultPhases
        template_vars = {
            'availablephaselist': session['available'],
            'selectedphaselist': session['selected'],
            'mode': session['dbname']
        }
        return render_template('phase.html', **template_vars)

    #    return "Total computation  time = %.2fs" %(time.time()-t0)
    #return_str = ''
    #return_str += 'results: {}<br />'.format(str(results))
    #return return_str

@app.route('/ludo')
def ludo():
    return render_template(
        'ludo.html',
        data=[{'name':'red'}, {'name':'green'}, {'name':'blue'}])

@app.route("/test" , methods=['GET', 'POST'])
def test():
    select = request.form.getlist('comp_select')
    return(str(select)) # just to see what select is
