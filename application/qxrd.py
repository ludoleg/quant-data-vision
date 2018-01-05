import logging
import numpy as np
import time
from math import *
#from math import factorial
from scipy.optimize import leastsq

'''
code was modified to enable selectedphase list to be used.  QXRDtools remains unchanged.

'''


def Setparameters():
    """
    this function sets parameters for QXRD analysis.
    It also serves as a patch for the poor implementation of metadata reading from XRD files
    and for the current absence of user calibration tools (find a, b, possible 2theta offsets)
    Should eventually be replaced by parameters sent from handlers based on user settings
    """
    BGsmoothing = True
    w = 100
    w2 = 5
    Polyorder = 4
    addBG = 0  # enter 0 to disable

    # Initialization
    INIsmoothing = False
    OStarget = 0.01

    return(BGsmoothing, w, w2, Polyorder, addBG, INIsmoothing, OStarget)


def SetparametersSTRIP():
    """
    this function sets parameters for QXRD analysis.
    It also serves as a patch for the poor implementation of metadata reading from XRD files
    and for the current absence of user calibration tools (find a, b, possible 2theta offsets)
    Should eventually be replaced by parameters sent from handlers based on user settings
    modified in Nov '17 for new BG stripping algorithm
    """
    BGsmoothing = True
    stripwindow = 15
    stripiterations = 100
    addBG = 0  # enter 0 to disable
    # Initialization
    INIsmoothing = True
    OStarget = 0.01

    return(BGsmoothing, stripwindow, stripiterations, addBG, INIsmoothing, OStarget)


def activatephases(selection):
    '''  
    This function creates an enable list by comparing the inventory of the database (mineral, code) with the user selection
    returns an enable list 
    '''
    enable = []
    selectedcode = []
    for i in range(0, len(selection)):
        selectedcode.append(selection[i][1])

    for i in range(0, len(code)):
        if code[i] in selectedcode:
            enable.append(1)
        else:
            enable.append(0)

    return enable


'''
def setQthresh(RIR):
    #######################   Define Initialization Threshold list      ############
    Thresh = np.zeros_like(RIR)
    for i in range(0,len(RIR)):
        Thresh[i] = 2
    return Thresh
'''


def setQthresh(RIR):
    #######################   Define Initialization Threshold list      ############
    Thresh = np.zeros_like(RIR)
    for i in range(0, len(RIR)):
        if RIR[i] < 1:
            Thresh[i] = 5.
        if RIR[i] >= 1:
            Thresh[i] = 3
        if RIR[i] >= 2:
            Thresh[i] = 2
    return Thresh


