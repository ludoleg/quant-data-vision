from flask import request, render_template, url_for, session, make_response, redirect, logging, json, flash
from werkzeug.utils import secure_filename

from application import app

from flask_login import login_required, current_user

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


def rebal(selected, inventory):
    if inventory == "cement":
        db = sorted(phaselist.cementPhases)
    elif inventory == "pigment":
        db = sorted(phaselist.pigmentPhases)
    elif inventory == "rockforming":
        db = sorted(phaselist.rockPhases)
    elif inventory == "chemin":
        db = sorted(phaselist.cheminPhases)
    selected.sort()
    available = [x for x in db if x not in selected]
    app.logger.debug(available)
    return available


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

    app.logger.debug('Rebalance: dbname % s', session['dbname'])

    available = []
    selected = [a[0] for a in results]
    inventory = [a.split('\t') for a in db]
    name = [a[0] for a in inventory]
    code = [a[1] for a in inventory]
    app.logger.debug(inventory)

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

    selected = [a[0] + '\t' + str(a[1]).zfill(6) for a in results]
    selected.sort()
    available.sort()
    app.logger.debug(selected)
    # app.logger.debug(available)
    return selected, available


@app.route('/')
def home():
    # session['dbname'] = 'difdata-rockforming.txt'
    # session['selected'] = phaselist.rockPhases
    # session['available'] = phaselist.availablePhases

    if not session.has_key('mode'):
        session['mode'] = None
        # None = default mode
        # if session.has_key('mode'):
        #    app.logger.warning("Session['mode']: %s", session['mode'])
    app.logger.debug(session)
    return render_template('index.html')


@app.route('/about')
def about():
    return render_template('about.html')

# This will reset the starting line up for the phases


@app.route('/setphase', methods=['GET', 'POST'])
def setphase():
    if request.method == 'POST':
        selectedlist = request.form.getlist('selectedphase')
        availlist = request.form.getlist('availablephase')
        selectedlist.sort()
        availlist.sort()
        session['available'] = availlist
        session['initial'] = selectedlist
        session['autoremove'] = True
        app.logger.warning("session['initial']: %s", session['initial'])
        return redirect('/')
    if request.method == 'GET':
        if session['mode']:
            mode = Mode.query.get(session['mode'])
        else:
            mode = db.session.query(Mode).filter_by(
                author_id=current_user.id).first()
            if mode is None:
                flash('Please create a mode!')
                return redirect('modes')
            else:
                flash('Please select a mode!')
                return redirect('activeMode')
        app.logger.debug("Inventory: %s", mode.inventory)
        # ava = rebal(session['selected'], mode.inventory)
        # This will reset the starting line up for the phases
        session['autoremove'] = True
        ava = rebal([], mode.inventory)
        template_vars = {
            'availablephaselist': '',
            'selectedphaselist': ava,
            'mode': mode
        }
    return render_template('setphase.html', **template_vars)


