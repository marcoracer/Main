####################################################
####################################################
#####################BANANARCHY#####################
##############Written by Kiril Staikov##############
####################################################
####################################################
from pandac.PandaModules import *
from pandaepl.common import *
import os
from numpy import *
import ctypes
import smtplib

#Remove Cursor, set Window title
props = WindowProperties()
props.setCursorHidden(True)
props.setTitle('Bananarchy')
base.win.requestProperties(props)

exp = Experiment.getInstance() #Get experiment instance.
vr = Vr.getInstance() #Get VR environment object.

# Set Session# to +1 the # of sessions the subject has data for so far.
if not os.access(exp.getExpDirectory(), os.F_OK):
    exp.setSessionNum(0)
else:
    i = 0
    while os.access(exp.getExpDirectory() + '/session_' + str(i), os.F_OK):
        i = i + 1
    exp.setSessionNum(i)

config = Conf.getInstance().getConfig() #Get configuration dictionary.

if config['nidaq'] == 1:

    from PyDAQmx.DAQmxConstants import *
    from PyDAQmx.DAQmxTypes import *
    from PyDAQmx.DAQmxFunctions import *
    from PyDAQmx.DAQmxCallBack import *

    class MyList(list):
        pass

    earliest = MyList()
    earliest.extend([0])
    id_a = create_callbackdata_id(earliest)

    def EveryNCallback_py(taskHandle, everyNsamplesEventType, nSamples, callbackData_ptr):
        latest = mstime()
        read = int32()
        eogData = zeros(2)
        DAQmxReadAnalogF64(eogTaskHandle,1,10.0,DAQmx_Val_GroupByScanNumber,eogData,2,byref(read),None)
        callbackdata = get_callbackdata_from_id(callbackData_ptr)
        Log.getInstance().writeLine([callbackdata[0], latest-callbackdata[0]], "EyeData",  [((eogData[0] * 231) + 30), ((eogData[1] * 176) - 43)])
        callbackdata[0] = latest
        #callbackdata = latest
        #print(callbackdata)
        return 0

    def DoneCallback_py(taskHandle, status, callbackData):
        print "Status",status.value
        return 0 # The function should return an integer

    eogSampRate = 240
    eogSampsPerChanToAcquire = 1
    eogTaskHandle = TaskHandle(1)

    DAQmxResetDevice('Dev1')    #Reset Device

    DAQmxCreateTask("",byref(eogTaskHandle))
    DAQmxCreateAIVoltageChan(eogTaskHandle,"Dev1/ai3","",DAQmx_Val_RSE,-5.0,5.0,DAQmx_Val_Volts,None)
    DAQmxCreateAIVoltageChan(eogTaskHandle,"Dev1/ai4","",DAQmx_Val_RSE,-5.0,5.0,DAQmx_Val_Volts,None)
    DAQmxCfgSampClkTiming(eogTaskHandle,"",eogSampRate,DAQmx_Val_Rising,DAQmx_Val_ContSamps,eogSampsPerChanToAcquire)

    #Callback
    EveryNCallback = DAQmxEveryNSamplesEventCallbackPtr(EveryNCallback_py)
    DoneCallback = DAQmxDoneEventCallbackPtr(DoneCallback_py)
    DAQmxRegisterEveryNSamplesEvent(eogTaskHandle,DAQmx_Val_Acquired_Into_Buffer,1,0,EveryNCallback,id_a)
    DAQmxRegisterDoneEvent(eogTaskHandle,0,DoneCallback,None)