def Qanalyze(userData, difdata, selection, instrParams, autoremove, BGstrip):
    """
    This function orchestrates the quantitative analysis
    All critical functions are imported from QRDtools
    Use this to change the sequence of processing
    Arguements:
    userdata: list of tupples angle (= axis X of diffraction pattern) and diff (axis Y of diffraction pattern)
    difdata: database
    selection: list of minerals and AMCSD #
    instrParams: dictionary with Lambda, Target, FWHMa, FWHMb,    more to come
    """
    global code, RIR
    #global RIR
    global enable
    global Thresh
    global PatDB
    global angle
    global diff
    global BG
    global mineral
    global I
    global Iinit
    global nameref

    angle, diff = userData
    angle = np.array(angle)
    diff = np.array(diff)

    logging.debug("Start Qanalyze")

    Lambda = instrParams['Lambda']
    Target = instrParams['Target']
    FWHMa = float(instrParams['FWHMa'])
    FWHMb = float(instrParams['FWHMb'])
    if Lambda in ('', 0) and Target in ["Co", "Cu"]:
        Lambda = getLambdafromTarget(Target)
    if Lambda in ('', 0) and Target == '':
        Target = "Co"
        Lambda = getLambdafromTarget(Target)
        logging.info('No Lambda or Target data:  assumed to be Co Ka')

    sigmaa = FWHMa / (2 * sqrt(2 * log(2)))
    sigmab = FWHMb / (2 * sqrt(2 * log(2)))
    #########    Process Background     #######################################

    if BGstrip:
        BGsmoothing, stripwindow, stripiterations, addBG, INIsmoothing, OStarget = SetparametersSTRIP()
        BG = BGsmooth_and_strip_rdmstep(
            stripwindow, stripwindow / 5, stripiterations, BGsmoothing)
    else:
        BGsmoothing, w, w2, Polyorder, addBG, INIsmoothing, OStarget = Setparameters()
        BG = BGfit(BGsmoothing, w, w2, Polyorder)
    ##########  builds minerals lists   #########################################

    mineral, code = makephaselist(difdata)
    nameref = {}
    for i in range(0, len(code)):
        nameref[code[i]] = mineral[i]
    enable = activatephases(selection)
    code, enable = CleanMineralList()
    #######################   Extract from difdata      ############

    logging.info("Starting extracting from difdata")
    starttime = time.time()
    # DB, RIR, peakcount = makeDB(difdata, code, enable, Lambda)
    DB, RIR, peakcount = makeDB(difdata, Lambda)
    DB2T = DB[:, :, 0]
    DBInt = DB[:, :, 1]
    PatDB, enable = calculatePatDB(DB2T, DBInt, sigmaa, sigmab)

    logging.info("PatDB computing time = %.3fs" % (time.time() - starttime))
    Thresh = setQthresh(RIR)
    trashme = RIR

    code, RIR, enable, Thresh, trashme, PatDB = CleanMineralListPatDB(trashme)

    if len(selection) > 0:
        initialize = True
        optimize = True
    else:
        initialize = False
        optimize = False

    starttime = time.time()

    if initialize and autoremove:
        logging.info("Start Initialization")
        Iinit = getIinitPatDB(INIsmoothing, OStarget)
        Ithresh = 0.01
        Ithresholding(Ithresh, Iinit)
        while sum(enable) > 25:
            Ithresh += 0.01
            Ithresholding(Ithresh, Iinit)
        logging.info("Done computing Initialization")

        #####     remove minerals disabled by initialization       ################
        if sum(enable) > 0:
            code, RIR, enable, Thresh, Iinit, PatDB = CleanMineralListPatDB(
                Iinit)
            Sum_init = sumPat(Iinit)
            #Sum_init *= max(diff-BG)/max(Sum_init)
            Sum_init += BG
            Qinit = Iinit / sum(Iinit) * 100
            logging.info("Iinit computing time = %.3fs" %
                         (time.time() - starttime))
        for i in range(0, len(code)):
            logging.info("Qinit_%s : %.2f " % (nameref[code[i]], Qinit[i]))
    else:
        Iinit = np.array(([1.] * len(enable))) * np.array(enable)

    starttime = time.time()

    if sum(enable) == 0:
        optimize = False

    if optimize:

        logging.info("Start computing optimization")
        I = QrefinelstsqPatDB(Iinit, autoremove)
        logging.info("Done computing optimization")

        # reorganize results by decreasing % order #########        print enable
        code, RIR, enable, Thresh, I, PatDB = CleanMineralListPatDB(I)
        code, RIR, enable, Thresh, I, PatDB = sortQlistPatDB()

    ####    #redo DB with shorter list    #####
    results = []

    if sum(enable) > 0:
        Sum = sumPat(I)
        Sum += BG
        Q = I / sum(I) * 100
        for i in range(0, len(code)):
            results.append([nameref[code[i]], code[i], '%.1f' % Q[i]])
    else:  # this is to prevdnt crash if no phase is found at INIT
        Sum = BG
        results = (('NO_RESULT', '0000', '000.0'),)

    for i in range(0, len(code)):
        logging.info("%s = %.2f" % (code[i], I[i]))

    logging.info("I Lstsq computing time = %.3fs" % (time.time() - starttime))
    logging.debug(code)
    return results, BG, Sum


'''
Bellow is the function to calculate the gaussian patterns using an erf function instead of a gaussian, to avoid sampling errors. 
It works but it's incredibly slow.   (65.s vs 1.5s).   Saved for later use:
if we detect 2theta sampling conditions not meeting Nyquist rule.
if max(FWHM) <2* 2theta_step (2theta_step =(X[len(X)-1]-X[0])/(len(X)-1)) then use gausspeakerf in place of gausspeak.

def phi(x):
    #Cumulative distribution function for the standard normal distribution
    #used to calculate the integral of the gaussian distribution inside a 2Theta bin
    phi=(1.0 + erf(x / sqrt(2.0))) / 2.0
    return phi
    
def gausspeakerf(X,X0,S):
    #X = 2T array, X0+peak position, S=sigma
    #calculates peak profile using Phi(x) function
    step = (X[len(X)-1]-X[0])/(len(X)-1)
    I = np.zeros_like(X)
    for i in range(0, len(X)-1):
        I[i] = phi((X[i]-X0+step/2)/S) - phi((X[i]-X0-step/2)/S)        
    return I
'''


