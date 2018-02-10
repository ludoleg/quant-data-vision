from flask import request, render_template, url_for, session, make_response, redirect, logging, json, flash
from werkzeug.utils import secure_filename
from flask_wtf import FlaskForm
from wtforms import FileField
from flask_wtf.file import FileField, FileRequired, FileAllowed

from flask_login import login_required, current_user

from application import app

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
defaultMode = Mode('Default', 0, 'Co', 0, 0.3, 'rockforming', None, None)


def before_request():
    app.jinja_env.cache = {}


@app.context_processor
def inject_title():
    # app.logger.warning(session)
    if current_user.is_authenticated:
        if 'mode' in session:
            mode = Mode.query.get(session['mode'])
            title = mode.title
        else:
            app.logger.info('No mode has been initialized')
            mode = db.session.query(Mode).filter_by(
                author_id=current_user.id).first()
            if mode:
                session['mode'] = mode.id
                app.logger.info('Mode has been initialized')
                title = mode.title
            else:
                title = ''
    else:
        app.logger.info('Anonymous mode')
        title = ''
    return dict(modetitle=title)


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
    elif session['dbname'] == 'difdata_rockforming.txt':
        db = phaselist.rockPhases
    elif session['dbname'] == 'difdata_chemin.txt':
        db = phaselist.cheminPhases

    app.logger.debug('Rebalance: dbname % s', session['dbname'])

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

    selected = [a[0] + '\t' + str(a[1]).zfill(6) for a in results]
    selected.sort()
    available.sort()
    app.logger.debug("*********** Rebalance ** *********")
    app.logger.debug("Inventory %s", inventory)
    app.logger.debug("Selected %s", selected)
    app.logger.debug("Available %s", available)
    return selected, available


class UploadForm(FlaskForm):
    file = FileField('File format', validators=[FileRequired(), FileAllowed(
        ['txt', 'plv', 'csv', 'mdi', 'dif'], 'Only XRD files format such as .plv, .mdi, .csv, etc are accepted.')])


@app.route('/about')
def about():
    return render_template('about.html')

# This will reset the starting line up for the phases