@app.route('/phase', methods=['GET', 'POST'])
def phase():
    if request.method == 'POST':
        session['autoremove'] = False
        selectedlist = request.form.getlist('selectedphase')
        availlist = request.form.getlist('availablephase')
        selectedlist.sort()
        availlist.sort()
        session['available'] = availlist
        session['selected'] = selectedlist
        print '####### Inside Phase ####'
        print session['selected']
        # print '####### Inside Phase ####'
        # print session['available']
        # app.logger.warning('Session[chemin]: %s', session['chemin'])
        if session.has_key('chemin'):
            app.logger.warning("Session['chemin']: %s", session['chemin'])
            # if session['chemin']:
            return redirect('/chemin_process')
        else:
            return redirect('/process')
        # result = request.form.get()
        # return(str(selectedlist))
        # return render_template("result.html",result = result)
    else:
        if session['mode']:
            mode = Mode.query.get(session['mode'])
            inventory = mode.inventory
        else:
            inventory = 'rockforming'

        if inventory == "cement":
            # phaselistname = 'difdata_cement_inventory.csv'
            session['dbname'] = 'difdata_cement.txt'
            session['selected'] = []
            phaselist.cementPhases.sort()
            session['available'] = phaselist.cementPhases
        elif inventory == "pigment":
            # phaselistname = 'difdata_pigment_inventory.csv'
            session['dbname'] = 'difdata_pigment.txt'
            session['selected'] = []
            phaselist.pigmentPhases.sort()
            session['available'] = phaselist.pigmentPhases
        elif inventory == "rockforming":
            # phaselistname = 'difdata-rockforming_inventory.csv'
            session['dbname'] = 'difdata-rockforming.txt'
            session['selected'] = []
            phaselist.rockPhases.sort()
            session['available'] = phaselist.rockPhases
        elif inventory == "chemin":
            # phaselistname = 'difdata_CheMin_inventory.csv'
            session['dbname'] = 'difdata_CheMin.txt'
            session['selected'] = []
            phaselist.cheminPhases.sort()
            session['available'] = phaselist.cheminPhases
        else:
            #            logging.critical("Can't find inventory")
            app.logger.error("Can't find inventory")

        # mode = QuantModeModel()
        # print(mode, file=sys.stderr)
        # session['mode'] = mode
        # session['selected'] = phaselist.defaultPhases
        template_vars = {
            'availablephaselist': session['available'],
            'selectedphaselist': session['selected'],
            'mode': mode
        }
        return render_template('phase.html', **template_vars)

    #    return "Total computation  time = %.2fs" %(time.time()-t0)
    # return_str = ''
    # return_str += 'results: {}<br />'.format(str(results))
    # return return_str


@app.route('/modes', methods=['GET', 'POST'])
@login_required
def modes():
    if request.method == 'GET':
        # myModes = db.session.query(Mode).filter(Mode.author_id == current_user.id)
        myModes = db.session.query(Mode).filter_by(author_id=current_user.id)
        # myModes = db.session.query(Mode).all()
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


@app.route('/modes/create', methods=['GET', 'POST'])
def createmodes():
    if request.method == 'GET':
        return render_template('modesCreate.html')
    if request.method == 'POST':
        print current_user.id
        print current_user.name
        title = request.form['modeTitle']
        qlambda = request.form['lambda']
        target = request.form['target']
        fwhma = request.form['fwhma']
        fwhmb = request.form['fwhmb']
        inventory = request.form['inventory']
        mode = Mode(title, qlambda, target, fwhma,
                    fwhmb, inventory, current_user.id)
        db.session.add(mode)
        db.session.commit()
        session['mode'] = mode.id
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


@app.route('/activeMode', methods=['GET', 'POST'])
def active_mode():
    if request.method == 'POST':
        # dict = request.form
        # for key in dict:
        #     print key
        #     print 'form key ' + dict[key]
        # multi_dict = request.args
        # for key in multi_dict:
        #     print multi_dict.get(key)
        #     print multi_dict.getlist(key)
        mode_id = request.form['mode']
        mode = Mode.query.get(mode_id)
        session['mode'] = mode_id

        # Assign DB
        inventory = mode.inventory
        # Unpack the selected inventory
        if inventory == "cement":
            # phaselistname = 'difdata_cement_inventory.csv'
            session['dbname'] = 'difdata_cement.txt'
            session['initial'] = phaselist.cementPhases
            session['available'] = phaselist.availablePhases
        elif inventory == "pigment":
            # phaselistname = 'difdata_pigment_inventory.csv'
            session['dbname'] = 'difdata_pigment.txt'
            session['initial'] = sorted(phaselist.pigmentPhases)
            session['available'] = phaselist.availablePhases
        elif inventory == "rockforming":
            # phaselistname = 'difdata-rockforming_inventory.csv'
            session['dbname'] = 'difdata-rockforming.txt'
            session['initial'] = phaselist.rockPhases
            session['available'] = phaselist.availablePhases
        elif inventory == "chemin":
            # phaselistname = 'difdata_CheMin_inventory.csv'
            session['dbname'] = 'difdata_CheMin.txt'
            session['initial'] = phaselist.cheminPhases
            session['available'] = phaselist.availablePhases
        else:
            #            logging.critical("Can't find inventory")
            app.logger.error("Can't find inventory")
        app.logger.warning("session['intial'], % s", session['initial'])
        return redirect('/')
    if request.method == 'GET':
        myModes = db.session.query(Mode).filter_by(author_id=current_user.id)
        return render_template('activeMode.html', modes=myModes, title=ludo)