def gausspeak(X, X0, S):
    # X = 2Theta array, X0+peak position, S=sigma
    # calculates peak profile using gauss function
    I = (1 / S / sqrt(2 * pi)) * e**(-(X - X0)**2 / 2 / S**2)
    return I


def gausspat(X, twoT, Irel, RIR, a, b):
    Yg = np.zeros_like(X)
    X = np.array(X)
    for i in range(0, len(twoT)):
        S = a * twoT[i] + b
        Yg += Irel[i] * gausspeak(X, twoT[i], S)
    Yg *= RIR
    return Yg


def calculatePatDB(DB2T, DBInt, a, b):
    '''
    calculates array of patterns
    '''

    PatDB = np.zeros((len(code), len(angle)))
    for i in range(0, len(code)):
        if enable[i] == 1:
            PatDB[i] = gausspat(angle, DB2T[i], DBInt[i], RIR[i], a, b)
            if sum(PatDB[i]) < 10:  # this is to disable phases with no peaks in the angular range
                enable[i] = 0
    return PatDB, enable


def sumPat(I):
    '''
    computes the sum of patterns with I as intensity vector
    take PatDB 2D array and I 1D array
    '''
    PatDB2 = np.array(PatDB)
    sumPat = np.zeros_like(diff)
    for i in range(0, PatDB2.shape[0]):
        sumPat += I[i] * PatDB2[i]
    return sumPat


'''    
def smoothing(Y,T):
    smooth = np.array(Y)
    for i in range(0,len(Y)):
        minsmooth = max(i-T/2, T/2)
        maxsmooth = min(i+T/2, len(Y)-T/2)
        if minsmooth-maxsmooth>1:
            smooth[i] = np.mean(Y[minsmooth:maxsmooth])
    return smooth
'''


def smoothdata(y, window_size, order, deriv=0, rate=1):
    """
    Data smoothing algorithm using the Savitzky Golay Filtering method
    Code found in scipy cookbook:  http://scipy.github.io/old-wiki/pages/Cookbook/SavitzkyGolay
    requires: from math import factorial
    """

    try:
        window_size = np.abs(np.int(window_size))
        order = np.abs(np.int(order))
    except ValueError, msg:
        raise ValueError("window_size and order have to be of type int")
    if window_size % 2 != 1 or window_size < 1:
        raise TypeError("window_size size must be a positive odd number")
    if window_size < order + 2:
        raise TypeError("window_size is too small for the polynomials order")
    order_range = range(order + 1)
    half_window = (window_size - 1) // 2
    # precompute coefficients
    b = np.mat([[k**i for i in order_range]
                for k in range(-half_window, half_window + 1)])
    m = np.linalg.pinv(b).A[deriv] * rate**deriv * factorial(deriv)
    # pad the signal at the extremes with
    # values taken from the signal itself
    firstvals = y[0] - np.abs(y[1:half_window + 1][::-1] - y[0])
    lastvals = y[-1] + np.abs(y[-half_window - 1:-1][::-1] - y[-1])
    y = np.concatenate((firstvals, y, lastvals))
    return np.convolve(m[::-1], y, mode='valid')


def BGsmooth_and_strip_rdmstep(stripwindow, rdmfactor, iterations, smooth):
    '''
    background striping inspired by the stripping in PyMCA but a randomization of the stripping window is added to remove ripples
    allow wider windows to be used, and fewer iterations than regular stripping.
    recommended setting:  Stripwindow = 15  (2xFWHM in points), rdmfactor = stripwindow/5, iterations = 100 
    initial smoothing of data avoids anchoring on low point of the noise.
    curved anchored on initial and final 15 points (j loop)
    '''

    SavitzkyGolay_window = 11  # has to be odd number
    SavitzkyGolay_poly_order = 3
    curve_ends_anchor_window = 15

    if smooth:
        datain = smoothdata(diff, SavitzkyGolay_window,
                            SavitzkyGolay_poly_order)
    else:
        datain = diff
    dataout = np.array(datain)

    for i in range(0, iterations):
        rdmstep = np.int_(np.random.randn(len(datain))
                          * rdmfactor + stripwindow)

        for j in range(curve_ends_anchor_window, len(datain) - curve_ends_anchor_window):
            dataout[j] = min(datain[j], (datain[max(
                0, j - rdmstep[j])] + datain[min(len(datain) - 1, j + rdmstep[j])]) / 2)
        datain = dataout

    return dataout


