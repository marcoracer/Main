# Copyright (c) 2007-2012, Michael J. Kahana.
#
# This file is part of PandaEPL.
#
# PandaEPL is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 2.1 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Author: Alec Solway
# URL: http://memory.psych.upenn.edu/PandaEPL

from Camera               import Camera
from Conf                 import Conf
from Log                  import *
from Model                import *
from MovingObject         import MovingObject
from Tuples               import *
from UniquelyIdentifiable import UniquelyIdentifiable
from VideoLogQueue        import VideoLogQueue as VLQ
from ptime                import *
from pandac.PandaModules  import NodePath, PandaNode

class Compass(MovingObject, UniquelyIdentifiable):
    """
    The Compass.
    """

    singletonInstance = None

    Log.getInstance().addType("COMPASS_INIT", [])
    Log.getInstance().addType("COMPASS_CREATED", [])
    Log.getInstance().addType("COMPASS_MODEL", [('modelId',basestring)])

    def __init__(self):
        """
        Creates a Compass object. Client scripts should treat
        Compass as a singleton and get references to it using
        getInstance() instead of creating a new instance.
        """
        Log.getInstance().writeLine((mstime(), 0), "COMPASS_INIT", [])

        self.model = None
        identifier = "PandaEPL_compass"
        UniquelyIdentifiable.__init__(self, identifier)

        # Create a dummy Panda3D node to represent the compass.
        # Models can be attached/detached if the compass's graphic
        # is set/changed.
        dummyNode = PandaNode(identifier)
        
        # Pass the identifier and dummy node to the parent class,
        # and tell it that this is a valid from collision object.
        MovingObject.__init__(self, identifier, NodePath(dummyNode), True)

        # Listen for configuration changes.
        Conf.getInstance().registerObserver(self.configEvent)

        Log.getInstance().writeLine((mstime(), 0), "COMPASS_CREATED", [])

    def __del__(self):
        """
        Destroys the object.
        """
        MovingObject.__del__(self)
        UniquelyIdentifiable.__del__(self)

    def configEvent(self, eventName, **dargs):
        """
        Updates the Compass with the current configuration
        values. Generally called by the Conf class
        and should not be used by PandaEPL client code
        directly.
        """
        config = Conf.getInstance().getConfig()

        if eventName == "configChanged":
            self.setMaxForwardSpeed(config['fullForwardSpeed'])
            self.setMaxBackwardSpeed(config['fullBackwardSpeed'])
            self.setMaxTurningSpeed(config['fullTurningSpeed'])
            self.setPos(config['initialPos'])
            if config.has_key('compassModel'):
                # If old model is a default model, delete it.
                if self.model!=None and self.model.getIdentifier() == "PandaEPL_compassModel":
                    self.model = None
                self.setModel(Model("PandaEPL_compassModel", config['compassModel'], Point3(0,0,0)))
            # Using avatar radius for now!
            if config.has_key('avatarRadius'):
                self.setCollisionRadius(config['avatarRadius'])

            # Set the near clipping plane to be closer than the avatar's 
            # radius, so that objects don't disappear when the user comes
            # right up on them. Here we arbitrarily set it to half the
            # collision radius.
            # Camera.getDefaultCamera().retrNodePath().node().getLens().setNear(self.getCollisionRadius()/2.0)

    def getInstance(cls):
        """
        Returns a reference to (the one and only) Compass instance.
        Use this instead of instantiating a copy directly.
        """
        if Compass.singletonInstance == None:
            Compass.singletonInstance = Compass()
        return Compass.singletonInstance

    getInstance = classmethod(getInstance)

    def getModel(self):
        """
        Returns the model representing the compass.
        """
        return self.model

    def setModel(self, newModel):
        """
        Sets the model representing the compass.
        """
        # If there's already a model attached, detach it.
        if self.model != None:
            self.model.retrNodePath().reparentTo(base.render)

        self.model = newModel

        # Attach the underlying Panda3D node to the 
        # compass dummy node.
        self.model.retrNodePath().reparentTo(self.nodePath)

        # Reset collision sphere to stretch around model.
        self.setCollisionRadius()

        # Log the event.
        VLQ.getInstance().writeLine("COMPASS_MODEL", [self.model.getIdentifier()])

