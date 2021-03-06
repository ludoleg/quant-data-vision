from flask import request, render_template, url_for, session, make_response, redirect, logging, json, flash, g, jsonify, abort
from werkzeug.utils import secure_filename
from flask_wtf import FlaskForm
from wtforms import FileField, ValidationError
from flask_wtf.file import FileField, FileRequired, FileAllowed

from flask_login import login_required, current_user
from marshmallow import Schema, pprint


from application import app

import numpy as np
import StringIO
import csv

import logging

# Application modules
import qxrd
import qxrdtools
import phaselist

from models import Mode, ModeSchema, db
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
defaultMode = Mode('Default', 0, 'Co', 0, 0.3, 'rockforming')


def before_request():
    app.jinja_env.cache = {}


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
    if 'mode' in session:
        mode = Mode.query.get(session['mode'])
    else:
        mode = defaultMode
    DBname = 'difdata_' + mode.inventory + '.txt'

    if DBname == 'difdata_cement.txt':
        db = phaselist.cementPhases
    elif DBname == 'difdata_pigment.txt':
        db = phaselist.pigmentPhases
    elif DBname == 'difdata_rockforming.txt':
        db = phaselist.rockPhases
    elif DBname == 'difdata_chemin.txt':
        db = phaselist.cheminPhases

    app.logger.debug('Rebalance: dbname % s', DBname)

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


@app.route('/setphase', methods=['GET', 'POST'])
@login_required
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
        app.logger.warning("Mode.initial: %s", mode.initial)
        return redirect('/')
    if request.method == 'GET':
        if 'mode' in session:
            mode = Mode.query.get(session['mode'])
        else:
            mode = Mode.query.filter_by(author_id=current_user.id).first()
        ava = rebal(mode.initial, mode.inventory)
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
        if request.form['origin'] == 'chemin':
            app.logger.warning("Chemin path")
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

# Modes CRUD


@app.route('/modes', methods=['GET'])
@login_required
def modes():
    if request.method == 'GET':
        all_modes = Mode.query.filter_by(author_id=current_user.id).all()
        # mode_schema = ModeSchema()
        # many needed for multiple
        # result = mode_schema.dump(all_modes)
        modes_schema = ModeSchema(many=True)
        result = modes_schema.dump(all_modes)
        app.logger.debug(result)
        # pprint(result)
        return modes_schema.jsonify(all_modes)


@app.route('/modes/<int:id>', methods=['GET'])
@login_required
def get_mode(id):
    mode = Mode.query.get_or_404(id)
    mode_schema = ModeSchema()
    return mode_schema.jsonify(mode)


@app.route('/modes', methods=['POST'])
@login_required
def create_mode():
    if not request.json or not 'title' in request.json:
        abort(400)
    json_data = request.get_json()
    mode_schema = ModeSchema()
    try:
        mode = mode_schema.load(json_data).data
    except ValidationError as err:
        return jsonify(err.messages), 422
    inventory = mode.inventory
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

    mode.initial = initial
    mode.author_id = current_user.id
    db.session.add(mode)
    db.session.commit()
    # return redirect(url_for('modes'))
    return mode_schema.jsonify(mode), 201


@app.route('/modes/<int:id>', methods=['PUT'])
@login_required
def update_mode(id):
    if not request.json or 'title' not in request.json:
        abort(400)
    myMode = Mode.query.get(id)
    json_data = request.get_json()
    old = json_data['oldinventory']
    json_data.pop('oldinventory', None)
    mode_schema = ModeSchema()
    try:
        mode = mode_schema.load(json_data).data
    except ValidationError as err:
        return jsonify(err.messages), 422
    inventory = mode.inventory
    myMode.title = json_data['title']
    myMode.qlambda = json_data['qlambda']
    myMode.qtarget = json_data['qtarget']
    myMode.fwhma = json_data['fwhma']
    myMode.fwhmb = json_data['fwhmb']
    inventory = json_data['inventory']
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
    return mode_schema.jsonify(myMode), 201