@app.route('/odr_demo')
def odr_demo():
    return render_template('odr_demo.html')


@app.route('/odr_post')
def odr_post():
    return render_template('odr_post.html')


# [START ODR service]
# Duplicates /processwith input from the ODR site
@app.route('/chemin', methods=['GET', 'POST'])
def chemin():
    if request.method == 'POST':
        # print request.__dict__
        # Load data from request
        # Ajax case
        if request.is_json:
            json_data = request.get_json()
            data = json_data
        # Regular post, text/plain encoded in body
        else:
            # Regular post x-www-form-urlencoded
            dsample = request.form['data']
            data = json.loads(dsample)
            # Other type of encoding via text/plain
            # a, b = request.data.split('=')
            # data = json.loads(b)

        sample = data['sample']
        filename = sample['name']
        array = sample['data']
        odr_phases = data['phases']
        app.logger.warning('Size of ODR array: %d', len(array))
        app.logger.debug(sample)
        app.logger.warning('Size of ODR phases: %d', len(odr_phases))
        app.logger.warning('ODR Phases: %s', odr_phases)

        # Save to file
        with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), 'w') as outfile:
            json.dump(array, outfile)

        app.logger.warning('Filename: %s', filename)

        # Initialize the session object with chemin data
        session['autoremove'] = False
        session['dbname'] = 'difdata_CheMin.txt'
        session['selected'] = phaselist.cheminPhases
        session['available'] = phaselist.availablePhases
        session['filename'] = filename
        session['chemin'] = True

        x = [li['x'] for li in array]
        y = [li['y'] for li in array]

        angle = np.asfarray(np.array(x))
        diff = np.asfarray(np.array(y))

        # Force mode
        Lambda = 0.0
        Target = 'Co'
        FWHMa = 0.0
        FWHMb = 0.35
        InstrParams = {"Lambda": Lambda,
                       "Target": Target,
                       "FWHMa": FWHMa,
                       "FWHMb": FWHMb}

        # Parse phases sent by ODR
        phasearray = data['phases']
        selectedphases = [(d['name'], d['AMCSD_code']) for d in phasearray]
        # TODO 2nd pass with selected

        # Force Chemin for ODR
        # Dif data captures all cristallographic data
        # Load in the DB file
        DBname = session['dbname']
        difdata = open(DBname, 'r').readlines()
        userData = (angle, diff)
        # results, BG, calcdiff = qxrd.Qanalyze(userData,
        results, BG, Sum, mineralpatterns = qxrd.Qanalyze(userData,
                                                          difdata,
                                                          selectedphases,
                                                          InstrParams,
                                                          session['autoremove'],
                                                          True)

        # Re-create the subset of phases to select
        sel, ava = rebalance(results)
        session['selected'] = sel
        session['available'] = ava
        # print(twoT.tolist(), file=sys.stderr)
        # print(userData, file=sys.stderr)

        twoT = userData[0]
        diff = userData[1]
        angle = twoT
        bgpoly = BG
        xmin = min(angle)
        xmax = max(angle)
        # xmax = max(angle)
        Imax = max(diff[min(np.where(np.array(angle) > xmin)[0])
                   :max(np.where(np.array(angle) > xmin)[0])])
        offset = Imax / 2 * 3
        offsetline = [offset] * len(angle)

        difference_magnification = 1
        difference = (diff - Sum) * difference_magnification
        # logging.debug(results)
        # logging.info("Done with processing")
        offsetdiff = difference + offset

        csv = 'ODR'
        app.logger.warning('Length of angle array: %d', len(angle))
        minerallist = [(l + BG).tolist() for l in mineralpatterns]

        session['results'] = results
        session['filename'] = filename

        defaultMode = Mode('DefaultChemin', 0, 'Co', 0, 0, 'chemin', None)

        template_vars = {
            'phaselist': results,
            'angle': angle.tolist(),
            'diff': diff.tolist(),
            'bgpoly': bgpoly.tolist(),
            'sum': Sum.tolist(),
            'difference': offsetdiff.tolist(),
            'minerals': minerallist,
            'url_text': csv,
            'key': 'chemin',
            'samplename': filename,
            'mode': defaultMode,
            'availablephaselist': session['available'],
            'selectedphaselist': session['selected']
        }
        return render_template('chart.html', **template_vars)
    else:
        return '''<html><body><h1>Did not get a post!</h1></body></html>'''