@login_required
@app.route('/setphase', methods=['GET', 'POST'])
def setphase():
    if request.method == 'POST':
        modeid = request.form['modeid']
        mode = Mode.query.get(modeid)
        selectedlist = request.form.getlist('selectedphase')
        availlist = request.form.getlist('availablephase')
        selectedlist.sort()
        availlist.sort()
        mode.initial = selectedlist
        db.session.flush()
        db.session.commit()
        session['autoremove'] = True
        app.logger.warning("Mode.initial: %s", mode.initial)
        return redirect('/')
    if request.method == 'GET':
        mode = Mode.query.get(session['mode'])
        ava = rebal(mode.initial, mode.inventory)
        # if session['mode']:
        #     mode = Mode.query.get(session['mode'])
        # else:
        #     mode = db.session.query(Mode).filter_by(
        #         author_id=current_user.id).first()
        #     if mode is None:
        #         flash('Please create a mode!')
        #         return redirect('modes')
        #     else:
        #         flash('Please select a mode!')
        #         return redirect('activeMode')
        app.logger.debug("Mode id : %s", mode.id)
        app.logger.debug("Mode initial : %s", mode.initial)
        # ava = rebal(session['selected'], mode.inventory)
        # This will reset the starting line up for the phases
        session['autoremove'] = True
        template_vars = {
            'availablephaselist': ava,
            'selectedphaselist': mode.initial,
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
            # phaselistname = 'difdata_rockforming_inventory.csv'
            session['dbname'] = 'difdata_rockforming.txt'
            session['selected'] = []
            phaselist.rockPhases.sort()
            session['available'] = phaselist.rockPhases
        elif inventory == "chemin":
            # phaselistname = 'difdata_chemin_inventory.csv'
            session['dbname'] = 'difdata_chemin.txt'
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
        # print modes_ids
        for id in modes_ids:
            if('mode' in session and session['mode'] == id):
                session.pop('mode')
                m = Mode.query.get(id)
                db.session.delete(m)
                db.session.commit()
        return redirect(url_for('modes'))


@login_required
@app.route('/modes/create', methods=['GET', 'POST'])
def createmodes():
    if request.method == 'GET':
        return render_template('modesCreate.html')
    if request.method == 'POST':
        # print current_user.id
        # print current_user.name
        title = request.form['modeTitle']
        qlambda = request.form['lambda']
        target = request.form['target']
        fwhma = request.form['fwhma']
        fwhmb = request.form['fwhmb']
        inventory = request.form['inventory']
        # populate initial list
        if inventory == "cement":
            initial = sorted(phaselist.cementPhases)
        elif inventory == "pigment":
            initial = sorted(phaselist.pigmentPhases)
        elif inventory == "rockforming":
            initial = sorted(phaselist.rockPhases)
        elif inventory == "chemin":
            initial = sorted(phaselist.cheminPhases)
        else:
            #            logging.critical("Can't find inventory")
            app.logger.error("Can't find inventory")

        mode = Mode(title, qlambda, target, fwhma,
                    fwhmb, inventory, initial, current_user.id)
        db.session.add(mode)
        db.session.commit()
        if 'mode' not in session:
            session['mode'] = mode.id
        return redirect(url_for('modes'))


@login_required
@app.route('/modes/edit', methods=['GET', 'POST'])
def editmodes():
    if request.method == 'GET':
        id = request.args.get('id')
        myMode = Mode.query.get(id)
        return render_template('modesEdit.html', mode=myMode, key=id)
    if request.method == 'POST':
        # print request.form
        id = request.form['key_id']
        myMode = Mode.query.get(id)
        myMode.title = request.form['name']
        myMode.qlambda = request.form['lambda']
        myMode.qtarget = request.form['target']
        myMode.fwhma = request.form['fwhma']
        myMode.fwhmb = request.form['fwhmb']
        inventory = request.form['inventory']
        old = request.form['oldinventory']
        if old != inventory:
            # print request.form['inventory'], old
            myMode.inventory = inventory
            if inventory == "cement":
                initial = sorted(phaselist.cementPhases)
            elif inventory == "pigment":
                initial = sorted(phaselist.pigmentPhases)
            elif inventory == "rockforming":
                initial = sorted(phaselist.rockPhases)
            elif inventory == "chemin":
                initial = sorted(phaselist.cheminPhases)
                myMode.initial = initial
                db.session.commit()
    return redirect(url_for('modes'))


@login_required
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
        clearModeCtx()
        mode_id = request.form['mode']
        mode = Mode.query.get(mode_id)
        session['mode'] = mode_id
        # print mode_id, mode.id, session
        return redirect('/')
    if request.method == 'GET':
        myModes = db.session.query(Mode).filter_by(author_id=current_user.id)
        current_mode = Mode.query.get(session['mode'])
        return render_template('activeMode.html', modes=myModes, current_mode=current_mode)


@app.route('/odr_ajax')
def odr_demo():
    return render_template('odr_ajax.html')


@app.route('/odr_post')
def odr_post():
    return render_template('odr_post.html')


def qxrd_worker(userData):
    angle = userData[0]
    diff = userData[1]

    # defaultMode = Mode('Default', 0, 'Co', 0, 0.3, 'rockforming', None, None)
    app.logger.debug(session)
    app.logger.warning('Length of angle array: %d', len(angle))

    # Load inventory
    DBname = session['dbname']
    difdata = open(DBname, 'r').readlines()

    # Mode
    myMode = defaultMode
    Lambda = myMode.qlambda
    Target = myMode.qtarget
    FWHMa = myMode.fwhma
    FWHMb = myMode.fwhmb

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

    InstrParams = {"Lambda": Lambda,
                   "Target": Target,
                   "FWHMa": FWHMa,
                   "FWHMb": FWHMb}

    # Phase selection
    selectedPhases = session['selected']
    selectedphases = []
    for i in range(len(selectedPhases)):
        name, code = selectedPhases[i].split('\t')
        code = int(code)
        selectedphases.append((name, code))

    results, BG, Sum, mineralpatterns = qxrd.Qanalyze(userData,
                                                      difdata,
                                                      selectedphases,
                                                      InstrParams,
                                                      session['autoremove'],
                                                      True)

    session['results'] = results
    sel, ava = rebalance(results)
    session['selected'] = sel

    minerallist = [(l + BG).tolist() for l in mineralpatterns]
    print len(minerallist)

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

    # Serialize the entire thing
    result = dict()
    result['traces'] = minerallist
    result['phases'] = results
    result['background'] = BG.tolist()
    result['fit'] = Sum.tolist()
    result['difference'] = offsetdiff.tolist()
    result['selected'] = sel  # session['selected']
    result['ava'] = ava

    return result


@app.route('/', methods=['GET', 'POST'])
def home():
    modeset = False
    if current_user.is_authenticated:
        mode = db.session.query(Mode).filter_by(
            author_id=current_user.id).first()
        if mode:
            modeset = True
            # app.logger.warning(session)

    form = UploadForm()

    if form.validate_on_submit():
        f = form.file.data
        filename = secure_filename(f.filename)
        f.save(os.path.join(app.config['UPLOAD_FOLDER'],
                            filename))
        session['filename'] = filename
        return redirect(url_for('chart'))
    print form.errors
    return render_template('index.html', form=form, mode=modeset)


@app.route('/chart', methods=['GET', 'POST'])
def chart():
    clearModeCtx()
    loadModeCtx()
    # Load parameters for computation
    filename = session['filename']
    XRDdata = open(os.path.join('uploads', filename), 'r')
    userData = qxrdtools.openXRD(XRDdata, filename)
    angle = userData[0]
    diff = userData[1]

    ava = rebal(session['selected'], 'rockforming')
    defaultMode = Mode('Default', 0, 'Co', 0, 0.3, 'rockforming', None, None)

    template_vars = {
        'angle': angle.tolist(),
        'diff': diff.tolist(),
        'samplename': filename,
        'mode': defaultMode,
        'availablephaselist': ava,
        'selectedphaselist': session['selected']

    }
    return render_template('chart2.html', **template_vars)


@app.route('/compute', methods=['GET', 'POST'])
def compute():
    if request.method == 'POST':
        # print request.__dict__
        # Load data from request
        # Ajax case
        if request.is_json:
            json_data = request.get_json()
            plotdata = json_data
            # Regular post, text/plain encoded in body
        else:
            print 'Not a json request'
        print plotdata
        data = plotdata['data']
        sample = data['sample']
        filename = sample['name']
        print filename
        phasearray = sample['phases']
        # selectedphases = [(d['name'], d['AMCSD_code']) for d in phasearray]
        print phasearray

        x = sample['x']
        y = sample['y']
        angle = np.asfarray(np.array(x))
        diff = np.asfarray(np.array(y))
        userData = (angle, diff)

        result = qxrd_worker(userData)

        return json.dumps(result)
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

    cheminMode = Mode('DefaultChemin', 0, 'Co', 0, 0, 'chemin', None, None)

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
        'mode': cheminMode,
        'availablephaselist': session['available'],
        'selectedphaselist': session['selected']
    }
    return render_template('chart.html', **template_vars)
