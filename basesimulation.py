from direct.showbase.ShowBase import ShowBase
from panda3d.core import AmbientLight, DirectionalLight, Vec3, Vec4
from direct.actor.Actor import Actor
from panda3d.core import PointLight, KeyboardButton, MouseWatcher
from panda3d.core import LineSegs, NodePath
import random
from direct.task import Task
import numpy as np
from panda3d.core import Mat3, deg2Rad
import math
import sys
from panda3d.core import Point3, TransparencyAttrib,TextNode
from direct.gui.DirectGui import DirectFrame, DirectButton, DGG, DirectCheckButton
from panda3d.core import OrthographicLens,PerspectiveLens
import os
from panda3d.core import Filename

from panda3d.core import getModelPath
from panda3d.core import loadPrcFile


loadPrcFile('settings.prc')

class BaseSimulation(ShowBase):
    
    def __init__(self):
        ShowBase.__init__(self)

        self.freeze=False
    
        self.lens2D=None
        self.lens3D=None

        self.models={}


        current_dir = os.path.dirname(__file__)
        model_dir = os.path.join(current_dir, 'models')
        print(f"Adding {model_dir} to the model path")
        # Add the model directory to the model path
        getModelPath().prependPath(model_dir)
        print(f"new ModelPath = {getModelPath()}")

        # Schedule the update task
        self.taskMgr.add(self.runSimulation, "update simulation")


    def loadModels(self, modelMappings):
       
        for modelName in modelMappings.keys():
            modelDef = modelMappings[modelName]

            path = modelDef["path"]
            model = self.loader.loadModel(path)
            self.models[modelName] = model

        self.modelMappings=modelMappings

    def getModel(self, modelName):
        return self.models.get(modelName, None)
    
    def getModelScaling(self, modelName):
        modelDef = self.modelMappings[modelName]
        return modelDef["scale"]

    def setupLights(self):
        # Ambient Light
        ambientLight = AmbientLight("ambientLight")
        ambientLight.setColor(Vec4(.2, .2, .2, 1))
        self.render.setLight(self.render.attachNewNode(ambientLight))

        # Directional light
        directionalLight = DirectionalLight("directionalLight")
        directionalLight.setDirection(Vec3(0, -45, -45))
        directionalLight.setColor(Vec4(0.8, 0.8, 0.8, 1))
        self.render.setLight(self.render.attachNewNode(directionalLight))


    def setupNavigationControls(self):
        self.userInputs = {
            "left": 0, "right": 0, "forward": 0, "back": 0, "up": 0, "down": 0,
            "cam-left": 0, "cam-right": 0, "mouse1": 0, "mouse2": 0, "mouse3": 0
        }

        self.accept("a", self.recordUserInput, ["left", True])
        self.accept("a-up", self.recordUserInput, ["left", False])
        self.accept("a", self.recordUserInput, ["left", True])
        self.accept("a-up", self.recordUserInput, ["left", False])
        self.accept("d", self.recordUserInput, ["right", True])
        self.accept("d-up", self.recordUserInput, ["right", False])
        self.accept("w", self.recordUserInput, ["forward", True])
        self.accept("w-up", self.recordUserInput, ["forward", False])
        self.accept("s", self.recordUserInput, ["back", True])
        self.accept("s-up", self.recordUserInput, ["back", False])
        self.accept("arrow_up", self.recordUserInput, ["up", True])
        self.accept("arrow_up-up", self.recordUserInput, ["up", False])
        self.accept("arrow_down", self.recordUserInput, ["down", True])
        self.accept("arrow_down-up", self.recordUserInput, ["down", False])
        self.accept("arrow_left", self.recordUserInput, ["cam-left", True])
        self.accept("arrow_left-up", self.recordUserInput, ["cam-left", False])
        self.accept("arrow_right", self.recordUserInput, ["cam-right", True])
        self.accept("arrow_right-up", self.recordUserInput, ["cam-right", False])

        

        # Mouse buttons
        self.accept("mouse1", self.recordUserInput, ["mouse1", True])  # Left click
        self.accept("mouse1-up", self.recordUserInput, ["mouse1", False])
        self.accept("mouse3", self.recordUserInput, ["mouse3", True])  # Right click
        self.accept("mouse3-up", self.recordUserInput, ["mouse3", False])
        self.accept("mouse2", self.recordUserInput, ["mouse2", True])  # Right click
        self.accept("mouse2-up", self.recordUserInput, ["mouse2", False])

        self.taskMgr.add(self.moveObserver, "moveObserver")
        
        # Speed of the camera movement
        self.movementSpeed = 500.0
        self.rotationSpeed = 1  # Degrees per task update

        # Set up a key to toggle the drawer
        self.accept("space", self.toggleDrawer)
        self.accept("p", self.toggleFreeze)


    def recordUserInput(self, input, value):
        self.userInputs[input] = value

    def moveObserver(self, task):
        dt = globalClock.getDt()        

        # Handle mouse movements
        if self.mouseWatcherNode.hasMouse():
            mpos = self.mouseWatcherNode.getMouse()  # get the mouse position

            if self.userInputs["mouse1"]:  # Left click (move)
                self.camera.setX(self.camera, mpos.getX() * self.movementSpeed * dt)
                self.camera.setY(self.camera, -mpos.getY() * self.movementSpeed * dt)

            if self.userInputs["mouse3"]:  # Right click (rotate)
                self.camera.setH(self.camera.getH() - mpos.getX() * self.rotationSpeed)
                self.camera.setP(self.camera.getP() + mpos.getY() * self.rotationSpeed)

        # Handle keyboard inputs for movement and rotation
        if self.userInputs["left"]: self.camera.setX(self.camera, -self.movementSpeed * dt)
        if self.userInputs["right"]: self.camera.setX(self.camera, self.movementSpeed * dt)
        if self.userInputs["forward"]: self.camera.setY(self.camera, self.movementSpeed * dt)
        if self.userInputs["back"]: self.camera.setY(self.camera, -self.movementSpeed * dt)
        if self.userInputs["up"]: self.camera.setZ(self.camera, self.movementSpeed * dt)
        if self.userInputs["down"]: self.camera.setZ(self.camera, -self.movementSpeed * dt)

        # Camera rotation
        if self.userInputs["cam-left"]: self.camera.setH(self.camera.getH() + self.rotationSpeed * dt)
        if self.userInputs["cam-right"]: self.camera.setH(self.camera.getH() - self.rotationSpeed * dt)

        return task.cont

    def toggleFreeze(self, status=None):
        self.freeze = not self.freeze

    def setupCamera(self):

        self.set3DCamera()        
        self.lens3D = self.cam.node().getLens()

    def set3DCamera(self):
        cameraDistance = 2000  # Adjust as necessary
        cameraHeight = 500
        cameraHeight=0
        self.camera.setPos(cameraDistance, cameraDistance, cameraHeight)
        self.camera.lookAt(0, 0, 0)  # Look at the center of the scene

    def setTopView(self):
        # Set camera for a top-down view of the scene
        self.camera.setPos(0, 0, 5000)  # Adjust as necessary for your scene
        self.camera.lookAt(0, 0, 0)

    def setSideView(self):
        # Set camera for a side view of the scene
        self.camera.setPos(0, 5000, 0)  # Adjust as necessary for your scene
        self.camera.lookAt(0, 0, 0)

    def activate2DView(self):

        lens = self.lens2D
        if lens==None:
            lens = OrthographicLens()
            lens.setFilmSize(3200, 1800)  
            lens.setNearFar(-10000,10000)
            self.lens2D = lens
        self.cam.node().setLens(lens)
    
    def activate3DView(self):

        lens = self.lens3D
        self.cam.node().setLens(lens)   

    def runSimulation(self, task):
        print("Implement 'BaseSimulation.runSimulation' ")