class bananarchy:
    def __init__(self):
        """
        Initialize the experiment.
        """

        avatar = Avatar.getInstance()

        # Register Custom Log Entries
        Log.getInstance().addType("YUMMY",[("BANANA",basestring)], False) #This one corresponds to colliding with a banana.
        Log.getInstance().addType("EyeData", [("X", float), ("Y", float)], False)
        Log.getInstance().addType("NewTrial", [("Trial", int)], False)

        self.nidaqSetup(config) #Setup the basic NI-DAQ Hardware Controls
        self.loadEnvironment(config) #Load environment.

        # Set up fog.
        if int(config['training'] == 4) or (config['training'] == 5.2):
            self.fogScheme = config['initialFogScheme']
            self.setUpFog()
        self.completedTrial = 0


        #Log.getInstance().addType("EyeData", [("Z", numpy.ndarray)], True)

        # Create crosshairs around what seems to be the center of the screen
        self.cross = Text("cross", '+', Point3(0,0,0), config['instructSize'], Point4(1,0,0,config['xHairAlpha']), config['instructFont'])
        self.cross.setPos(Point3(-(self.cross.getWidth() / 2) + (.143995289939 * (self.cross.getWidth() / 2)), 0, (self.cross.getHeight() / 2) - (.326956465492 * (self.cross.getHeight() / 2))))
        self.fontSize = config['instructSize']
        self.xHairAlpha = config['xHairAlpha']

        # Register tasks to be performed between frames
        vr.addTask(Task("pumpOut",
                        lambda taskInfo:
                          self.pumpOut(config),
                        config['pulseInterval'])) # Outputs pulses to pump when reward is called for.

        vr.addTask(Task("trackHeader",
                        lambda taskInfo:
                          self.trackHeader(config, avatar))) # Monitors header position and calls for reward when necessary.

        vr.addTask(Task("eotEffect",
                        lambda taskInfo:
                          self.eotEffect(config),
                        config['eotEffectSpeed']))


        # Register the handling of keyboard events.
        vr.inputListen("toggleDebug",
                       lambda inputEvent:
                         Vr.getInstance().setDebug(not Vr.getInstance().isDebug()))
        vr.inputListen("restart", self.restart)
        if config['training'] > 0:
            vr.inputListen("left", self.left)
            vr.inputListen("center", self.center)
            vr.inputListen("right", self.right)
            vr.inputListen("increaseDist", self.increaseDist)
            vr.inputListen("decreaseDist", self.decreaseDist)
            vr.inputListen("toggleFog", self.toggleFog)
            vr.inputListen("decreaseFog", self.decreaseFog)
            vr.inputListen("increaseFovRay", self.increaseFovRay)
            vr.inputListen("decreaseFovRay", self.decreaseFovRay)
            vr.inputListen("toggleCollisionView", self.toggleCollisionView)
            vr.inputListen("increaseMaxFwDistance", self.increaseMaxFwDistance)
            vr.inputListen("decreaseMaxFwDistance", self.decreaseMaxFwDistance)
            vr.inputListen("increaseMinFwDistance", self.increaseMinFwDistance)
            vr.inputListen("decreaseMinFwDistance", self.decreaseMinFwDistance)
            vr.inputListen("upTurnSpeed", self.upTurnSpeed)
            vr.inputListen("downTurnSpeed", self.downTurnSpeed)
            vr.inputListen("decreaseXHairSize", self.decreaseXHairSize)
            vr.inputListen("increaseXHairSize", self.increaseXHairSize)
            vr.inputListen("decreaseXHairAlpha", self.decreaseXHairAlpha)
            vr.inputListen("increaseXHairAlpha", self.increaseXHairAlpha)



        #Build Collision Rays
        self.setupCollisionRays(config, avatar)

        if config['alignmentReward'] == 1:
            self.deliveredInitReward = 0
        else:
            self.deliveredInitReward = 1

        # Starting banana location
        self.maxFwDistance = config['maxFwDistance']
        self.minFwDistance = config['minFwDistance']
        self.fwDistanceIncrement = config['fwDistanceIncrement']

        self.fullTurningSpeed = config['fullTurningSpeed']
        self.maxFwDistance = config['maxFwDistance']
        self.minFwDistance = config['minFwDistance']
        self.trialNum = 0
        if config['training'] < 5:
            if config['training'] == 3.1:
                self.center(self, config, avatar)
            elif ((config['training'] == 1.1) | (random.randint(0, 2) > 0)) & (config['training'] != 1.2):
                self.left(self, config, avatar)
            else:
                self.right(self, config, avatar)
        else:
            self.restart(self)


        #Login into email account
        if config['emailNotifications'] == 1:
            self.email = smtplib.SMTP_SSL(config['emailServer'])
            self.email.login(config['emailUsername'], config['emailPassword'])
            self.msgHeaders = ("From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n" % (config['emailFrom'], ", ".join(config['emailTo']), config['subject']))
            self.sendEmail("New Session Started. Training = " + str(config['training']))

    def setupCollisionRays(self, config, avatar):
        #self.terrainModel.retrNodePath().reparentTo(render)
        #self.terrainModel.retrNodePath().setCollideMask(BitMask32.bit(1))
        #self.bananaModels[0].retrNodePath().setCollideMask(BitMask32.bit(1)) #Not necessary?
        #avatar.retrNodePath().reparentTo(self.bananaModels[0].retrNodePath())
        #avatar.retrNodePath().reparentTo(self.terrainModel.retrNodePath())
        self.collTrav = CollisionTraverser() #the collision traverser. we need this to perform collide in the end
        self.targetRay = avatar.retrNodePath().attachNewNode(CollisionNode('targetRayColNode'))
        self.targetRay.node().addSolid(CollisionRay(0, 0, 0, 0, 1, 0))
        self.targetRayRight = avatar.retrNodePath().attachNewNode(CollisionNode('targetRayRightColNode'))
        self.targetRayRight.node().addSolid(CollisionRay(0, 0, 0, -sin(deg2rad(-config['targetRayWindow'])), cos(deg2rad(-config['targetRayWindow'])), 0))
        self.targetRayLeft = avatar.retrNodePath().attachNewNode(CollisionNode('targetRayLeftColNode'))
        self.targetRayLeft.node().addSolid(CollisionRay(0, 0, 0, -sin(deg2rad(config['targetRayWindow'])), cos(deg2rad(config['targetRayWindow'])), 0))
        self.fovRayR = avatar.retrNodePath().attachNewNode(CollisionNode('fovRayRightColNode'))
        self.fovRayR.node().addSolid(CollisionRay(.25, 0, 0, -sin(deg2rad(-config['fovRayVecX'])), cos(deg2rad(-config['fovRayVecX'])), 0))
        self.fovRayL = avatar.retrNodePath().attachNewNode(CollisionNode('fovRayLeftColNode'))
        self.fovRayL.node().addSolid(CollisionRay(-.25, 0, 0, -sin(deg2rad(config['fovRayVecX'])), cos(deg2rad(config['fovRayVecX'])), 0))
        #avatar.retrNodePath().node().setIntoCollideMask(BitMask32.allOff()) #Not necessary?
        #self.theRay.node().setFromCollideMask(BitMask32.bit(1)) #Not necessary?
        self.targetRayColQueue = CollisionHandlerQueue()
        self.collTrav.addCollider(self.targetRay, self.targetRayColQueue)
        self.collTrav.addCollider(self.targetRayRight, self.targetRayColQueue)
        self.collTrav.addCollider(self.targetRayLeft, self.targetRayColQueue)

        self.fovRayLeftColQueue = CollisionHandlerQueue()
        self.collTrav.addCollider(self.fovRayL, self.fovRayLeftColQueue)
        self.fovRayRightColQueue = CollisionHandlerQueue()
        self.collTrav.addCollider(self.fovRayR, self.fovRayRightColQueue)

        self.collisionView = 0
        self.fovRayVecX = config['fovRayVecX']

    def sendEmail(self, msg):
        config = Conf.getInstance().getConfig()
        if config['emailNotifications'] == 1:
            self.email.sendmail(config['emailFrom'], config['emailTo'], self.msgHeaders + msg)

    def nidaqSetup(self, config):
        """
        Setup basic NI-DAQ hardware controls
        """

        self.beeps = 0   #Beep/Pulse counter
        self.reward = 2  #When set to 1, reward output is triggered.

        if config['nidaq'] == 1:



            #Initialize NI-DAQ Task Handles
            self.pumpTaskHandle = TaskHandle(0)
            #self.eogTaskHandle = TaskHandle(1)


            #Pump output parameters.
            outRate = 115
            outSamps = 15
            outMinV = 5.0
            outMaxV = 10.0
            self.outPumpData = zeros(outSamps, dtype = float64)


            #EOG input parameters.
            #eogSampRate = 240
            #eogSampsPerChanToAcquire = 1000

            nidaq = ctypes.windll.nicaiu

            #Setup NI-DAQ pump output task
            DAQmxCreateTask("", byref(self.pumpTaskHandle))
            DAQmxCreateAOVoltageChan(self.pumpTaskHandle, "Dev1/ao0", "", outMinV, outMaxV, DAQmx_Val_Volts, None)
            DAQmxCfgSampClkTiming(self.pumpTaskHandle, "", outRate, DAQmx_Val_Rising,
                                  DAQmx_Val_FiniteSamps, outSamps)
            #DAQmxWriteAnalogF64(self.pumpTaskHandle, int32(outSamps), 0, float64(-1),
            #                    DAQmx_Val_GroupByChannel, self.outPumpData, None, None)
            #One day should modify self.outPumpData to allow for the above. insead of below function.
            nidaq.DAQmxWriteAnalogF64( self.pumpTaskHandle,
                                          int32(outSamps),
                                          0,
                                          float64(-1),
                                          DAQmx_Val_GroupByChannel,
                                          self.outPumpData.ctypes.data,
                                          None,
                                          None)

            earliest[0] = mstime()
            DAQmxStartTask(eogTaskHandle)


