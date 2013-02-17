####################################################
####################################################
#####################BANANARCHY#####################
##############Written by Kiril Staikov##############
####################################################
####################################################
#TO DO:
#------------
#8.) Write 4.3, where further bananas appear in the field of view after a hit.
#--  Write a step where he starts at new location each trial
#--  Write a step where many bananas appear


#1.) Figure out what to do with the window sizes for each training step, the speeds, distances, etc.  
#2.) Use assignment operators where possible
#3.) Use modulus if it would improve anything.
#4.) Use words for the logical operators for the sake of readability.
#5.) Use membership operators where possible, if they would improve anything.
#6.) Make if statements more readable by by starting new line after each conditional


#10.) Write method to initialize / import all config variables.
#11.) Set emails to send out one message (constructed throughout a trial) only between trials.
#12.) Add other 3D objects/models to the environment.
#13.) A separate nidaq class should be made, akin to the EEG class.
#14.) Get a higher quality banana
#---  Setup to use the rays as much as possible and maybe avoid having to do the whole clunky trig
#     calculations for the training steps < 4.0
#---  Make a GUI!
#
#============================================================================================================
#Version 0.3.2 Changelog
#-------------
#1) Adjusted to use only one banana, instead of unnecessarily using 3 in the code.
#2) Added 4.1, to remove the block on turning once the avatar has moved forward a bit.
#============================================================================================================
#Version 0.3.3 Changelog
#1) Added framework for email updates.
#   -Added email updates for the fogScheme
#   -Notification email for when new session begins.
#2) Added a palm tree to the field.
#============================================================================================================
#Version 0.3.4 Changelog
#1) Made NI-Daq use optional for testing purposes on computers with no nidaq.  However,
#   at this point, it is necessary to also comment out the 'nidaq = ctypes.windll.nicaiu' line
#   at the top of the main bananarchy file to ignore the nidaq.  It is not enough to just change
#   the variable in the config file to 0.
#2) The banana now rotates!
#3) Implemented collision rays instead of doing all the angle/header calculations.
#4) Added Training 4.2
#5) Added option to visualize collisions with the collision rays.
#6) Added option to change FOV boundary ray vectors on the fly.
#7) Training steps < 4.0 are broken now due to the collision rays.  Line 485 is where the problem
#   happens here.  Probably there is more to it.
#8) Training 3.1 fixed.
#9) Added system beep bell character as non-nidaq alternative reward.
#============================================================================================================
#
#Training Steps? 
#  0 = Final Task [BROKEN].
#
#1.x = Left-Right Training.  No background.  Crosshairs in center of screen,
#      and banana appears on left or right of crosshairs.  Subject has to
#      push joystick to right or left to align the crosshairs with the
#      bannaa.  Once the crosshairs hit the banana, the position is locked in place
#      until all the reward is dispensed.  Then the tasks restarts with the banana
#      in a new random location.
#1.1 = Left only. [Perhaps need to add a variable to 
#      control max distance, and vary within that.  That's what
#      increaseDistance and decreaseDistance should do.]
#1.2 = Right only. [Perhaps need to add a variable to 
#      control max distance, and vary within that.  That's what
#      increaseDistance and decreaseDistance should do.]
#1.3 = Both, randomized location and distance.
#
#2.x = Continuation of the left-right training in 1.x.  When the crosshairs
#      align wih the target, some reward is dispensed, but the positions
#      don't lock in and the crosshairs are allowed to leave the target, at
#      which point reward stops being dispensed, until the crosshairs and
#      target are aligned again.  The goal is to get the animal to leave
#      the crosshairs 
#2.1 = The window within which the crosshair has to fall is fairly large
#      Window to Left of Banana = 4; Right = 6.  They are different for technical
#      reasons I won't go into here.
#2.2 = Left = 3; Right = 5.
#2.3 = Left = 2; Right = 4.
#2.4 = Left = 1; Right = 3;
#2.5 = Left = 1; Right = 2; This is the final window.
#
#3.x = Introducing forward movement. 
#3.1 = Start out with banana centered, just go forward to get reward.
#3.2 = Left-right to banana, with crosshairs on it, then go forward to get rewarded again.
#      Forward movement is blocked until crosshair turns blue.  When crosshairs hit banana,
#      further turning is blocked.  Only forward movement is allowed.
#3.3 = Require him to stop on his own on the banana.  As soon as he moves forward a bit,
#      left and right turning is blocked, only more forward movement is allowed.    He is
#      rewarded up to 6 beeps at a time for turning until the crosshairs are blue, and then
#      he can only get more reward by actually going up to the banana.
#
#4.x = Introducing the environment. 
#4.0 = Starts off the same place as 3.3. Except the background is present and there is a massive,
#      and very dense fog over it.  Press F to remove the fog and eluminate the environment/backround
#      little by little.
#4.1 = Remove the block for turning after he moves forward.
#4.2 = Allow forward movement even when he's not with a blue cross.  