class BaseSimulationWithDrawer(BaseSimulation):
    
    def __init__(self):
        BaseSimulation.__init__(self)
        self.orthographic=False
 
    def setupDrawer(self):
      # Create a frame that acts as a drawer
        
        drawerPosition = -1.5
        margin=0.43
        btnWidth = 10  # Adjust as needed
        btnHeight = 2  # Adjust as needed
        btnSize = (-btnWidth/2, btnWidth/2, -btnHeight/2, btnHeight/2)

        # Create a frame that acts as a drawer
        self.drawer = DirectFrame(frameColor=(0.1, 0.1, 0.1, 0.8),
                                  frameSize=(drawerPosition, -0.8, -1.0, 1.0),
                                  pos=(0, 0, 0))
        self.drawer.setTransparency(TransparencyAttrib.MAlpha)

        normalColor = (0.2, 0.2, 0.8, 1)  # Normal state color
        rolloverColor = (0.3, 0.3, 0.9, 1)  # Rollover state color


        # Create buttons within the drawer
        self.freeViewButton = DirectButton(text="Free View", scale=0.05, 
                                          command=self.set3DCamera, parent=self.drawer,
                                          pos=(drawerPosition + margin , 0, 0.61),  # Adjust pos as needed
                                          frameSize=btnSize,
                                          text_align=TextNode.ACenter,  # Center text
                                          relief=DGG.FLAT,  # Flat relief for modern look
                                          frameColor=normalColor,  # Normal color
                                          )
        self.freeViewButton['frameColor'] = (normalColor, rolloverColor, rolloverColor, normalColor)


        self.topViewButton = DirectButton(text="Top View", scale=0.05, 
                                          command=self.setTopView, parent=self.drawer,
                                          pos=(drawerPosition + margin , 0, 0.5),  # Adjust pos as needed
                                          frameSize=btnSize,
                                          text_align=TextNode.ACenter,  # Center text
                                          relief=DGG.FLAT,  # Flat relief for modern look
                                          frameColor=normalColor,  # Normal color
                                          )
        self.topViewButton['frameColor'] = (normalColor, rolloverColor, rolloverColor, normalColor)


        self.sideViewButton = DirectButton(text="Side View", scale=.05, 
                                           command=self.setSideView, parent=self.drawer,
                                           pos=(drawerPosition + margin , 0, 0.39),  # Adjust pos as needed
                                           frameSize=btnSize,
                                           text_align=TextNode.ACenter,
                                           relief=DGG.FLAT,
                                           frameColor=normalColor,
                                           )


        # Add button
        self.toggle2DCheckbox = DirectCheckButton(text = "2D Render" ,
                                                  parent=self.drawer,
                                                  scale=.05,
                                                  command=self.toggle2DView,
                                                  pos=(drawerPosition + margin , 0, 0.28),
                                                  frameSize=btnSize)


        self.freezeCheckbox = DirectCheckButton(text = "Pause" ,
                                                  parent=self.drawer,
                                                  scale=.05,
                                                  command=self.toggleFreeze,
                                                  pos=(drawerPosition + margin , 0, 0.17),
                                                  frameSize=btnSize)


        # Initially, the drawer is closed 
        self.drawerOpen = False
        self.drawer.hide()

    def toggleFreeze(self, status=None):
        self.freeze = not self.freeze

    def toggleDrawer(self):
        if self.drawerOpen:
            self.drawer.hide()
        else:
            self.drawer.show()

        self.drawerOpen = not self.drawerOpen


    def toggle2DView(self, status=None):

        self.orthographic=not self.orthographic

        if self.orthographic:
            self.activate2DView()
        else:
            self.activate3DView()