def BGfit(BGsmoothing, w, w2, Polyorder):
    '''
    ####################   fits background   ###########################
    # Smoothing option
    #  BGsmoothing = boolean
    #  w = window width for minimum testing (INT)
    #  w2 = window width for averaging (INT)
    #  Polyorder= polynomial fit order (INT)
    '''
    if BGsmoothing:
        BGthresh = 1.25
    else:
        BGthresh = 1.5

    #########   Spot selection   ########################################
    diffBG = np.zeros_like(diff)
    BGX = []
    BGY = []

    if BGsmoothing:
        diffBG = smoothdata(diff, w2, 3)
    else:
        diffBG = diff

    for i in range(1, len(angle) - 1):
        minBGwin = max(i - w / 2, w / 2)
        maxBGwin = min(i + w / 2, len(angle) - w / 2)
        if diffBG[i] < (min(diffBG[minBGwin:maxBGwin]) * BGthresh):
            BGX.append(angle[i])
            BGY.append(diffBG[i])
    #########   Polynomial fit   ########################################
    if len(BGY) < 10:
        BGpoly = diff - diff
    else:
        polycoefs = []
        polycoefs = np.polyfit(BGX, BGY, Polyorder)
        BGpoly = np.zeros(len(angle))
        for i in range(0, Polyorder + 1):
            BGpoly += polycoefs[i] * angle ** (Polyorder - i)

    return BGpoly


def getLambdafromTarget(Target):
    if Target == "Cu":
        Lambda = 1.541838
    elif Target == 'Co':
        Lambda = 1.78897
    else:
        logging.info('ERROR: Tube target material unknown')
    return Lambda


def makephaselist(difdata):
    """"
    makes inventory of phase present in difdata and associated AMCSD codes.
    """

    limits_nameorder = []
    nameline = True
    name = []
    code = []
    Imax = []

    # loop bellow find the line positions of each beginning and end of difdata.txt
    for i in range(0, len(difdata)):
        iv2 = 0
        Vcell = 0
        line = difdata[i]
        if nameline:
            namelinenum = i
            name.append(str(line[6:-2]))
            nameline = False
        if not(nameline) and ("database_code_amcsd") in line:
            code.append(int((line[27:-1])))

        if not(nameline) and "_END_" in line:
            endline = i
            nameline = True

    return name, code


