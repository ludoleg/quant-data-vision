import logging
import numpy as np
import time
from math import *
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
    w2 = 4
    Polyorder = 4
    addBG = 0  # enter 0 to disable
   
    # Initialization
    INIsmoothing = False
    OStarget = 0.01

    return(BGsmoothing,w,w2,Polyorder,addBG,INIsmoothing,OStarget)


def activatephases(code, selection):
    '''  
    This function creates an enable list by comparing the inventory of the database (mineral, code) with the user selection
    returns an enable list 
    '''
    enable = []
    selectedcode = []
    for i in range (0, len(selection)):
        selectedcode.append(selection[i][1])

    for i in range(0, len(code)):
        if code[i] in selectedcode:
            enable.append(1)
        else:
            enable.append(0)

    return enable


def setQthresh(RIR):
    #######################   Define Initialization Threshold list      ############
    Thresh = np.zeros_like(RIR)
    for i in range(0,len(RIR)):
        if RIR[i] < 1:
            Thresh[i] = 5.
        if RIR[i] >= 1:
            Thresh[i] = 3
        if RIR[i] >= 2:
            Thresh[i] = 2
    return Thresh

def Qanalyze(userData, difdata, selection, instrParams):
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
    angle, diff = userData
    angle = np.array(angle)
    diff = np.array(diff)
    
    logging.debug("Start Qanalyze")

    Lambda = instrParams['Lambda']
    Target = instrParams['Target']
    FWHMa = float(instrParams['FWHMa'])
    FWHMb = float(instrParams['FWHMb'])
    
    if Lambda in ('',0) and Target in ["Co", "Cu"]:
        Lambda = getLambdafromTarget(Target)
    if Lambda in ('',0) and Target == '':
        Target = "Co"
        Lambda = getLambdafromTarget(Target)
        logging.info('No Lambda or Target data:  assumed to be Co Ka')
    
    sigmaa = FWHMa / (2*sqrt(2*log(2)))
    sigmab = FWHMb / (2*sqrt(2*log(2)))
    #########    Process Background     #######################################
    
    BGsmoothing,w,w2,Polyorder,addBG,INIsmoothing,OStarget = Setparameters()

    BGpoly = BGfit(angle, diff, BGsmoothing, w, w2, Polyorder)

    # logging.debug('Starting PhaseAnalysis')
    # logging.debug(phaselist)
    
    ##########  builds minerals lists   #########################################

    mineral, code = makephaselist(difdata)
    nameref = {}
    for i in range(0,len(code)):
        nameref[code[i]] = mineral[i]
    enable = activatephases(code, selection)
    code, enable = CleanMineralList(code, enable)
    #######################   Extract from difdata      ############
    
    logging.info("Starting extracting from difdata")
    starttime = time.time()
    DB, RIR, peakcount = makeDB(difdata, code, enable, Lambda)
    DB2T = DB[:,:,0]
    DBInt = DB[:,:,1]
    PatDB, enable = calculatePatDB(angle,DB2T, DBInt, code, RIR, enable, sigmaa, sigmab)
    
    logging.info("PatDB computing time = %.3fs" %(time.time()-starttime))
    Thresh = setQthresh(RIR)
    trashme = RIR
    code, RIR, enable, Thresh, trashme, PatDB = CleanMineralListPatDB (code, RIR, enable, Thresh, trashme, PatDB)
    
    if len(selection) > 0:
        initialize = True
        optimize = True
    else:
        initialize = False
        optimize = False        
    
    starttime = time.time()
    
    if initialize:
        logging.info("Start Initialization")
        Iinit = getIinitPatDB(angle,diff,BGpoly,PatDB, code,enable, INIsmoothing, OStarget)
        Ithresh = 0.05        
        enable = Ithresholding(code, enable,RIR, Ithresh, Iinit)
        while sum(enable) > 25:
            Ithresh += 0.01
            enable = Ithresholding(code, enable,RIR, Ithresh, Iinit)
            
                    
        
        logging.info("Done computing Initialization")
       
        #####     remove minerals disabled by initialization       ################
        if sum(enable) > 0:        
            code, RIR, enable, Thresh, Iinit, PatDB = CleanMineralListPatDB (code, RIR, enable, Thresh, Iinit, PatDB)
            Sum_init = sumPat(Iinit, PatDB)
            #Sum_init *= max(diff-BGpoly)/max(Sum_init)
            Sum_init += BGpoly
            Qinit = Iinit/sum(Iinit)*100
            logging.info( "Iinit computing time = %.3fs" %(time.time()-starttime))
        for i in range(0,len(code)):
            logging.info("Qinit_%s : %.2f " %(nameref[code[i]], Qinit[i]))
    else:
        Iinit = np.array(([1.] * len(enable)))* np.array(enable)

    starttime = time.time()
    
    if sum(enable) == 0:
        optimize = False

    if optimize:
        
        logging.info("Start computing optimization")
        code, RIR, enable, Thresh, I, PatDB = QrefinelstsqPatDB(angle, diff, BGpoly, code, RIR, enable, Thresh, Iinit, PatDB)
        logging.info("Done computing optimization")
    
        #####  reorganize results by decreasing % order #########
        code, RIR, enable, Thresh, I, PatDB = CleanMineralListPatDB(code, RIR, enable, Thresh, I, PatDB)
        code, RIR, enable, Thresh, I, PatDB = sortQlistPatDB(nameref, code, RIR, enable, Thresh, I, PatDB)
    
    ####    #redo DB with shorter list    #####
    results = []
    
    if sum(enable) > 0:
        Sum= sumPat(I, PatDB)
        Sum += BGpoly
        Q = I/sum(I)*100
        for i in range(0, len(code)):
            results.append([nameref[code[i]], code[i], '%.1f' %Q[i]])
    else: #this is to prevdnt crash if no phase is found at INIT
        Sum = BGpoly
        results=(('NO_RESULT', '0000', '000.0'),)
        
    for i in range (0, len(code)):
        logging.info("%s = %.2f" %(code[i], I[i]))
        
    logging.info("I Lstsq computing time = %.3fs" %(time.time()-starttime))
    logging.debug(code)
    return results, BGpoly, Sum

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