##            #Setup NI-DAQ EOG input task
##            DAQmxCreateTask("",byref(self.eogTaskHandle))
##            DAQmxCreateAIVoltageChan(self.eogTaskHandle,"Dev1/ai3","",DAQmx_Val_RSE,-5.0,5.0,DAQmx_Val_Volts,None)
##            DAQmxCreateAIVoltageChan(self.eogTaskHandle,"Dev1/ai4","",DAQmx_Val_RSE,-5.0,5.0,DAQmx_Val_Volts,None)
##            DAQmxCfgSampClkTiming(self.eogTaskHandle,"",eogSampRate,DAQmx_Val_Rising,DAQmx_Val_ContSamps,eogSampsPerChanToAcquire)
##            self.startedEOG = 0
##            #Callback
##            eogTest = MyList()
##            id_a = create_callbackdata_id(eogTest)
##            EveryNCallback = DAQmxEveryNSamplesEventCallbackPtr(self.EveryNCallback_py)
##            DoneCallback = DAQmxDoneEventCallbackPtr(self.DoneCallback_py)
##            DAQmxRegisterEveryNSamplesEvent(self.eogTaskHandle,DAQmx_Val_Acquired_Into_Buffer,1000,0,EveryNCallback,id_a)
##            DAQmxRegisterDoneEvent(self.eogTaskHandle,0,DoneCallback,None)
##            DAQmxStartTask(self.eogTaskHandle)