def makeDB(difdata, Lambda):
    """"
    # DB is a 3D list containing all data of each mineral
    ##  1st dimension:  mineral number
    ##  2nd dimension: peak number
    ##  3rd dimension: data 2T I d H K L Multiplicity
    """
    5
    limits_nameorder = []
    nameline = True
    codes = []
    # loop bellow find the line positions of each beginning and end of difdata.txt
    for i in range(0, len(difdata)):
        line = difdata[i]
        if nameline:
            cardcode = 0
            for j in range(i, i + 11):
                line2 = difdata[j]
                if ("_database_code_amcsd") in line2:
                    cardcode = int(line2[26:-1])
            namelinenum = i
            if cardcode > 0:
                codes.append(cardcode)
            nameline = False
        if "_END_" in line:
            endline = i
            if cardcode > 0:
                limits_nameorder.append([namelinenum, endline])
            nameline = True

    limits = np.zeros_like(limits_nameorder)

    for i in range(0, len(code)):
        for j in range(0, len(codes)):
            if codes[j] == code[i]:
                limits[i] = limits_nameorder[j]

    RIR = []
    cellparam = []
    DB = np.zeros((len(code), 200, 7))
    peakcount = 0

    for i in range(0, len(code)):
        iv2 = 0
        density = 0
        datavalues = []
        peaknum = 0
        start = 99999
        if enable[i] == 1:
            for j in range(limits[i][0], limits[i][1] - 3):
                line = difdata[j]
                if ("DENSITY (gm/cm3):") in line:
                    density = float(line[24:-1])
                if ("MAX. ABS. INTENSITY / VOLUME**2:") in line:
                    iv2 = float(line[44:-1])
                    start = j + 2
                elif ("CELL PARAMETERS:") in line:
                    cellparamline = line[24:len(line) - 1]
                    cellparam = [float(n) for n in cellparamline.split()]
                    for k in range(3, 6):
                        cellparam[k] *= pi / 180
                    Vcell = cellparam[0] * cellparam[1] * cellparam[2] * (1 - (cos(cellparam[3]))**2 - (cos(cellparam[4]))**2 - (
                        cos(cellparam[5]))**2 + 2 * cos(cellparam[3]) * cos(cellparam[4]) * cos(cellparam[5]))**0.5
                elif j >= start and peaknum < 20:
                    # linedata = linedata[16:len(linedata)]
                    linedata = difdata[j]
                    datavalues = [float(n) for n in linedata.split()]
                    if len(datavalues) == 7:
                        # datavalues contains data in difdata card: 2T I d H K L Multiplicity
                        # recalculate 2t positions depending on Lambda
                        datavalues[0] = 2 * 180 / pi * \
                            asin(Lambda / 2 / datavalues[2])
                        if datavalues[0] >= 5 and datavalues[0] <= 55:
                            DB[i][peaknum] = datavalues
                            peaknum += 1
            peakcount += peaknum + 1
            if iv2 > 0 and density > 0:
                RIR.append((iv2 / density) / 2.89690461461)
            else:
                RIR.append(0)
        else:
            RIR.append(0)

    return DB, RIR, peakcount


def scalePat(X, Yexp, Pat, OStarget):
    """
    #  Scales pattern intensity using PatDB for initialization
    """
    tol = .5
    I = 1.

    Pat_area = sum(Pat)
    negativearea = 0

    for i in range(0, len(X)):
        if Yexp[i] < 0:
            negativearea += abs(Yexp[i])
            tol = 0.8  # tolerance factor on overshoot target
    ontarget = False
    if Pat_area <= 0:
        ontarget = True
        I = 0
    while ontarget == False:

        difference = Yexp - Pat * I
        negativearea2 = 0
        for i in range(0, len(X)):
            if difference[i] < 0:
                negativearea2 += abs(difference[i])
        overshoot = (negativearea2 - negativearea) / Pat_area
        if overshoot < OStarget * tol:
            I *= 1.2
        elif overshoot > OStarget / tol:
            I /= 1.2999
        else:
            ontarget = True
    return I


def getIinitPatDB(INIsmoothing, OStarget):
    """
    #######################   Initialization   ###################################
    ############   Computes mineral intensity sustained under diffractogram   ####
    ####   builds 1D array of intensity factors 
    ####  OStarget = overshoot of integral intensity of the single mineral (proportion of mineral calculated pattern above experimental data)
    ####allows removing phase that are obviously not present using Thresh 1D array
    """

    Iinit = np.zeros(len(code))
    diffsmooth = np.zeros_like(diff)
    if INIsmoothing:
        w3 = 4  # width of smooothing window
        for i in range(0, len(angle)):
            minsmooth = max(i - w3 / 2, w3 / 2)
            maxsmooth = min(i + w3 / 2, len(angle) - w3 / 2)
            # computes smoothed value for i
            diffsmooth[i] = np.mean(diff[minsmooth:maxsmooth])

    for i in range(0, len(code)):
        if enable[i] == 1:
            Iinit[i] = scalePat(angle, (diff - BG), PatDB[i], OStarget)
        else:
            Iinit[i] = 0
    return Iinit


def Ithresholding(Ithreshratio, Iloc):
    '''
    ####  turns minerals OFF (enable =0) if under their threshold%   ##############
    '''
    global enable

    for i in range(0, len(enable)):
        if enable[i] <> 0 and Iloc[i] < max(Iloc) * Ithreshratio:
            enable[i] = 0
            #logging.info("%s- init : %.4f >>> eliminated\t" %(mineral[i],I[i]))
    return