def gausspeak(X,X0,S):
    #X = 2Theta array, X0+peak position, S=sigma
    #calculates peak profile using gauss function
    I = (1/S/sqrt(2*pi)) * e**(-(X-X0)**2/2/S**2)    
    return I
    
def gausspat (X,twoT, Irel, RIR, a, b):
    Yg = np.zeros_like(X)
    X = np.array(X)
    for i in range(0, len(twoT)):
        S = a * twoT[i] + b         
        Yg += Irel[i]*gausspeak(X, twoT[i], S)
    Yg *= RIR
    return Yg


def calculatePatDB(X,DB2T, DBInt, mineral, RIR, enable, a, b):
    '''
    calculates array of patterns
    '''
    
    PatDB = np.zeros((len(mineral),len(X)))
    for i in range(0, len(mineral)):
        if enable[i]==1:
            PatDB[i] = gausspat(X,DB2T[i], DBInt[i], RIR[i], a, b)
            if sum(PatDB[i])<10:  # this is to disable phases with no peaks in the angular range
                enable[i]=0
    return PatDB, enable


def sumPat(I, PatDB):
    '''
    computes the sum of patterns with I as intensity vector
    take PatDB 2D array and I 1D array
    '''
    PatDB = np.array(PatDB)
    sumPat = np.zeros(PatDB.shape[1])
    for i in range(0,PatDB.shape[0]):
        sumPat+= I[i]*PatDB[i]
    return sumPat

    
def BGfit(angle, diff, BGsmoothing, w, w2, Polyorder):
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
        for i in range(0,len(angle)):
            minBGsmooth = max(i-w2/2, w2/2)
            maxBGsmooth = min(i+w2/2, len(angle)-w2/2)
            diffBG[i] = np.mean(diff[minBGsmooth:maxBGsmooth])
        else: 
            diffBG = diff

    for i in range(1,len(angle)-1):
        minBGwin = max(i-w/2, w/2)
        maxBGwin = min(i+w/2, len(angle)-w/2)
        if diffBG[i] < (min(diffBG[minBGwin:maxBGwin])*BGthresh):
            BGX.append(angle[i])
            BGY.append(diffBG[i])
    #########   Polynomial fit   ########################################
    if len(BGY)<10:
        BGpoly = diff-diff
    else:
        polycoefs = []
        polycoefs = np.polyfit(BGX,BGY,Polyorder)
        BGpoly = np.zeros(len(angle))
        for i in range(0, Polyorder+1):
            BGpoly += polycoefs[i] * angle ** (Polyorder-i)
    
    return BGpoly


def getLambdafromTarget(Target):
    if Target == "Cu":
        Lambda = 1.541838
    elif Target == 'Co':
        Lambda = 1.78897
    else : logging.info( 'ERROR: Tube target material unknown')
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
        iv2=0
        Vcell=0
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