# [END ODR service]

# [START odr second pass process, this is run when the user changes the phases and relaunch after the chemin call]


@app.route('/chemin_process', methods=['GET'])
def chemin_process():
    # Load parameters for computation
    filename = session['filename']

    # Extract angle, diff to populate userData
    with open(os.path.join(app.config['UPLOAD_FOLDER'], filename)) as infile:
        array = json.load(infile)
    x = [li['x'] for li in array]
    y = [li['y'] for li in array]
    angle = np.asfarray(np.array(x))
    diff = np.asfarray(np.array(y))

    # Force mode
    Lambda = 0.0
    Target = 'Co'
    FWHMa = 0.0
    FWHMb = 0.35
    InstrParams = {"Lambda": Lambda,
                   "Target": Target,
                   "FWHMa": FWHMa,
                   "FWHMb": FWHMb}

    # Phase selection
    selectedPhases = session['selected']
    # Dif data captures all cristallographic data
    selectedphases = []
    for i in range(len(selectedPhases)):
        name, code = selectedPhases[i].split('\t')
        code = int(code)
        selectedphases.append((name, code))

    # Load in the DB file
    DBname = session['dbname']
    difdata = open(DBname, 'r').readlines()
    userData = (angle, diff)
    results, BG, Sum, mineralpatterns = qxrd.Qanalyze(userData,
                                                      difdata,
                                                      selectedphases,
                                                      InstrParams,
                                                      session['autoremove'],
                                                      True)

    # Re-create the subset of phases to select
    sel, ava = rebalance(results)
    session['selected'] = sel
    session['available'] = ava
    # print(twoT.tolist(), file=sys.stderr)
    # print(userData, file=sys.stderr)

    twoT = userData[0]
    diff = userData[1]
    angle = twoT
    bgpoly = BG
    xmin = min(angle)
    xmax = max(angle)
    Imax = max(diff[min(np.where(np.array(angle) > xmin)[0]):max(np.where(np.array(angle) > xmin)[0])])
    offset = Imax / 2 * 3
    offsetline = [offset] * len(angle)

    difference_magnification = 1
    difference = (diff - Sum) * difference_magnification
    # logging.debug(results)
    # logging.info("Done with processing")
    offsetdiff = difference + offset

    csv = 'ODR'
    app.logger.warning('Length of angle array: %d', len(angle))
    minerallist = [(l + BG).tolist() for l in mineralpatterns]

    session['results'] = results

    defaultMode = Mode('DefaultChemin', 0, 'Co', 0, 0, 'chemin', None)

    template_vars = {
        'phaselist': results,
        'angle': angle.tolist(),
        'diff': diff.tolist(),
        'bgpoly': bgpoly.tolist(),
        'sum': Sum.tolist(),
        'difference': offsetdiff.tolist(),
        'minerals': minerallist,
        'url_text': csv,
        'key': 'chemin',
        'samplename': filename,
        'mode': defaultMode,
        'availablephaselist': session['available'],
        'selectedphaselist': session['selected']
    }
    return render_template('chart.html', **template_vars)
# [END process]

# [START process]


def InitPhases(inventory):
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
    elif inventory == "rockforming":
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
        app.logger.error("Can't find inventory")
    app.logger.warning("Initphases DBname: %s", session['dbname'])


