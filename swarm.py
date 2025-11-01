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
from fish import FishActor, createFish
from factory import mkCube, mkSpatialGrid

TANK_DIMENSION = Vec3(1600,900, 200)

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
        # NOTE: fish-ani.gltf causes segfault with Panda3D 1.10.15 and Python 3.12
        # Using koifish.egg instead which is more compatible
        modelMappings = {
            "fish": { "path": "koi_low.gltf", "scale": 0.012},
            "fish-ani": { "path" : "koifish.egg", "scale": 0.8},  # Changed from fish-ani.gltf to koifish.egg
            "fish-egg": { "path" : "koifish.egg", "scale": 0.8} 
        }
        self.loadModels(modelMappings)

        # create the Tank
        self.setupTank(TANK_DIMENSION, thickness=5.0, color=[0.4,0.75,1])

        self.setupEnvironment()

        # Create fish group
        self.setupSwarm()

        #self.fishSwarm = self.createSwarm(w=1, l=1, spacing=60)

        # Init the spatial gr
        grid, gridCubes, gridDimentions = mkSpatialGrid(TANK_DIMENSION,5)
        grid.reparentTo(self.render)

        self.gridCubes = gridCubes
        self.gridDimentions = gridDimentions
        
        # maps cube to fish
        # (x,y,z) => [fish_idx1, fish_idx2]
        self.gridMapping={}
       
        #self.freeze=True
        self.setTopView()
        #self.setSideView()
    
    def setupSwarm(self):

        for npath in self.render.getChildren():
            if  npath.name.startswith("fish_"):
                npath.remove_node()
 
        #self.fishSwarm = self.createSwarm(w=7, l=5, spacing=50)
        self.fishSwarm = self.createTriangleSwarm(15, 8, spacing=60)
        #self.fishSwarm = self.createTriangleSwarm(2, 2, spacing=50)
        

    def resetSimulation(self):
        self.setupSwarm()

    def setupEnvironment(self):
         self.environment={
            "attractors": [],
            "repulsors": [],
            "aligners" : []
        }

        #attractor_path = mkCube([5,5,5], 1, [1,0,0])
        #attractor_path.reparentTo(self.render)
        #attractor_path.setPos(Vec3(-1000,300,0))
        #self.environment["attractors"].append(attractor_path)

        #repulsor_path = mkCube([5,5,5], 1, [1,0,0])
        #repulsor_path.reparentTo(self.render)
        #repulsor_path.setPos(Vec3(500,100,0))
        #self.environment["repulsors"].append(repulsor_path)

    def setupTank(self, dimentions=Vec3(1,1,1), thickness=1, color=[1,1,1]):
        
        # Draw a simple cube
        node_path = mkCube(dimentions, thickness, color)
        node_path.reparentTo(self.render)
    
    def createSwarm(self, w=10, l=5, spacing=100):
        fishSwarm = []
        modelName = "fish-ani"
        model = self.getModel(modelName)
        scalingRatio = self.getModelScaling(modelName)
        for i in range(w):
            for j in range(l):
                # Calculate the x and y positions for the fish
                x = (i - w / 2) * spacing 
                y = (j - l / 2) * spacing 
                z = 0  
                # Create and add the fish to the array
                fish = createFish(x,y,z,model, scalingRatio, len(fishSwarm))
                fish.reparentTo(self.render)
                fishSwarm.append(fish)
        return fishSwarm
    
    def createTriangleSwarm(self, w=10, max_l=5, spacing=100):
        fishSwarm = []
        modelName = "fish-ani"
        model = self.getModel(modelName)
        scalingRatio = self.getModelScaling(modelName)
        l=0
        for i in range(w):
            if l< max_l:
                l+=1
            for j in range(l):
                # Calculate the x and y positions for the fish
                x = ( w / 2 - i) * spacing 
                y = (j - l / 2) * spacing 
                z = 0  
                # Create and add the fish to the array
                fish = createFish(x,y,z,model, scalingRatio, len(fishSwarm))
                fish.reparentTo(self.render)
                fishSwarm.append(fish)
        return fishSwarm
    

    def computeSpacialDistribution(self, display_non_empty_cube=False):

        if display_non_empty_cube:
            # hide previously displayed cubes
            for ccords in self.gridMapping.keys():
                try:
                    self.gridCubes[ccords[0]][ccords[1]][ccords[2]].hide()
                except IndexError:
                    pass

        gridMapping={}

        # update the mapping between cubes and fishes
        for idx, fish in enumerate(self.fishSwarm):
            key = fish.get3DGridCoords(self.gridDimentions)
            fish.setCube(key)
            if not key in gridMapping:
                gridMapping[key]=[]
            gridMapping[key].append(idx)
            
        if display_non_empty_cube:
            for ccords in gridMapping.keys():
                try:
                    self.gridCubes[ccords[0]][ccords[1]][ccords[2]].show()
                except IndexError:
                    pass

        self.gridMapping=gridMapping

    def runSimulation(self, task):

        if self.freeze:
            return task.cont

        if random.randint(0,100)==100:
            for attractor in self.environment["attractors"]:
                attractor.setPos(int(TANK_DIMENSION[0]*random.uniform(-0.8, 0.8)), int(TANK_DIMENSION[1]*random.uniform(-0.8, 0.8)), int(TANK_DIMENSION[2]*random.uniform(-0.8, 0.8)))

        # the the 3D Cube grid to partition the space
        # map each fish to a cube
        self.computeSpacialDistribution(DISPLAY_CUBES)

        # Call computeMove for each fish every frame
        for fish in self.fishSwarm:
            neighboursIdx=fish.computeNeighBours(self.gridDimentions, self.gridMapping, 2)
            neighbours=[]
            for idx in neighboursIdx:
                if self.fishSwarm[idx].name !=fish.name:
                    neighbours.append(self.fishSwarm[idx])
            if len(neighbours)>6:
                neighbours.sort(key = lambda f : (f.getPos()-fish.getPos()).length())
                neighbours=neighbours[:6]
            fish.swim(self.render, neighbours, TANK_DIMENSION, self.environment)
        return task.cont

if __name__ == "__main__":
    app = FishTankSimulation()
    app.run()