def makeDB(difdata, codelist, enable, Lambda):
    """"
    # DB is a 3D list containing all data of each mineral
    ##  1st dimension:  mineral number
    ##  2nd dimension: peak number
    ##  3rd dimension: data 2T I d H K L Multiplicity
    """    
    
    limits_nameorder = []
    nameline = True
    codes = []
    # loop bellow find the line positions of each beginning and end of difdata.txt
    for i in range(0, len(difdata)):
        line = difdata[i]
        if nameline:
            cardcode = 0
            for j in range (i, i+11):
                line2 = difdata[j]
                if ("_database_code_amcsd") in line2:
                    cardcode = int(line2[26:-1])
            namelinenum = i
            if cardcode > 0 :
                codes.append(cardcode)
            nameline = False
        if "_END_" in line:
            endline = i
            if cardcode > 0 :
                limits_nameorder.append([namelinenum,endline])
            nameline = True

    limits = np.zeros_like(limits_nameorder)        
        
    for i in range(0,len(codelist)):
        for j in range(0,len(codes)):
            if codes[j] == codelist[i]:
                limits[i] = limits_nameorder[j]

    RIR = []
    cellparam = []
    DB = np.zeros((len(codelist), 200, 7))
    peakcount = 0

    for i in range(0, len(codelist)):
        iv2=0
        density=0
        datavalues = []
        peaknum = 0
        start = 99999
        if enable[i] == 1:
            for j in range (limits[i][0], limits[i][1]-3):
                line = difdata[j]
                if ("DENSITY (gm/cm3):") in line:
                    density=float(line[24:-1])
                if ("MAX. ABS. INTENSITY / VOLUME**2:") in line:
                    iv2=float(line[44:-1])
                    start=j+2
                elif ("CELL PARAMETERS:") in line:
                    cellparamline = line[24:len(line)-1]
                    cellparam = [float(n) for n in cellparamline.split()]
                    for k in range(3,6):
                        cellparam[k] *=pi/180
                    Vcell = cellparam[0] * cellparam[1] *cellparam[2] * (1- (cos(cellparam[3]))**2 - (cos(cellparam[4]))**2 - (cos(cellparam[5]))**2 + 2 * cos(cellparam[3]) * cos(cellparam[4]) * cos(cellparam[5]))**0.5
                elif j >= start and peaknum < 20:
                    linedata = difdata[j]   #       linedata = linedata[16:len(linedata)]
                    datavalues = [float(n) for n in linedata.split()]
                    if len(datavalues)==7:
                        #datavalues contains data in difdata card: 2T I d H K L Multiplicity
                        ##  recalculate 2t positions depending on Lambda  
                        datavalues[0] = 2*180/pi*asin(Lambda/2/datavalues[2])
                        if datavalues[0] >= 5 and datavalues[0] <= 55 :
                            DB[i][peaknum] = datavalues
                            peaknum += 1
            peakcount += peaknum + 1
            if iv2 > 0 and density > 0:
                RIR.append((iv2/density)/2.89690461461)
            else: RIR.append(0)
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
    if Pat_area <= 0 :
        ontarget = True
        I = 0 
    while ontarget==False:
        
        difference = Yexp - Pat*I
        negativearea2 = 0
        for i in range(0, len(X)):
            if difference[i] < 0:
                negativearea2 += abs(difference[i])      
        overshoot = (negativearea2-negativearea)/Pat_area
        if overshoot < OStarget*tol:
            I *= 1.2
        elif overshoot > OStarget/tol:
            I /= 1.2999
        else:
            ontarget = True
    return I


def getIinitPatDB(angle,diff,BGpoly,PatDB, mineral, enable, INIsmoothing, OStarget):
    """
    #######################   Initialization   ###################################
    ############   Computes mineral intensity sustained under diffractogram   ####
    ####   builds 1D array of intensity factors 
    ####  OStarget = overshoot of integral intensity of the single mineral (proportion of mineral calculated pattern above experimental data)
    ####allows removing phase that are obviously not present using Thresh 1D array
    """    
    
    
    Iinit = np.zeros(len(mineral))
    diffsmooth = np.zeros_like(diff)
    if INIsmoothing:
        w3 = 4  #width of smooothing window
        for i in range(0,len(angle)):
            minsmooth = max(i-w3/2, w3/2)
            maxsmooth = min(i+w3/2, len(angle)-w3/2)
            diffsmooth[i] = np.mean(diff[minsmooth:maxsmooth])  #computes smoothed value for i
    
    for i in range(0, len(mineral)):
        if  enable[i] == 1:
            Iinit[i] = scalePat(angle, (diff-BGpoly),PatDB[i],OStarget)
        else :
            Iinit[i] = 0
    return Iinit