@app.route('/modes/<int:id>', methods=['DELETE'])
def delete_task(id):
    m = Mode.query.get(id)
    db.session.delete(m)
    db.session.commit()
    return jsonify({'result': True})

# Mode Landing page


@app.route('/mode')
@login_required
def mode():
    if request.method == 'GET':
        # myModes = db.session.query(Mode).filter(Mode.author_id == current_user.id)
        # myModes = db.session.query(Mode).filter_by(author_id=current_user.id)
        # myModes = db.session.query(Mode).all()
        return render_template('mode.html')


@app.route('/activeMode', methods=['GET', 'POST'])
@login_required
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
        session['mode'] = request.form['mode']
        # print mode_id, mode.id, session
        return redirect('/')
    if request.method == 'GET':
        myModes = Mode.query.filter_by(author_id=current_user.id).all()
        if 'mode' in session:
            current_mode = Mode.query.get(session['mode'])
        else:
            current_mode = Mode.query.filter_by(
                author_id=current_user.id).first()
        return render_template('activeMode.html', modes=myModes, current_mode=current_mode)


@app.route('/odr_ajax')
def odr_demo():
    return render_template('odr_ajax.html')


@app.route('/odr_post')
def odr_post():
    return render_template('odr_post.html')


def qxrd_worker(userData, phasearray, ar):
    angle = userData[0]
    diff = userData[1]

    # defaultMode = Mode('Default', 0, 'Co', 0, 0.3, 'rockforming', None, None)
    app.logger.warning(session)
    app.logger.warning('Length of angle array: %d', len(angle))

    # Mode
    if 'mode' in session:
        myMode = Mode.query.get(session['mode'])
    else:
        myMode = defaultMode
    Lambda = myMode.qlambda
    Target = myMode.qtarget
    FWHMa = myMode.fwhma
    FWHMb = myMode.fwhmb

    # Load inventory
    DBname = 'difdata_' + myMode.inventory + '.txt'
    difdata = open(DBname, 'r').readlines()

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
    selectedPhases = phasearray
    selectedphases = []
    for i in range(len(selectedPhases)):
        name, code = selectedPhases[i].split('\t')
        code = int(code)
        selectedphases.append((name, code))

    app.logger.warning('Autorm: %s', ar)
    app.logger.info(InstrParams)
    
    results, BG, Sum, mineralpatterns = qxrd.Qanalyze(userData,
                                                      difdata,
                                                      selectedphases,
                                                      InstrParams,
                                                      ar,
                                                      True)
    app.logger.warning(results)
    session['results'] = results
    sel, ava = rebalance(results)
    g.selected = sel

    minerallist = [(l + BG).tolist() for l in mineralpatterns]

    xmin = min(angle)
    xmax = max(angle)
    Imax = max(diff[min(np.where(np.array(angle) > xmin)[0])
               :max(np.where(np.array(angle) > xmin)[0])])
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
    modeset = None
    if current_user.is_authenticated:
        mode = Mode.query.filter_by(author_id=current_user.id).first()
        if mode:
            modeset = True

    form = UploadForm()

    if form.validate_on_submit():
        f = form.file.data
        filename = secure_filename(f.filename)
        f.save(os.path.join(app.config['UPLOAD_FOLDER'],
                            filename))
        return redirect(url_for('chart', filename=filename))
    return render_template('index.html', form=form, modeset=modeset)


def clearModeCtx():
    session.pop('dbname', None)
    session.pop('available', None)
    session.pop('selected', None)
    session.pop('autoremove', None)
    session.pop('results', None)