##    def EveryNCallback_py(taskHandle, everyNsamplesEventType, nSamples, callbackData_ptr):
##        return 0
##        read = int32()
##        eogData = zeros(100)
##        DAQmxReadAnalogF64(self.eogTaskHandle,DAQmx_Val_Auto,10.0,DAQmx_Val_GroupByScanNumber,eogData,100,byref(read),None)
##        print(eogData[0:read*2])
#        for i in range(0, read.value):
#            VLQ.getInstance().writeLine("EyeData",  [eogData[2*(i-1)], eogData[(2*i)-1]])



##        callbackdata = get_callbackdata_from_id(callbackData_ptr)
##        read = int32()
##        data = zeros(2000)
##        DAQmxReadAnalogF64(taskHandle,DAQmx_Val_Auto,10.0,DAQmx_Val_GroupByScanNumber,data,2000,byref(read),None)
##        callbackdata.extend(data.tolist())
##        #print "Acquired total %d samples"%len(data)
##        return 0 # The function should return an integer
##    def DoneCallback_py(taskHandle, status, callbackData):
##        print "Status",status.value
##        return 0 # The function should return an integer

    def loadEnvironment(self, config):
        """
        Load terrain, sky, and bananas.
        """

        if (config['training'] == 0) or (int(config['training']) >= 4):
            # Load terrain.
            self.terrainModel = Model("terrain", config['terrainModel'],
                                      config['terrainCenter'])

            # When hitting an object that is part of the terrain, repel or slide?
            self.terrainModel.setCollisionCallback(MovingObject.handleRepelCollision)

            # Load sky.
            self.skyModel = Model("sky", config['skyModel'])
            self.skyModel.setScale(config['skyScale'])

            # Load palm tree.
            self.treeModel = Model("tree", config['treeModel'], config['treeLoc'])
            self.treeModel.setScale(config['treeScale'])

            # Load Skyscraper
            self.skyscraperModel = Model("skyscraper", config['skScraperModel'], config['skScraperLoc'])
            self.skyscraperModel.setScale(config['skScraperScale'])

            # Load Streetlight
            self.streetlightModel = Model("streetlight", config['strtLightModel'], config['strtLightLoc'])
            self.streetlightModel.setScale(config['strtLightScale'])

            # Load Windmill