def Ithresholding(mineral, enable,RIR, Ithreshratio, I):
    '''
    ####  turns minerals OFF (enable =0) if under their threshold%   ##############
    '''
    for i in range(0, len(enable)):        
        if enable[i]<>0 and  I[i] < max(I)*Ithreshratio:
            enable[i] = 0
            #logging.info("%s- init : %.4f >>> eliminated\t" %(mineral[i],I[i]))
    return enable


def Qthresholding(mineral, enable, Thresh, I):
    '''
    ####  turns minerals OFF (enable =0) if under their threshold%   ##############
    '''
    Q = I*enable/sum(I)*100
    
    for i in range(0, len(enable)):        
        if enable[i]<>0 and  Q[i] < Thresh[i]:
            enable[i] = 0
            #logging.info( "%s- init : %.1f >>> eliminated\t" %(mineral[i],Q[i]))
    return enable

def CleanMineralList(code, enable):
    '''
    #####  removes minerals in list if enable=0
    #####  restructures all lists in input
    '''
    codethresh = []
    enablethresh=[]
    
    for i in range(0, len(code)):
        if enable[i] == 1:
            codethresh.append(code[i])
            enablethresh.append(enable[i])
    return codethresh, enablethresh


def CleanMineralListPatDB (code, RIR, enable, Thresh, I, PatDB):
    '''
    #####  removes minerals in list if enable=0
    #####  restructures all lists in input
    #t0=time.time()
    '''
    codethresh = []
    RIRthresh=[]
    enablethresh=[]
    Threshthresh=[]
    Ithresh=[]
    PatDBthresh=[]
    
    for i in range(0, len(code)):
        if enable[i] == 1:
            codethresh.append(code[i])
            RIRthresh.append(RIR[i])
            enablethresh.append(enable[i])
            Threshthresh.append(Thresh[i])
            Ithresh.append(I[i])
            PatDBthresh.append(PatDB[i])
    #logging.info("list cleanup computing time = %.2f" %(time.time()-t0))
    return codethresh, RIRthresh, enablethresh, Threshthresh, Ithresh, PatDBthresh


def getKey(item):
    # used for sorting % results in decreasing order
    return item[5]


def sortQlistPatDB(nameref, code, RIR, enable, Thresh, I, PatDB):
    
    #######################   sorts lists in decreasing Q order      ############
    table = []
    for i in range(0,len(code)):
        table.append([nameref[code[i]], code[i], RIR[i], enable[i], Thresh[i], I[i], PatDB[i]])

    table.sort(key=getKey, reverse=True)
    
    codesorted =[]
    enablesorted=[]
    RIRsorted=[]
    Threshsorted=[]
    Isorted=[]
    PatDBsorted=[]
    
    for i in range(0,len(code)):
        codesorted.append(table [i][1])
        RIRsorted.append(table[i][2])
        enablesorted.append(table[i][3])
        Threshsorted.append(table[i][4])
        Isorted.append(table[i][5])
        PatDBsorted.append(table[i][6])
    
    return codesorted, RIRsorted, enablesorted, Threshsorted, Isorted, PatDBsorted    
    
def residualPatDB(I, Yexp, PatDB):
    """
    # Residual function for least square optimization of gaussian peaks 
    #  variable to refine:  I = intensity factors list  
    """
    I = abs(I)
    return (Yexp-sumPat(I, PatDB))


def QrefinelstsqPatDB(angle,diff,BGpoly, mineral, RIR, enable, Thresh, Iinit, PatDB):
    """
    This function refine the % values of the mineral in the mixture using least-square optimization method.
    Requires scipy
    """
    Keep_refining = True
    counter = 0 # counts iteration of the refinement.
    I = abs(np.array(Iinit))
    precision=[0.1, 0.05, 0.01]

    while Keep_refining:
        ## recalculate DB with current list
        counter +=1
        t0=time.time()
        logging.info( "counter = %s     minerals:%s", counter, sum(enable))
        Keep_refining = False
        Istart = I
            
        I, tossme = leastsq(residualPatDB, Istart, args=(diff-BGpoly, PatDB),  gtol=precision[counter-1])#, col_deriv=1, maxfev=100)
        I=abs(I)       
        logging.info( "end LSTSQ #%s",  counter)

        enable2 = Qthresholding(mineral, enable, Thresh, I)
        #I *= enable2
        
        if sum(enable2) < sum(enable):
            Keep_refining = True
            enable = enable2
            mineral, RIR, enable, Thresh, I, PatDB = CleanMineralListPatDB(code, RIR, enable, Thresh, I, PatDB)
        
        if counter < 3:
            Keep_refining = True

        logging.info( "lstsq computing time =%s", (time.time()-t0))
        
    return mineral, RIR, enable, Thresh, I, PatDB 