def loadModeCtx():
    g.autorm = True
    if current_user.is_authenticated:
        if 'mode' in session:
            mode = Mode.query.get(session['mode'])
        else:
            mode = Mode.query.filter_by(author_id=current_user.id).first()
        g.selected = mode.initial
        g.mode = mode
    else:
        # anonymous flow
        g.selected = phaselist.rockPhases
        g.mode = defaultMode
        # app.logger.warning("loadModeCtx session['selected']: % s", session['selected'])


@app.route('/chart/<filename>', methods=['GET', 'POST'])
def chart(filename):
    clearModeCtx()
    loadModeCtx()

    # app.logger.info(session)

    # Load parameters for computation
    XRDdata = open(os.path.join('uploads', filename), 'r')
    userData = qxrdtools.openXRD(XRDdata, filename)
    angle = userData[0]
    diff = userData[1]

    ava = rebal(g.selected, g.mode.inventory)
    # app.logger.warning(g.selected)

    template_vars = {
        'angle': angle.tolist(),
        'diff': diff.tolist(),
        'samplename': filename,
        'mode': g.mode,
        'availablephaselist': ava,
        'selectedphaselist': g.selected,
        'autorm': g.autorm
    }
    return render_template('chart.html', **template_vars)


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

        data = plotdata['data']
        ar = data['autorm']
        sample = data['sample']
        phasearray = sample['phases']
        # selectedphases = [(d['name'], d['AMCSD_code']) for d in phasearray]

        x = sample['x']
        y = sample['y']
        angle = np.asfarray(np.array(x))
        diff = np.asfarray(np.array(y))
        userData = (angle, diff)

        result = qxrd_worker(userData, phasearray, ar)

        return json.dumps(result)
    else:
        return '''<html><body><h1>Did not get a post!</h1></body></html>'''
    # [END ODR service]

# [START odr second pass process, this is run when the user changes the phases and relaunch after the chemin call]


# [START ODR service]
# Duplicates /process with input from the ODR site
# Handles both post and ajax json service mode
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

        # Initialize the session object with chemin data
        session['autoremove'] = False
        session['dbname'] = 'difdata_chemin.txt'
        session['selected'] = phaselist.cheminPhases
        session['available'] = phaselist.availablePhases
        session['filename'] = filename

        x = [li['x'] for li in array]
        y = [li['y'] for li in array]

        angle = np.asfarray(np.array(x))
        diff = np.asfarray(np.array(y))

        # Force mode
        Lambda = 1.79027
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
        # print session
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
        Imax = max(diff[min(np.where(np.array(angle) > xmin)[0])                        :max(np.where(np.array(angle) > xmin)[0])])
        offset = Imax / 2 * 3
        offsetline = [offset] * len(angle)

        difference_magnification = 1
        difference = (diff - Sum) * difference_magnification
        # logging.debug(results)
        # logging.info("Done with processing")
        offsetdiff = difference + offset

        csv = 'ODR'
        session['results'] = results

        app.logger.warning('Length of angle array: %d', len(angle))
        minerallist = [(l + BG).tolist() for l in mineralpatterns]

        session['filename'] = filename

        cheminMode = Mode('DefaultChemin', 0, 'Co', 0, 0, 'chemin')

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
        return render_template('chemin.html', **template_vars)
    else:
        return '''<html><body><h1>Did not get a post!</h1></body></html>'''
# [END ODR service]


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

    cheminMode = Mode('DefaultChemin', 0, 'Co', 0, 0, 'chemin')

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
    return render_template('chemin.html', **template_vars)
# [END process]


# [START process]


@app.route('/process', methods=['GET', 'POST'])
def process():
    if current_user.is_authenticated:
        app.logger.warning('User:{}'.format(current_user.name))

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
    selectedPhases = g.selected

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
    g.selected = sel
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
    Imax = max(diff[min(np.where(np.array(angle) > 15)[0]):max(np.where(np.array(angle) > xmin)[0])])
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
        'selectedphaselist': session['selected'],
        'autoremove': False
    }
    return render_template('chemin.html', **template_vars)
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
