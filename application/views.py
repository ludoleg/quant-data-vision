from flask import request, render_template, url_for, session, make_response, redirect, logging, json
from werkzeug.utils import secure_filename

from application import app

from flask_login import login_required

import numpy as np
import StringIO
import csv

import logging

# Application modules
import qxrd
import qxrdtools
import phaselist

from models import *
from users.views import users_blueprint

app.register_blueprint(users_blueprint)

ALLOWED_EXTENSIONS = set(['txt', 'plv', 'csv', 'mdi', 'dif'])
UPLOAD_DIR = 'uploads'

import os
app.config.from_object(os.environ['APP_SETTINGS'])
app.config['UPLOAD_FOLDER'] = UPLOAD_DIR

if not os.path.isdir(UPLOAD_DIR):
    os.mkdir(UPLOAD_DIR)


# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://localhost/qanalyze'

def rebalance(results):
    # Get the base list
    if session['dbname'] == 'difdata_cement.txt':
        db = phaselist.cementPhases
    elif session['dbname'] == 'difdata_pigment.txt':
        db = phaselist.pigmentPhases
    elif session['dbname'] == 'difdata-rockforming.txt':
        db = phaselist.rockPhases
    elif session['dbname'] == 'difdata_CheMin.txt':
        db = phaselist.cheminPhases

    available = []
    selected = [a[0] for a in results]
    inventory = [a.split('\t') for a in db]
    name = [a[0] for a in inventory]
    code = [a[1] for a in inventory]

    # for i in range(0, len(phaselist.rockPhases)):
    #     if selected[i] in phaselist.rockPhases[i]:
    #         print "yes"
    i = 0
    while i < len(name):
        if any(word in name[i] for word in selected):
            # print i, name[i]
            del name[i], code[i]
        else:
            i += 1

    for i in range(len(name)):
        available.append(name[i] + '\t' + code[i])

    selected = [a[0] + '\t' + str(a[1]) for a in results]
    selected.sort()
    available.sort()
    return selected, available


@app.route('/')
def home():
    session['dbname'] = 'difdata-rockforming.txt'
    session['selected'] = phaselist.rockPhases
    session['available'] = phaselist.availablePhases
    return render_template('index.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/modes', methods=['GET', 'POST'])
@login_required
def modes():
    if request.method == 'GET':
        myModes = db.session.query(Mode).all()
        # myModes = Mode.query.all()
        return render_template('modes.html', modes=myModes)
    if request.method == 'POST':
        modes_ids = request.form.getlist('mode_id', type=int)
        print modes_ids
        for id in modes_ids:
            m = Mode.query.get(id)
            db.session.delete(m)
        db.session.commit()
        return redirect(url_for('modes'))


@app.route('/phase', methods=['GET', 'POST'])
def phase():
    if request.method == 'POST':
        selectedlist = request.form.getlist('selectedphase')
        availlist = request.form.getlist('availablephase')
        selectedlist.sort()
        availlist.sort()
        session['available'] = availlist
        session['selected'] = selectedlist
        session['autoremove'] = False
        print '####### Inside Phase ####'
        # print session['selected']
        # print '####### Inside Phase ####'
        print session['available']
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
    # return_str = ''
    # return_str += 'results: {}<br />'.format(str(results))
    # return return_str


@app.route('/modes/create', methods=['GET', 'POST'])
def createmodes():
    if request.method == 'GET':
        return render_template('modesCreate.html')
    if request.method == 'POST':
        title = request.form['modeTitle']
        qlambda = request.form['lambda']
        target = request.form['target']
        fwhma = request.form['fwhma']
        fwhmb = request.form['fwhmb']
        inventory = request.form['inventory']
        mode = Mode(title, qlambda, target, fwhma,
                    fwhmb, inventory)
        db.session.add(mode)
        db.session.commit()
        return redirect(url_for('modes'))


@app.route('/modes/edit', methods=['GET', 'POST'])
def editmodes():
    if request.method == 'GET':
        id = request.args.get('id')
        myMode = Mode.query.get(id)
        return render_template('modesEdit.html', mode=myMode, key=id)
    if request.method == 'POST':
        print request.form
        id = request.form['key_id']
        myMode = Mode.query.get(id)
        myMode.title = request.form['name']
        myMode.qlambda = request.form['lambda']
        myMode.qtarget = request.form['target']
        myMode.fwhma = request.form['fwhma']
        myMode.fwhmb = request.form['fwhmb']
        myMode.inventory = request.form['inventory']
        db.session.commit()
    return redirect(url_for('modes'))


@app.route('/odr_demo')
def odr_demo():
    return render_template('odr_demo.html')


