# This will upload a file and print content
@app.route('/boo', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('uploaded_file',
                                    filename=filename))
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>
    '''

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)


@app.route('/printdata', methods=['GET', 'POST'])
def printdata():
    resp = make_response(render_template('index.html'))
    return resp    

@app.route('/run_post')
def run_post():
    url = '/parse_post'
    data = {'name': 'Burbank', 'format': 'XRD', 'coord': 36}
    headers = {'Content-Type': 'application/json'}

    return Request('POST',url, data=json.dumps(data), headers=headers)

@app.route('/parse_post', methods=['POST'])
def parse_post():
    if request.method == 'POST':
        json_dict = request.get_json()
        filename = json_dict['name']
#        print(filename, file=sys.stderr)
        print(filename)

        return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>YES!</h1>
    '''
    else:
        return '''<html><body>Something went horribly wrong</body></html>'''

# [START form]
# This will upload a file and process as quant
@app.route('/form')
def form():
    return """
<form method="POST" action="/process" enctype="multipart/form-data">
    <input type="file" name="file">
    <input type="submit">
</form>
"""
# [END form]

# [START phase setting]
@app.route('/phase', methods=['GET', 'POST'])
def phase():
    if request.method == 'POST':
        selectedlist = request.form['selectedphase']
        availlist = request.form['availablephase']
        # selectedlist.sort()
        # availlist.sort()

        return redirect('/')
    else:
        mode = QuantModeModel()
        # print(mode, file=sys.stderr)
        # session['mode'] = mode

        template_vars = {
            'availablephaselist': mode.available,
            'selectedphaselist': mode.selected,
            'mode': ''
        }
        return render_template('phase.html', **template_vars)

    #    return "Total computation  time = %.2fs" %(time.time()-t0)
    #return_str = ''
    #return_str += 'results: {}<br />'.format(str(results))
    #return return_str

    # [START parseSampleFile]
@app.route('/parseSampleFile', methods=['POST'])
def parse_sample_file():
    uploaded_file = request.files.get('file')
    if not uploaded_file:
        return 'No file uploaded.', 400

    # Load the sample data file in userData
    # parse sample data file wrt format

    filename = uploaded_file.filename
    XRDdata = uploaded_file
    userData = qxrdtools.openXRD(XRDdata, filename)
    
    return render_template('chart.html', **template_vars)

    
    #    return "Total computation  time = %.2fs" %(time.time()-t0)
    #return_str = ''
    #return_str += 'results: {}<br />'.format(str(results))
    #return return_str
# [END parseSampleFile]

# [START chemin micro service]
# WE are not using np.loadtxt to split angle, diff so no need to massage for display
# util for chemin service
# util for chemin service
# util for chemin service
@app.route('/odr_process', methods=['POST'])
def odr_process_data():
    json_dict = request.get_json()
    # samplename = json_dict['samplename']
    # list = json_dict['phaselist']
    #    selectedphases = json_dict.items()
    list = json_dict['phaselist']
    samplename = json_dict['samplename']
    angle = json_dict['angle']
    diff = json_dict['diff']
    selectedphases = list.items()
    # print(selectedphases, file=sys.stderr)

    # Chemin: Parameters are fixed, as well as the mineral database
    InstrParams = {"Lambda": 0, "Target": 'Co', "FWHMa": 0.00, "FWHMb": 0.35}
    DBname ='difdata_CheMin.txt'
    # Dif data captures all cristallographic data
    # Load in the DB file
    difdata = open(DBname, 'r').readlines()
    
    #Data coming from ODR
    #samplename = "Mix3C-film.txt"
    # userData = (samples.angle, samples.diff)
    userData = (angle, diff)
#    selectedphases = samples.phaselist.items()
    # print(selectedphases, file=sys.stderr)
        
    results, BG, calcdiff = qxrd.Qanalyze(userData, difdata, selectedphases, InstrParams)
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
    csv = 'LUDO'
    
    template_vars = {
        'phaselist': results,
        'angle': angle,
        'diff': diff,
        'bgpoly': bgpoly.tolist(),
        'sum': calcdiff.tolist(),
        'url_text': csv,
        'key': 'ludo',
        'samplename': samplename,
        'mode': ''
    }
    return render_template('chart.html', **template_vars)
# [END chemin]

@app.route('/test')
def test():
    # Load data from file
    json_data = open('ludo.txt')
    
    data = json.load(json_data)
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
    print(userData)
    results, BG, calcdiff = qxrd.Qanalyze(userData, difdata, selectedphases, InstrParams)

    twoT = userData[0]
    diff = userData[1]

    # logging.debug(results)3
    # logging.info("Done with processing")

    angle = twoT
    # diff = diff
    bgpoly = BG
    #calcdiff = calcdiff

    # csv = session_data_key.urlsafe()
    csv = 'LUDO'
    
    template_vars = {
        'phaselist': results,
        'angle': angle.tolist(),
        'diff': diff.tolist(),
        'bgpoly': bgpoly.tolist(),
        'sum': calcdiff.tolist(),
        'url_text': csv,
        'key': 'ludo',
        'samplename': filename,
        'mode': ''
    }
    return render_template('chart.html', **template_vars)

@app.route('/ludo', methods=['POST'])
def ludo_process_data():
    json_dict = request.get_json()

    sample = json_dict["sample"]
    samplename = sample["name"]

    array = sample["data"]
    angle = [li['x'] for li in array]
    diff = [li['y'] for li in array]

    phasearray = json_dict["phases"]
    selectedphases = [(d['name'], d['AMCSD_code']) for d in phasearray]

    print(selectedphases)

    # Chemin: Parameters are fixed, as well as the mineral database
    InstrParams = {"Lambda": 0, "Target": 'Co', "FWHMa": 0.00, "FWHMb": 0.35}
    DBname ='difdata_CheMin.txt'
    # Dif data captures all cristallographic data
    # Load in the DB file
    difdata = open(DBname, 'r').readlines()
    
    #Data coming from ODR
    #samplename = "Mix3C-film.txt"
    # userData = (samples.angle, samples.diff)
    userData = (angle, diff)
    print(userData)
    #    selectedphases = samples.phaselist.items()
        
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
    csv = 'LUDO'
    
    template_vars = {
        'phaselist': results,
        'angle': angle,
        'diff': diff,
        'bgpoly': bgpoly.tolist(),
        'sum': calcdiff.tolist(),
        'url_text': csv,
        'key': 'ludo',
        'samplename': samplename,
        'mode': ''
    }
    return render_template('chart.html', **template_vars)
# [END ludo]

from flask import Flask, flash, request, render_template, redirect, make_response, url_for, send_from_directory, session

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/cheminfile')
def get_data():
#    return("upload your file")
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>
    '''
    