@app.route('/process', methods=['GET', 'POST'])
def process():
    # if request.method == 'GET':
    defaultMode = Mode('Default', 0, 'Co', 0, 0.35, 'rockforming', None)
    if request.method == 'POST':
        uploaded_file = request.files['rockdatafile']
        if not uploaded_file:
            return 'No file uploaded.', 400

        # Load the sample data file in userData
        # parse sample data file wrt format
        filename = uploaded_file.filename

        session['autoremove'] = True

        # Need to reset to initial as we are dealing with new file
        if session['mode'] is None:
            # Default case
            inventory = defaultMode.inventory
            InitPhases(inventory)
        else:
            session['selected'] = session['initial']

        if uploaded_file and allowed_file(uploaded_file.filename):
            # Make a valid version of filename for any file ystem
            filename = secure_filename(uploaded_file.filename)
            uploaded_file.save(os.path.join(app.config['UPLOAD_FOLDER'],
                                            filename))
            session['filename'] = filename
        else:
            return 'File not supported', 400

    app.logger.debug(session)

    # Mode setup
    mode_id = session['mode']
    if mode_id:
        myMode = Mode.query.get(mode_id)
    else:
        myMode = defaultMode

    Lambda = myMode.qlambda
    Target = myMode.qtarget
    FWHMa = myMode.fwhma
    FWHMb = myMode.fwhmb
    title = myMode.title
    app.logger.info("Mode: %s", myMode)

    # Load parameters for computation
    filename = session['filename']

    XRDdata = open(os.path.join('uploads', filename), 'r')

    DBname = session['dbname']
    # Load in the DB file
    difdata = open(DBname, 'r').readlines()

    # Phase selection
    selectedPhases = session['selected']
    app.logger.warning("session['selected']: % s", session['selected'])
    # selectedPhases = phaselist.defaultPhases
    # print selectedPhases
    # print(selectedPhases, file=sys.stderr)
    userData = qxrdtools.openXRD(XRDdata, filename)
    # print userData

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

    app.logger.warning("Size of selected before QAnalyze: %d",
                       len(selectedphases))
    # results, BG, calcdiff = qxrd.Qanalyze(
    results, BG, Sum, mineralpatterns = qxrd.Qanalyze(
        userData, difdata, selectedphases, InstrParams, session['autoremove'], True)
    app.logger.warning("Length of mineralpatterns: %d",  len(mineralpatterns))
    # print results, len(results)
    app.logger.debug("Length of BG array: %s", len(BG))
    session['results'] = results
    sel, ava = rebalance(results)
    session['selected'] = sel
    app.logger.debug(sel)
    session['available'] = ava

    # print(twoT.tolist(), file=sys.stderr)
    # print(userData, file=sys.stderr)

    twoT = userData[0]
    diff = userData[1]
    angle = twoT
    bgpoly = BG

    xmin = min(angle)
    xmax = max(angle)
    Imax = max(diff[min(np.where(np.array(angle) > 15)[0])
               :max(np.where(np.array(angle) > xmin)[0])])
    offset = Imax / 2 * 3
    offsetline = [offset] * len(angle)

    difference_magnification = 1
    difference = (diff - Sum) * difference_magnification

    offsetdiff = difference + offset
    # print difference
    app.logger.warning(results)
    app.logger.debug("Done with processing")

    minerallist = [(l + BG).tolist() for l in mineralpatterns]
    # print u'\u03B8' Theta

    # calcdiff = calcdiff
    # csv = session_data_key.urlsafe()
    csv = 'ODR'
    app.logger.warning('Length of angle array: %d', len(angle))

    template_vars = {
        'phaselist': results,
        'angle': angle.tolist(),
        'diff': diff.tolist(),
        'bgpoly': bgpoly.tolist(),
        'sum': Sum.tolist(),
        'difference': offsetdiff.tolist(),
        'minerals': minerallist,
        'url_text': csv,
        'key': 'ludo',
        'samplename': filename,
        'mode': myMode,
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
    print current_user
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