training = 4.2

nidaq = 0


from random import uniform

##########################
# Core PandaEPL settings.#
##########################

FOV = 60

# Movement.
linearAcceleration  = 30
if int(training) >= 3:
        fullForwardSpeed = 4
else:
        fullForwardSpeed    = 0
fullBackwardSpeed   = 0 
turningAcceleration = 50
if training == 3.1:
        fullTurningSpeed = 0
elif training >= 2:
        fullTurningSpeed    = 14
else:
        fullTurningSpeed = 200
turningLinearSpeed  = 2 # Factor

maxTurningLinearSpeed          = 90.0
minTurningLinearSpeedReqd      = 1.0
minTurningLinearSpeed          = 1.5
minTurningLinearSpeedIncrement = 0.5 

initialPos   = Point3(0, 0, 0.5)
avatarRadius = 0.5
cameraPos    = Point3(0, 0, 0.5)
friction     = .4
movementType = 'walking' # car | walking

# Instructions.
instructSize    = 0.075
#instructFont    = '/usr/share/fonts/truetype/freefont/FreeSans.ttf';  #Linux
#instructFont    = '/c/Windows/Fonts/times.ttf';                      # Windows 7
instructFont    = '/c/WINDOWS/Fonts/times.ttf';                 #Windows XP
instructBgColor = Point4(0, 0, 0, 1)
instructFgColor = Point4(1, 1, 1, 1)
instructMargin  = 0.06
instructSeeAll  = False

################################
# Experiment-specific settings.#
################################
# Font
#textFont = '/c/Windows/Fonts/times.ttf' # Used for the crosshairs plus sign
textFont = '/c/WINDOWS/Fonts/times.ttf' # Windows XP

# Bananas.
bananaDir  = './models/bananas/'
bananaZ    = 1
bananaScale = .5
bananaRotation = 0 # Rotation speed in degrees/frame.
bananaLocs = []
numBananas = 100
for i in range(0, numBananas):
	x = uniform(-12, 12)
	y = uniform(-15.5, 15.5)
	bananaLocs.append([x, y, 90])

if training > 0:
	numBananas = 1
	distance = .15
	bananaLocs[0] = [initialPos[0] - distance, initialPos[1] + 2, 90]
#	bananaLocs[1] = [initialPos[0], initialPos[1] + 2, 0]
#	bananaLocs[2] = [initialPos[0] + distance, initialPos[1] + 2, 90]

minDistance = 1.7
maxDistance = 1.8
minFwDistance = 2.7
maxFwDistance = 3.8
targetRayWindow = .25
fovRayVecX = 30

# Target header window, to the left and right
if (training > 2) & (training < 2.5):
        targetHwinL = 4 - (((training - 2) * 10) - 1)
        targetHwinR = 4 - (((training - 2) * 10) - 1)
else:
        targetHwinL = 2 #1.2 is sort of the boundary.
        targetHwinR = 2 #1.2 is sort of the boundary.

# Terrain, sky.
terrainModel  = './models/towns/final.bam'
terrainCenter = Point3(0,0,0)
skyModel      = './models/sky/sky.bam'
skyScale      = 1.6
treeModel     = './models/trees/palmTree.bam'
treeLoc       = Point3(11, 14, 0)
treeScale     = .0175

# Some reward pump parameters.
pulseInterval = 200 # in ms
if int(training) == 2:
        numBeeps = 50 # Number of pulses/beeps in typical reward sequence
else:
        numBeeps = 20

# (Non-default) command keys.
keyboard = Keyboard.getInstance()
keyboard.bind("exit", ["escape", "q"])
keyboard.bind("toggleDebug", ["escape", "d"])
keyboard.bind("left", "l")
keyboard.bind("right", "r")
keyboard.bind("restart", "y")
keyboard.bind("center", "m")
keyboard.bind("increaseDist", "i")
keyboard.bind("decreaseDist", "d")

if int(training) == 4:
        keyboard.bind("toggleFog", "f")
        keyboard.bind("decreaseFog", "v")
        keyboard.bind("increaseFovRay", "q")
        keyboard.bind("decreaseFovRay", "w")
        keyboard.bind("toggleCollisionView", ["escape", "c"])

joystick = Joystick.getInstance()
joystick.bind("toggleDebug", "joy_button0")

# Fog.
initialFogScheme  = 0
expFogColor       = Point3(0.4,0.4,0.4)
expFogDensity     = 1

# Email Info
emailNotifications = 0 # 1 = yes; 0 = no.
emailServer = 'smtp.gmail.com:465'
emailUsername = 'monkeyjn9'
emailPassword = 'MonkeyLabGiz'
emailFrom = 'Giuseppe Buffalo <monkeyjn9@gmail.com>'
emailTo = ['kstaikov@gmail.com', 'drewsolyst@gmail.com']
subject = 'Giz Log'