##            self.windmillModel = Model("windmill", config['windmillModel'], config['windmillLoc'])
##            self.windmillModel.setScale(config['windmillScale'])
##            self.windmillModel.setH(config['windmillH'])


        # Load bananas.
        self.bananaModels = []
        for i in range(0, config['numBananas']):
            bananaModel = Model("banana"+str(i),
                               os.path.join(config['bananaDir'],"banana"+".bam"),
                               Point3(config['bananaLocs'][i][0],
                                      config['bananaLocs'][i][1],
                                      config['bananaZ']),
                               self.collideBanana)
            bananaModel.setScale(config['bananaScale'])
            self.bananaModels.append(bananaModel)
            self.bananaModels[i].setH(random.randint(0, 361))
            #self.bananaModels[i].retrNodePath().getChild(0).getChild(0).getChild(0).node().modifySolid(0).setRadius(.34)
            if config['training'] > 0:
                self.bananaModels[i].setStashed(1)



    def setUpFog(self):
        """
        Set up fog according to the current scheme.
        """
        # Get configuration dictionary.
        config = Conf.getInstance().getConfig()

        # Delete previously set fog.
        self.fog = None

        # No fog.
        if self.fogScheme == 0:
            pass
        # Exponential fog.
        elif self.fogScheme >= 1:
            self.fog = ExpFog("demoExpFog", config['expFogColor'],
                              config['expFogDensity'] * (.9**self.fogScheme))

        # Display fog everywhere.
        #Vr.getInstance().setFog(self.fog)
        self.skyModel.setFog(self.fog)
        self.terrainModel.setFog(self.fog)
        for i in range(0, config['numBananas']):
            self.bananaModels[i].setFog(self.fog)
        #self.bananaModels.setFog(self.fog)

    def toggleFog(self, inputEvent):
        """
        Cycle between different fog schemes.
        """
        TOTAL_FOG_SCHEMES = 70
        if self.fogScheme > 0:
            self.fogScheme    = (self.fogScheme+1) % TOTAL_FOG_SCHEMES
        self.sendEmail('fogScheme: ' + str(self.fogScheme))
        self.setUpFog()

    def decreaseFog(self, inputEvent):
        """
        Cycle between different fog schemes.
        """
        TOTAL_FOG_SCHEMES = 70
        if self.fogScheme != 1:
            self.fogScheme    = (self.fogScheme-1) % TOTAL_FOG_SCHEMES
        self.sendEmail('fogScheme: ' + str(self.fogScheme))
        self.setUpFog()

    def restart(self, inputEvent):
        '''
        Reload config file, give bananas new locations, make them visible, set new session number
        and return the subject to the original location, with no movement/momentum in any direction.
        '''
        self.trialNum += 1
        VLQ.getInstance().writeLine("NewTrial", [self.trialNum])

        config = Conf.getInstance().getConfig()

        self.cross.setColor(Point4(1, 0, 0, self.xHairAlpha))
        self.bananaModels[0].setStashed(1)
        avatar = Avatar.getInstance()
        avatar.setLinearAccel(0)
        avatar.setLinearSpeed(0)
        avatar.setTurningSpeed(0)
        avatar.setTurningAccel(0)

        self.deliveredLastReward = 0

        if (config['training'] < 4.3) or (config['training'] == 5.1):
            avatar.setH(0)
        if config['training'] < 5.2:
            avatar.setPos(config['initialPos'])
        avatar.setMaxTurningSpeed(self.fullTurningSpeed)
        if config['alignmentReward']:
            self.deliveredInitReward = 0

        if config['training'] < 5:
            if config['training'] == 3.1:
                self.center(self, config, avatar)
            else:
                randSide = random.randint(0, 2)
                if randSide < 1:
                    self.left(self, config, avatar)
                else:
                    self.right(self, config, avatar)
        else:
            for i in range(0, config['numBananas']):
                x = random.uniform(config['minDistance'], config['maxDistance'])
                y = random.uniform(config['minFwDistance'], config['maxFwDistance'])
                self.bananaModels[i].setPos(Point3(x, y, config['bananaZ']))
                self.bananaModels[i].setStashed(0)
                self.stashed = 0

    def left(self, inputEvent, config, avatar):
        self.bananaModels[0].setStashed(1)
        self.targetHeader = float('nan')
        self.bananaModels[0].retrNodePath().setPos(avatar.retrNodePath(), Point3(random.uniform(-config['minDistance'], -config['maxDistance']), random.uniform(self.minFwDistance, self.maxFwDistance), .5))
        self.bananaModels[0].setStashed(0)
        a = self.bananaModels[0].getPos()[0]
        b = self.bananaModels[0].getPos()[1]
        self.targetHeader = rad2deg(arccos(b/sqrt(square(a) + square(b))))

    def center(self, inputEvent, config, avatar):
        self.bananaModels[0].setStashed(1)
        self.targetHeader = float('nan')
        self.bananaModels[0].retrNodePath().setPos(avatar.retrNodePath(), Point3(0, random.uniform(self.minFwDistance, self.maxFwDistance), .5))
        self.bananaModels[0].setStashed(0)
        a = self.bananaModels[0].getPos()[0]
        b = self.bananaModels[0].getPos()[1]
        self.targetHeader = rad2deg(arccos(b/sqrt(square(a) + square(b))))

    def right(self, inputEvent, config, avatar):
        self.bananaModels[0].setStashed(1)
        self.targetHeader = float('nan')
        self.bananaModels[0].retrNodePath().setPos(avatar.retrNodePath(), Point3(random.uniform(config['minDistance'], config['maxDistance']), random.uniform(self.minFwDistance, self.maxFwDistance), .5))
        self.bananaModels[0].setStashed(0)
        a = self.bananaModels[0].getPos()[0]
        b = self.bananaModels[0].getPos()[1]
        self.targetHeader = -rad2deg(arccos(b/sqrt(square(a) + square(b))))

    def increaseDist(self, inputEvent):
        pass

    def decreaseDist(self, inputEvent):
        pass

    def increaseFovRay(self, inputEvent):
        self.fovRayVecX += 1
        self.fovRayR.node().modifySolid(0).setDirection(-sin(deg2rad(-self.fovRayVecX)), cos(deg2rad(-self.fovRayVecX)), 0)
        self.fovRayL.node().modifySolid(0).setDirection(-sin(deg2rad(self.fovRayVecX)), cos(deg2rad(self.fovRayVecX)), 0)
        self.sendEmail("FOV Window: " + str(self.fovRayVecX))
        print('fovRayVecX: ' + str(self.fovRayVecX))


    def decreaseFovRay(self, inputEvent):
        self.fovRayVecX -= 1
        self.fovRayR.node().modifySolid(0).setDirection(-sin(deg2rad(-self.fovRayVecX)), cos(deg2rad(-self.fovRayVecX)), 0)
        self.fovRayL.node().modifySolid(0).setDirection(-sin(deg2rad(self.fovRayVecX)), cos(deg2rad(self.fovRayVecX)), 0)
        self.sendEmail("FOV Window: " + str(self.fovRayVecX))
        print('fovRayVecX: ' + str(self.fovRayVecX))

    def toggleCollisionView(self, inputEvent):
        self.collisionView = (self.collisionView + 1) % 2
        if self.collisionView == 1:
            self.cV = self.collTrav.showCollisions(render)
        else:
            render.node().removeChild(render.node().findChild(self.cV))

    def increaseMaxFwDistance(self, inputEvent):
        self.maxFwDistance += self.fwDistanceIncrement
        print('maxFwDistance: ' + str(self.maxFwDistance))

    def decreaseMaxFwDistance(self, inputEvent):
        self.maxFwDistance -= self.fwDistanceIncrement
        print('maxFwDistance: ' + str(self.maxFwDistance))

    def increaseMinFwDistance(self, inputEvent):
        self.minFwDistance +=  self.fwDistanceIncrement
        print('minFwDistance: ' + str(self.minFwDistance))

    def decreaseMinFwDistance(self, inputEvent):
        self.minFwDistance -= self.fwDistanceIncrement
        print('minFwDistance: ' + str(self.minFwDistance))

    def upTurnSpeed(self, inputEvent):
        avatar = Avatar.getInstance()
        self.fullTurningSpeed += .1
        if avatar.getMaxTurningSpeed() > 0:
            avatar.setMaxTurningSpeed(self.fullTurningSpeed)
        print("fullTurningSpeed: " + str(self.fullTurningSpeed))

    def downTurnSpeed(self, inputEvent):
        avatar = Avatar.getInstance()
        self.fullTurningSpeed -= .1
        if avatar.getMaxTurningSpeed() > 0:
            avatar.setMaxTurningSpeed(self.fullTurningSpeed)
        print("fullTurningSpeed: " + str(self.fullTurningSpeed))

    def decreaseXHairSize(self,inputEvent):
        self.cross.setScale(self.fontSize - .01)
        self.fontSize -= .01
        self.cross.setPos(Point3(-(self.cross.getWidth() / 2) + (.143995289939 * (self.cross.getWidth() / 2)), 0, (self.cross.getHeight() / 2) - (.326956465492 * (self.cross.getHeight() / 2))))
        print("Crosshair Size: " + str(self.fontSize))


    def increaseXHairSize(self, inputEvent):
        self.cross.setScale(self.fontSize + .01)
        self.fontSize += .01
        self.cross.setPos(Point3(-(self.cross.getWidth() / 2) + (.143995289939 * (self.cross.getWidth() / 2)), 0, (self.cross.getHeight() / 2) - (.326956465492 * (self.cross.getHeight() / 2))))
        print("Crosshair Size: " + str(self.fontSize))

    def decreaseXHairAlpha(self, inputEvent):
        self.xHairAlpha -= .01
        self.cross.setColor(Point4(self.cross.getColor()[0], self.cross.getColor()[1], self.cross.getColor()[2], self.xHairAlpha))
        print("Crosshair Alpha: " + str(self.xHairAlpha))

    def increaseXHairAlpha(self, inputEvent):
        self.xHairAlpha += .01
        self.cross.setColor(Point4(self.cross.getColor()[0], self.cross.getColor()[1], self.cross.getColor()[2], self.xHairAlpha))
        print("Crosshair Alpha: " + str(self.xHairAlpha))
        DAQmxStopTask(eogTaskHandle)

    def start(self):
        """
        Start the experiment.
        """

        Experiment.getInstance().start()

    def collideBanana(self, collisionInfoList):
        """
        Handle the participant colliding with a banana.
        """
        config = Conf.getInstance().getConfig()

        # ID of the banana the participant collided with.
        banana = collisionInfoList[0].getInto().getIdentifier()
        self.collided = collisionInfoList[0].getInto()

        # Log collision.
        VLQ.getInstance().writeLine("YUMMY", [banana])

        # Upon touching banana, repel movement.  Banana disappears.



        # Reward

        #self.reward = 1
        #Make sure enough of banana is visible on screen to avoid rewards without actually seeing the banana on the screen.
        camNodePath = Camera.getDefaultCamera().retrNodePath()
        if (self.cross.getColor()[0] != 1) and (self.collided.retrNodePath().getName() == self.targetRayColQueue.getEntry(3).getIntoNodePath().getName()) and camNodePath.node().isInView(self.collided.retrNodePath().getPos(camNodePath)) and (camNodePath.node().isInView(self.collided.retrNodePath().getPos(camNodePath) + (0, .1, 0)) or camNodePath.node().isInView(self.collided.retrNodePath().getPos(camNodePath) + (0, -.1, 0))) and (camNodePath.node().isInView(self.collided.retrNodePath().getPos(camNodePath) + (.1, 0, 0)) or camNodePath.node().isInView(self.collided.retrNodePath().getPos(camNodePath) + (-.1, 0, 0))):
            MovingObject.handleRepelCollision(collisionInfoList)
            if config['training'] < 3.1:
                self.targetHeader = float('nan')
            Avatar.getInstance().setMaxTurningSpeed(0)
            self.cross.setColor(Point4(0, 1, 0, self.xHairAlpha))
            self.reward = 1
        #else:
        #    MovingObject.handleSlideCollision(collisionInfoList)


    def eotEffect(self, config):
        if self.completedTrial == 1:
            self.decreaseFog(self)
            if self.fogScheme == 1:
                self.completedTrial = 0
                self.restart(self)
        else:
            self.toggleFog(self)

    def pumpOut(self, config):
        """
        Carry out reward delivery process when self.reward is set to 1.
        """

        if (self.beeps < config['numBeeps']) & (self.reward == 1):
            if config['nidaq'] == 1:
                DAQmxStartTask(self.pumpTaskHandle)
                DAQmxWaitUntilTaskDone(self.pumpTaskHandle, DAQmx_Val_WaitInfinitely)
                DAQmxStopTask(self.pumpTaskHandle)
            else:
                print('Beep: ' + str(self.beeps + 1))
                #print('\a')
            self.beeps = self.beeps + 1
            if self.beeps == 6:
                self.deliveredInitReward = 1
        else:
            self.beeps = 0
            self.reward = 0
            if self.cross.getColor()[1] == 1:
                if (self.stashed == config['numBananas'] - 1) and (self.deliveredLastReward == 0) and (config['lastBananaBonus'] == 1):
                    self.reward = 1
                    self.deliveredLastReward = 1
                elif (config['training'] < 5):
                    self.restart(self)
                else:
                    self.collided.setStashed(1)
                    self.stashed += 1
                    self.cross.setColor(Point4(1, 0, 0, self.xHairAlpha))
                    avatar = Avatar.getInstance()
                    avatar.setMaxTurningSpeed(self.fullTurningSpeed)
                    if config['alignmentReward']:
                        self.deliveredInitReward = 0
                    if self.stashed == config['numBananas']:
                        if config['eotEffect'] == 1:
                            self.completedTrial = 1
                        else:
                            self.restart(self)
                    elif self.stashed == config['bananaReplenishment']:
                        for i in range(0, config['numBananas']):
                            if self.bananaModels[i].isStashed() == 1:
                                x = random.uniform(config['minDistance'], config['maxDistance'])
                                y = random.uniform(config['minFwDistance'], config['maxFwDistance'])
                                self.bananaModels[i].setPos(Point3(x, y, config['bananaZ']))
                                self.bananaModels[i].setStashed(0)
                                self.stashed -= 1




    def trackHeader(self, config, avatar):
        """
        Monitor the header between every frame and perform the relevant
        header-dependent functions.
        """
        
        self.collTrav.traverse(render)
        self.targetRayColQueue.sortEntries()

        if self.cross.getColor()[1] != 1:
            for i in range(0, config['numBananas']):
                self.bananaModels[i].setH(self.bananaModels[i].getH() + (config['bananaRotation'] * (-1)**(i+1))) #Rotate the banana

        hedder = avatar.getH()

        #Maintain boundaries to ensure Avatar never rotates so much that banana disappears from screen
        if config['training'] < 4.2:
            if (self.bananaModels[0].getPos()[0] < 0) & (-hedder >= (config['FOV']/2 - 1) - abs(self.targetHeader)):
                avatar.setLinearAccel(0)
                avatar.setLinearSpeed(0)
                avatar.setTurningSpeed(0)
                avatar.setTurningAccel(0)
                avatar.setH(hedder+.02)
            elif (self.bananaModels[0].getPos()[0] > 0) & (hedder >= (config['FOV']/2 - 1) - abs(self.targetHeader)):
                avatar.setLinearAccel(0)
                avatar.setLinearSpeed(0)
                avatar.setTurningSpeed(0)
                avatar.setTurningAccel(0)
                avatar.setH(hedder-.02)

            if (self.bananaModels[0].getPos()[0] < 0) & (hedder >= (config['FOV']/2 - 1) + self.targetHeader):
                avatar.setLinearAccel(0)
                avatar.setLinearSpeed(0)
                avatar.setTurningSpeed(0)
                avatar.setTurningAccel(0)
                avatar.setH(hedder-.02)
            elif (self.bananaModels[0].getPos()[0] > 0) & (hedder <= -(config['FOV']/2 - 1) + self.targetHeader):
                avatar.setLinearAccel(0)
                avatar.setLinearSpeed(0)
                avatar.setTurningSpeed(0)
                avatar.setTurningAccel(0)
                avatar.setH(hedder+.02)
        elif (config['training'] != 4.25) and (config['training'] != 4.35) and (config['training'] < 5):
            self.fovRayRightColQueue.sortEntries()
            self.fovRayLeftColQueue.sortEntries()
            if self.bananaModels[0].retrNodePath().getName() == self.fovRayRightColQueue.getEntry(0).getIntoNodePath().getName():
                avatar.setLinearAccel(0)
                avatar.setLinearSpeed(0)
                avatar.setTurningSpeed(0)
                #avatar.setTurningAccel(0)
                avatar.setMaxForwardSpeed(0)
                avatar.setH(hedder-.1)
            elif self.bananaModels[0].retrNodePath().getName() == self.fovRayLeftColQueue.getEntry(0).getIntoNodePath().getName():
                avatar.setLinearAccel(0)
                avatar.setLinearSpeed(0)
                avatar.setTurningSpeed(0)
                #avatar.setTurningAccel(0)
                avatar.setMaxForwardSpeed(0)
                avatar.setH(hedder+.1)
            else:
                avatar.setMaxForwardSpeed(config['fullForwardSpeed'])

        #What to do when the current header matches the target header:
        #Reward, make crosshairs blue, and freeze rotation until reward is complete.  Then hide banana, reset position,
        #allow rotation, and present new target banana in random location.
        #for i in range(self.targetRayColQueue.getNumEntries()):
            #entry = self.targetRayColQueue.getEntry(i)
            #print entry
            #print(self.bananaModels[0].retrNodePath().getChild(0).getChild(0).getChild(0).getBounds()
        #print(self.bananaModels[0].retrNodePath().getChild(0).getChild(0).getChild(0).getClassType())
        #self.bananaModels[0].retrNodePath().getChild(0).getChild(0).getChild(0).node().modifySolid(0).setRadius(.2)
