from direct.showbase.ShowBase import ShowBase
from panda3d.core import AmbientLight, DirectionalLight, Vec3, Vec4
from direct.actor.Actor import Actor
from panda3d.core import PointLight, KeyboardButton, MouseWatcher
from panda3d.core import LineSegs, NodePath
import random
from direct.task import Task
from panda3d.core import Mat3, deg2Rad
import math
import sys
from panda3d.core import Point3, TransparencyAttrib,TextNode
from direct.gui.DirectGui import DirectFrame, DirectButton, DGG, DirectCheckButton
from panda3d.core import OrthographicLens,PerspectiveLens

from basesimulation import BaseSimulation, BaseSimulationWithDrawer
from fish import FishActor
from factory import mkCube, mkSpatialGrid

TANK_DIMENSION = Vec3(1600,600, 200)

DISPLAY_CUBES=True

class FishTankSimulation(BaseSimulationWithDrawer):
    
    def __init__(self):

        BaseSimulationWithDrawer.__init__(self)
    
        # Scene initialization
        self.setupLights()

        # take over camera control
        self.disableMouse()  
        self.setupCamera()
        self.setupNavigationControls()

        #self.toggle2DView()
        #self.setTopView()

        # Drawer to configure simulation
        self.setupDrawer()

        # Pre-load models
        modelMappings = {
            "fish": { "path": "koi_low.gltf", "scale": 0.012},
            "fish-ani": { "path" : "fish-ani.gltf", "scale": 0.8}, 
            "fish-egg": { "path" : "koifish.egg", "scale": 0.8} 
        }
        self.loadModels(modelMappings)

        # create the Tank
        self.setupTank(TANK_DIMENSION, thickness=5.0, color=[0.4,0.75,1])

        # Create fish group
        self.fishArray = self.createFishArray(w=5, l=4, spacing=60)

        # Init the spatial gr
        grid, cubes, gridDimentions = mkSpatialGrid(TANK_DIMENSION,5)
        grid.reparentTo(self.render)

        self.cubes = cubes
        self.gridDimentions = gridDimentions
        
        # maps cube to fish
        # (x,y,z) => [fish_idx1, fish_idx2]
        self.cubmapping={}


    def setupTank(self, dimentions=Vec3(1,1,1), thickness=1, color=[1,1,1]):

        # Draw a simple cube
        
        node_path = mkCube(dimentions, thickness, color)
        node_path.reparentTo(self.render)
    

    def createFish(self, x, y, z, modelName, idx):

        model = self.getModel(modelName)
        fishActor = FishActor(model)
        fishActor.setPos(x, y, z)
        
        #fishActor.setHpr(0, 0, -40)
        #fishActor.setHpr(0, 0, -20)
        fishActor.setHpr(random.uniform(-5,5), 0, random.uniform(-2,2))

        fishActor.name = f"fish_{idx}"

        scalingRatio = self.getModelScaling(modelName)
        fishActor.setScale(scalingRatio *  fishActor.length)

        fishActor.reparentTo(self.render)

        return fishActor

    def createFishArray(self, w=10, l=5, spacing=100):
        fishArray = []
        for i in range(w):
            for j in range(l):
                # Calculate the x and y positions for the fish

                # Center the array around the origin (0,0,0)
                #x = (i - w / 2) * spacing + random.uniform(-0.1, 0.1)*spacing
                #y = (j - l / 2) * spacing + random.uniform(-0.1, 0.1)*spacing
                #z = 0  + random.uniform(-0.1, 0.1)*spacing # Assuming fish swim at a constant depth

                x = (i - w / 2) * spacing 
                y = (j - l / 2) * spacing 
                z = 0  
                # Debug print to verify positions
                # print(f"Fish at: x={x}, y={y}, z={z}")

                # Create and add the fish to the array
                x = x -spacing*12
                fishArray.append(self.createFish(x, y, z,"fish-ani", len(fishArray)) )
        return fishArray

    def computeCubCoords(self, fish):
            pos = fish.getPos()
            cs = self.gridDimentions[0]
            xMin = -len(self.cubes)*cs/2
            yMin = -len(self.cubes[0])*cs/2
            zMin = -len(self.cubes[0][0])*cs/2
            x = (pos[0]-xMin)//cs
            y = (pos[1]-yMin)//cs
            z = (pos[2]-zMin)//cs            
            coords = (int(x),int(y),int(z))
            return coords
    
    def gatherNeighBours(self, fish, radius = 2):
        
        cubeCoords = fish.getCube()
        neighbours = []

        for x in range(max(0, cubeCoords[0]-radius), min(len(self.cubes), cubeCoords[0]+radius)):
            for y in range(max(0, cubeCoords[1]-radius), min(len(self.cubes[0]), cubeCoords[1]+radius)):
                for z in range(max(0, cubeCoords[2]-radius), min(len(self.cubes[0][0]), cubeCoords[2]+radius)):
                        key = (x,y,z)
                        if key in self.cubmapping:
                            for f in self.cubmapping[key]:
                                neighbours.append(f)
        return neighbours

    def computeSpacialDistribution(self):

        if DISPLAY_CUBES:
            for ccords in self.cubmapping.keys():
                try:
                    self.cubes[ccords[0]][ccords[1]][ccords[2]].hide()
                except IndexError:
                    pass

        cubmapping={}

        # first loop to compute the cube
        for idx, fish in enumerate(self.fishArray):
            key = self.computeCubCoords(fish)
            fish.setCube(key)
            if not key in cubmapping:
                cubmapping[key]=[]
            cubmapping[key].append(idx)

        # second loop to find neighbours
        for fish in self.fishArray:
            fish.setNeighbours(self.gatherNeighBours(fish, 2))
            
        if DISPLAY_CUBES:
            for ccords in cubmapping.keys():
                try:
                    self.cubes[ccords[0]][ccords[1]][ccords[2]].show()
                except IndexError:
                    pass

        self.cubmapping=cubmapping

    def runSimulation(self, task):

        if self.freeze:
            return task.cont

        # the the 3D Cube grid to partition the space
        # map each fish to a cube
        self.computeSpacialDistribution()

        # Call computeMove for each fish every frame
        for fish in self.fishArray:
            fish.computeMove(self.render, self.fishArray, TANK_DIMENSION)
        return task.cont

if __name__ == "__main__":
    app = FishTankSimulation()
    app.run()