# [END process]


def clearModeCtx():
    session.pop('dbname', None)
    session.pop('selected', None)
    session.pop('autoremove', None)
    session.pop('results', None)


def loadModeCtx():
    session['autoremove'] = True
    if current_user.is_authenticated:
        if 'mode' in session:
            mode = Mode.query.get(session['mode'])
        else:
            # No mode has been selected yet - should all be replaced by a function activatemode
            mode = db.session.query(Mode).filter_by(
                author_id=current_user.id).first()
            # print mode.initial
        session['mode'] = mode.id
        session['selected'] = mode.initial
        session['dbname'] = 'difdata_' + mode.inventory + '.txt'
    else:
        # anonymous flow
        inventory = defaultMode.inventory
        session['dbname'] = 'difdata_' + inventory + '.txt'
        session['selected'] = phaselist.rockPhases
        # app.logger.warning("loadModeCtx session['selected']: % s", session['selected'])
        print session

# [START process]


@app.route('/process', methods=['GET', 'POST'])
def process():
    if current_user.is_authenticated:
        app.logger.warning('User:{}'.format(current_user.name))

    app.logger.warning('File:{}'.format(session['filename']))
    # Need to reset to initial as we are dealing with new file
    app.logger.debug(session)

    # Mode setup
    if 'mode' in session:
        myMode = Mode.query.get(session['mode'])
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
    # print XRDdata, filename

    DBname = session['dbname']
    # Load in the DB file
    difdata = open(DBname, 'r').readlines()

    # Phase selection
    selectedPhases = session['selected']

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

    # print session
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
    # session['available'] = ava

    # print(twoT.tolist(), file=sys.stderr)
    # print(userData, file=sys.stderr)

    twoT = userData[0]
    diff = userData[1]
    angle = twoT
    bgpoly = BG

    xmin = min(angle)
    xmax = max(angle)
    Imax = max(diff[min(np.where(np.array(angle) > 15)[0])                    :max(np.where(np.array(angle) > xmin)[0])])
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
        'availablephaselist': ava,
        'selectedphaselist': session['selected']
    }
    return render_template('chart.html', **template_vars)
# [END process]


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

# [START CSV]


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