def Qthresholding(Iloc):
    '''
    ####  turns minerals OFF (enable =0) if under their threshold%   ##############
    '''
    global enable
    Q = Iloc * enable / sum(Iloc) * 100
    enable2 = enable

    for i in range(0, len(enable2)):
        if enable2[i] <> 0 and Q[i] < Thresh[i]:
            enable2[i] = 0
            #logging.info( "%s- init : %.1f >>> eliminated\t" %(mineral[i],Q[i]))
    return enable2


def CleanMineralList():
    '''
    #####  removes minerals in list if enable=0
    #####  restructures all lists in input
    '''
    codethresh = []
    enablethresh = []

    for i in range(0, len(code)):
        if enable[i] == 1:
            codethresh.append(code[i])
            enablethresh.append(enable[i])
    return codethresh, enablethresh


def CleanMineralListPatDB(Iloc):
    '''
    removes minerals in list when enable=0
    '''
    codethresh = []
    RIRthresh = []
    enablethresh = []
    Threshthresh = []
    Ithresh = []
    PatDBthresh = []

    for i in range(0, len(code)):
        if enable[i] == 1:
            codethresh.append(code[i])
            RIRthresh.append(RIR[i])
            enablethresh.append(enable[i])
            Threshthresh.append(Thresh[i])
            Ithresh.append(Iloc[i])
            PatDBthresh.append(PatDB[i])
    #logging.info("list cleanup computing time = %.2f" %(time.time()-t0))
    return codethresh, RIRthresh, enablethresh, Threshthresh, Ithresh, PatDBthresh


def getKey(item):
    # used for sorting % results in decreasing order
    return item[5]


def sortQlistPatDB():

    #######################   sorts lists in decreasing Q order      ############
    table = []
    for i in range(0, len(code)):
        table.append([nameref[code[i]], code[i], RIR[i],
                      enable[i], Thresh[i], I[i], PatDB[i]])

    table.sort(key=getKey, reverse=True)

    codesorted = []
    enablesorted = []
    RIRsorted = []
    Threshsorted = []
    Isorted = []
    PatDBsorted = []

    for i in range(0, len(code)):
        codesorted.append(table[i][1])
        RIRsorted.append(table[i][2])
        enablesorted.append(table[i][3])
        Threshsorted.append(table[i][4])
        Isorted.append(table[i][5])
        PatDBsorted.append(table[i][6])

    return codesorted, RIRsorted, enablesorted, Threshsorted, Isorted, PatDBsorted


def residualPatDB(I):
    """
    # Residual function for least square optimization of gaussian peaks 
    #  variable to refine:  I = intensity factors list  
    """
    I = abs(I)
    residual = np.absolute(diff - BG - sumPat(I))
    return residual


def modelcurve(X, I):

    I = (1 / S / sqrt(2 * pi)) * e**(-(X - X0)**2 / 2 / S**2)

    Yg = np.zeros_like(X)
    X = np.array(X)
    for j in range(len(I)):

        for i in range(0, len(twoT)):
            S = a * twoT[i] + b
            Yg += Irel[i] * gausspeak(X, twoT[i], S)
        Yg *= RIR[j]

    return sumPat(I) + BG


def QrefinelstsqPatDB(Iinit, autoremove):
    """
    This function refine the % values of the mineral in the mixture using least-square optimization method.
    Requires scipy
    """
    global code, RIR, enable, Thresh, PatDB, angle, diff, BG, mineral

    Keep_refining = True
    counter = 0  # counts iteration of the refinement.
    I = abs(np.array(Iinit))
    precision = [0.1, 0.05, 0.01]

    while Keep_refining:
        # recalculate DB with current list
        counter += 1
        t0 = time.time()
        #logging.info( "counter = %s     minerals:%s", counter, sum(enable))
        Keep_refining = False
        Istart = I
        I, pcov = leastsq(residualPatDB, Istart,  gtol=precision[counter - 1])
        I = abs(I)
        logging.info("end LSTSQ #%s",  counter)
        if autoremove:
            enable2 = Qthresholding(I)
            #I *= enable2
            if sum(enable2) < sum(enable):
                Keep_refining = True
                enable = enable2
                mineral, RIR, enable, Thresh, I, PatDB = CleanMineralListPatDB(
                    I)

            if counter < 3:
                Keep_refining = True

        logging.info("lstsq computing time =%s", (time.time() - t0))

    return I