# [START process]
@app.route('/process', methods=['GET', 'POST'])
def process():
    if request.method == 'GET':
        inventory = request.args.get('dbinventory')
        # Unpack the selected inventory
        if inventory == "cement":
            # phaselistname = 'difdata_cement_inventory.csv'
            session['dbname'] = 'difdata_cement.txt'
            session['selected'] = phaselist.cementPhases
            session['available'] = phaselist.availablePhases
        elif inventory == "pigment":
            # phaselistname = 'difdata_pigment_inventory.csv'
            session['dbname'] = 'difdata_pigment.txt'
            session['selected'] = phaselist.pigmentPhases
            session['available'] = phaselist.availablePhases
        elif inventory == "rock":
            # phaselistname = 'difdata-rockforming_inventory.csv'
            session['dbname'] = 'difdata-rockforming.txt'
            session['selected'] = phaselist.rockPhases
            session['available'] = phaselist.availablePhases
        elif inventory == "chemin":
            # phaselistname = 'difdata_CheMin_inventory.csv'
            session['dbname'] = 'difdata_CheMin.txt'
            session['selected'] = phaselist.cheminPhases
            session['available'] = phaselist.availablePhases
        else:
            #            logging.critical("Can't find inventory")
            print "Can't find inventory"
        print session['dbname']

    if request.method == 'POST':
        uploaded_file = request.files['rockdatafile']
        if not uploaded_file:
            return 'No file uploaded.', 400

        # Load the sample data file in userData
        # parse sample data file wrt format
        filename = uploaded_file.filename
        session['filename'] = filename
        session['autoremove'] = True

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
    # print selectedPhases
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

    InstrParams = {"Lambda": Lambda, "Target": Target,
                   "FWHMa": FWHMa, "FWHMb": FWHMb}

    # Dif data captures all cristallographic data
    selectedphases = []
    for i in range(len(selectedPhases)):
        name, code = selectedPhases[i].split('\t')
        code = int(code)
        selectedphases.append((name, code))

    # Load in the DB file
    difdata = open(DBname, 'r').readlines()

    results, BG, calcdiff = qxrd.Qanalyze(
        userData, difdata, selectedphases, InstrParams, session['autoremove'], True)
    # print results, len(results)
    print len(BG)
    print len(calcdiff)
    # session['results'] = results
    sel, ava = rebalance(results)
    session['selected'] = sel
    session['available'] = ava

    # print(twoT.tolist(), file=sys.stderr)
    # print(userData, file=sys.stderr)

    twoT = userData[0]
    diff = userData[1]

    Sum = calcdiff
    difference_magnification = 1
    difference = (diff - Sum) * difference_magnification
    # print difference
    # logging.debug(results)
    # logging.info("Done with processing")

    angle = twoT
    # diff = diff
    bgpoly = BG
    # calcdiff = calcdiff
    # csv = session_data_key.urlsafe()
    csv = 'ODR'
    app.logger.warning('Length of angle array" %d', len(angle))

    template_vars = {
        'phaselist': results,
        'angle': angle.tolist(),
        'diff': diff.tolist(),
        'bgpoly': bgpoly.tolist(),
        'sum': calcdiff.tolist(),
        'difference': difference.tolist(),
        'url_text': csv,
        'key': 'ludo',
        'samplename': filename,
        'mode': session['dbname'],
        'availablephaselist': session['available'],
        'selectedphaselist': session['selected']
    }
    return render_template('chart.html', **template_vars)
# [END process]

# [START ODR service]


@app.route('/odr', methods=['GET', 'POST'])
def odr():
    if request.method == 'POST':
        # L oad data from request
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
        InstrParams = {"Lambda": 0, "Target": 'Co',
                       "FWHMa": 0.00, "FWHMb": 0.35}
        DBname = 'difdata_CheMin.txt'
        # Dif data captures all cristallographic data
        # Load in the DB file
        difdata = open(DBname, 'r').readlines()
        userData = (angle, diff)
        # print(userData)
        results, BG, calcdiff = qxrd.Qanalyze(
            userData, difdata, selectedphases, InstrParams)

        twoT = userData[0]
        diff = userData[1]

        # logging.debug(results)
        # logging.info("Done with processing")

        angle = twoT
        # diff = diff
        bgpoly = BG
        # calcdiff = calcdiff

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
@app.route('/phaseAnalysis', methods=['GET', 'POST'])
def phaseAnalysis():
    # select = request.form.get('key')
    # return select
    results = session['results']
    sel, ava = reformat(results)
    session['selected'] = sel
    session['available'] = ava
    template_vars = {
        'availablephaselist': session['available'],
        'selectedphaselist': session['selected'],
        'mode': session['dbname']
    }
    return render_template('selector.html', **template_vars)

    # return render_template('selector.html')

# [START CVS]


@app.route('/csvDownload', methods=['GET'])
def csvDownload():
    line = StringIO.StringIO()
    cw = csv.writer(line)
    cw.writerow(['Mineral', 'AMCSD', 'Mass %'])
    cw.writerows(session['results'])
    output = make_response(line.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename={}.csv".format(
        session['filename'])
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


# [START phase setting]


@app.route('/ludo')
def ludo():
    return render_template(
        'ludo.html',
        data=[{'name': 'red'}, {'name': 'green'}, {'name': 'blue'}])


@app.route("/test", methods=['GET', 'POST'])
def test():
    select = request.form.getlist('comp_select')
    return(str(select))  # just to see what select is


def reformat(results):
    selected = [a[0] for a in results]
    available = []
    db = session['selected']

    # print selected
    # inventory = phaselist.rockPhasesj
    # print inventory
    inventory = [a.split('\t') for a in db]
    name = [a[0] for a in inventory]
    code = [a[1] for a in inventory]

    # for i in range(0, len(phaselist.rockPhases)):
    #     if selected[i] in phaselist.rockPhases[i]:
    #         print "yes"
    i = 0
    while i < len(name):
        if any(word in name[i] for word in selected):
            # print i, name[i]
            del name[i], code[i]
        i += 1

    for i in range(len(name)):
        available.append(name[i] + '\t' + code[i])

    # selected = [name+code for a in name]

    # selected = [name[0]+'\t'+str(a[1]) for a in results]
    # selected = [(name, code) for a in name]
    # print available
    # print selected
    selected = [a[0] + '\t' + str(a[1]) for a in results]
    # print selected, available
    return selected, available


def cleanup(results):
    selected = [a[0] + '\t' + str(a[1]) for a in results]
    return selected