##        #print(self.targetRayColQueue.getEntries())
        #self.bananaModels[0].retrNodePath().node().setBounds(BoundingSphere(self.bananaModels[0].getPos(), .5))
        #print(self.bananaModels[0].retrNodePath().node().getBounds())
        #self.bananaModels[0].retrNodePath().node().setFinal(1)
        #self.bananaModels[0].retrNodePath().showBounds()

        if config['training'] < 4.0:
            alignment = (hedder < self.targetHeader + config['targetHwinL']) & (hedder > self.targetHeader - config['targetHwinR'])
        else:
            alignment = False
            for i in range(self.targetRayColQueue.getNumEntries()):
                entry = self.targetRayColQueue.getEntry(i)
                if entry.getIntoNodePath().getName().startswith('banana'):#[0:6] == self.bananaModels[0].retrNodePath().getName()[0:6]:
                    alignment = True
            #alignment = self.bananaModels[0].retrNodePath().getName()[0:6] == self.targetRayColQueue.getEntry(3).getIntoNodePath().getName()[0:6]

        if alignment:
            if int(config['training']) < 3:
                self.reward = 1
            if (config['training'] >= 3.2) & (self.deliveredInitReward == 0) & (self.beeps < 6):
                self.reward = 1
                #self.deliveredInitReward = 1
            elif self.cross.getColor()[1] == 1:
                self.reward = 1
            elif config['training'] >= 3.2:
                self.reward = 0

            if self.cross.getColor()[1] != 1:
                self.cross.setColor(Point4(0, 0, 1, self.xHairAlpha))

            avatar.setMaxForwardSpeed(config['fullForwardSpeed'])

            if (int(config['training']) == 1) or (config['training'] == 3.2) or ((config['training'] >= 3.3) and (avatar.getPos()[1] > 0) and (config['training'] < 4.1)):
                avatar.setMaxTurningSpeed(0)
            if (self.beeps >= config['numBeeps']) & (config['training'] < 3.1):
                self.bananaModels[0].setStashed(1)
                avatar.setH(0)
                if ((config['training'] == 1.1) | (random.randint(0, 2) < 1)) & (config['training'] != 1.2):
                    self.left(self, config)
                else:
                    self.right(self, config)

                self.cross.setColor(Point4(1, 0, 0, self.xHairAlpha))
                avatar.setMaxTurningSpeed(self.fullTurningSpeed)
        else:
            if config['training'] >= 3.3:
                self.reward = 0
            if self.reward == 0:
                self.cross.setColor(Point4(1, 0, 0, self.xHairAlpha))
                avatar.setMaxTurningSpeed(self.fullTurningSpeed) #To solve the controls freezing bug
                if config['training'] < 4.2:
                    avatar.setMaxForwardSpeed(0)
            if int(config['training']) <= 3:
                if self.beeps >= 5:
                    self.reward = 0

##        if config['nidaq'] == 1:
##            if self.startedEOG == 0:
##                DAQmxStartTask(self.eogTaskHandle)
##                self.startedEOG = 1
##
##            read = int32()
##            eogData = zeros(100)
##            DAQmxReadAnalogF64(self.eogTaskHandle,DAQmx_Val_Auto,10.0,DAQmx_Val_GroupByScanNumber,eogData,100,byref(read),None)
##            #VLQ.getInstance().writeLine("EyeData", [eogData[0:read.value*2]])
##            #VLQ.getInstance().writeLine("EyeData", [eogData[0], eogData[1]])
##            if read.value >= 1:
##                for i in range(0, read.value):
##                    VLQ.getInstance().writeLine("EyeData",  [eogData[2*(i-1)], eogData[(2*i)-1]])
##
# Create a new instance of the experiment and start it up.
#DAQmxStartTask(eogTaskHandle)
bananarchy().start()
