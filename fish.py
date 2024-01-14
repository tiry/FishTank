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
from basesimulation import BaseSimulation, BaseSimulationWithDrawer





def createFish( x, y, z, model, scalingRatio,  idx):
    fishActor = FishActor(model)
    fishActor.setPos(x, y, z)
    fishActor.setHpr(random.uniform(-5,5), 0, random.uniform(-2,2))
    fishActor.name = f"fish_{idx}"
    fishActor.setScale(scalingRatio *  fishActor.length)
    return fishActor



class FishActor(Actor):

    def __init__(self, model, **kwargs):
        # Initialize the base class with the model and any other required arguments
        super().__init__(model, **kwargs) #  ???

        # Set additional properties for FishActor
        self.model_name = "fish-ani"  # or derived from model parameter
        self.length = 10  # Assuming a default length for all fish
        
        # Initial speed
        forwardSpeed=25
        self.speedVec = Vec3(forwardSpeed, 0, 0)  # Initial speed vector

        self._model = model
        self.targetIncidence = [ [None]*2 for i in range(3)]
        
        # the cube the Fish is currently located in
        self.cube=None
        # 
        self.neighbours=[]
    

    def get3DGridCoords(self, gridDimentions):
        pos = self.getPos()
        cs = gridDimentions[0]
        xMin = -gridDimentions[1]*cs/2
        yMin = -gridDimentions[2]*cs/2
        zMin = -gridDimentions[3]*cs/2
        x = (pos[0]-xMin)//cs
        y = (pos[1]-yMin)//cs
        z = (pos[2]-zMin)//cs            
        coords = (int(x),int(y),int(z))
        return coords


    def setCube(self, cube):
        self.cube=cube
    
    def getCube(self):
        return self.cube
    
#    def setNeighbours(self, neighbours):
        # print(f"Neighbours = {neighbours}")
#        self.neighbours=neighbours
    
    def getNeighbours(self):
        return self.neighbours

    def computeNeighBours(self, gridDimentions, gridMapping, radius = 2):
        
        cubeCoords = self.getCube()
        neighbours = []
        for x in range(max(0, cubeCoords[0]-radius), min(gridDimentions[1], cubeCoords[0]+radius)):
            for y in range(max(0, cubeCoords[1]-radius), min(gridDimentions[2], cubeCoords[1]+radius)):
                for z in range(max(0, cubeCoords[2]-radius), min(gridDimentions[3], cubeCoords[2]+radius)):
                        key = (x,y,z)
                        if key in gridMapping:
                            for f in gridMapping[key]:
                                neighbours.append(f)
        self.neighbours=neighbours
        return neighbours


    def getTargetIncidence(self, dim, sign):
        y=0
        if sign==-1:
            y=1
        return self.targetIncidence[dim][ y]
    
    def storeTargetIncidence(self, dim, sign, val):
        y=0
        if sign==-1:
            y=1
        self.targetIncidence[dim][y] = val

    def _normHpr(self):
        hpr = self.getHpr()
        for i in range(3):
            hpr[i] = self._normAngle(hpr[i])
        self.setHpr(hpr)
        return hpr

    def _fastestPath(self, target, start):
        return min(target-start, target-start+2*180, target-start-2*180, key=abs)

    def _normAngle(self, angle):
        angle = angle %360
        if angle==0:
            return 0
        sign = angle / abs(angle)
        if (abs(angle)>180):
            angle = - sign*(360- abs(angle))
        return angle

    def stayInTank(self, tankDimensions, rootNode, globalSpeedVec):

        avoidanceRadius = 80  # Distance at which fish start turning

        # Get fish position
        fishPos = self.getPos()

        # Check each face of the tank
        for dim, sign in [(0, 1), (0, -1), (1, 1), (1, -1), (2, 1), (2, -1)]:

            hpr=self._normHpr()

            # check if we are already outside of the limit
            if (sign > 0 and fishPos[dim] > tankDimensions[dim]) or (sign<0 and fishPos[dim] < -tankDimensions[dim]):
                fishPos[dim] = sign* (tankDimensions[dim]-5)
                if dim==0:
                    hpr[0]=0 if sign <0 else 180
                elif dim==1:
                    hpr[0]=90 if sign <0 else -90
                elif dim==2:
                    hpr[2]=-30 if sign <0 else 30
                # reset previously stored 
                self.setPos(fishPos)
                self.setHpr(hpr)
                self.storeTargetIncidence(dim,sign, [0,0])    
                # print(f"LOST {dim} {sign}")
                return

            # Calculate distance to the current face
            distance = abs(sign* tankDimensions[dim] - fishPos[dim])
            
            debug=False

            if distance < tankDimensions[dim]*0.2:

                if debug: print(f"Avoid trajectory for dimention {dim} {sign}")

                target_incidence = self.getTargetIncidence(dim, sign)

                if (target_incidence==None):
                    # no move to finish
                    # check if we actually need to do anything
                    if sign*globalSpeedVec[dim]<0:
                        # opposite direction so nothing to do
                        print("abort move")
                        continue

                hpr= self.getHpr()
                if debug: print(f"HPR = {self.getHpr()}")

                # get current position from HPR
                incidence_degree_head =  hpr[0]
                #if dim==1:
                #    incidence_degree_head = sign* (90-incidence_degree_head)
                incidence_degree_roll =  hpr[2]

                if debug: print(f"angle head = {incidence_degree_head}")
                if debug: print(f"angle roll = {incidence_degree_roll}")

                # init target if not already done
                if (target_incidence==None):
                    if dim==0:
                        if sign==1:
                            target_degree_head=180-2*incidence_degree_head
                            target_degree_roll=incidence_degree_roll
                        elif sign==-1:
                            target_degree_head= -180-incidence_degree_head 
                            target_degree_roll=incidence_degree_roll
                    elif dim==1:
                            target_degree_head = -incidence_degree_head
                            target_degree_roll=incidence_degree_roll
                    elif dim==2:
                            target_degree_head = incidence_degree_head
                            target_degree_roll=-incidence_degree_roll
                    
                    target_incidence = [self._normAngle(target_degree_head), self._normAngle(target_degree_roll)]
                    if debug: print(f"computed target = {target_incidence}")
                    self.storeTargetIncidence(dim,sign, target_incidence)
                else:
                    if debug: print(f"retrieved target = {target_incidence}")
                    

                degrees_to_rotate_head=self._fastestPath(target_incidence[0],incidence_degree_head)
                degrees_to_rotate_roll=self._fastestPath(target_incidence[1],incidence_degree_roll)
   

                if debug: print(f"degrees_to_rotate head = {degrees_to_rotate_head}")
                if debug: print(f"degrees_to_rotate roll = {degrees_to_rotate_roll}")

                #  compute step size depending on remaining speed and distance*0.7
                time_to_colision = 0.7* distance/self.speedVec.length()
                dt = globalClock.getDt() 
                rotate_step_head = degrees_to_rotate_head/time_to_colision * dt 
                rotate_step_roll = degrees_to_rotate_roll/time_to_colision * dt

                if debug: print(f"rotate_step head {rotate_step_head}")
                if debug: print(f"rotate_step roll {rotate_step_roll}")

                hpr=self.getHpr()
                hpr[0]+= rotate_step_head
                hpr[2]+= rotate_step_roll
                self.setHpr(hpr)

            else:
                # clear incidence
                self.storeTargetIncidence(dim,sign, None)




    def swim(self, rootNode, neighbours, tankDimensions):
        # Implement fish movement logic here
        dt = globalClock.getDt()
    

        ############################################
        # Compute influence from neighbours
        print(f" fish {self.name} neighbours => {neighbours}")
         

        ############################################
        # Move with the resulting speed 
        # Need to translate speed to the fish referencial
        transMat = self.getTransform().getMat()
        # Transform the local speed vector to the global coordinate system
        globalSpeedVec = transMat.xformVec(self.speedVec)
        # Scale the speed by the time delta for consistent movement over time
        globalSpeedVec *= dt
        # Update the fish's position by the global speed vector
        self.setPos(self.getPos() + globalSpeedVec)


        ############################################
        # Collision avoidance
        self.stayInTank(tankDimensions, rootNode, globalSpeedVec)

        self.displaySpeedArrow()

    def displaySpeedArrow(self):

        arrow_node_name = "speed_arrow"

        # get child the hard way since find does not work
        #arrow_node = self.find(f"render/{self.name}/{arrow_node_name}")
        idx=0
        for npath in self.getChildren():
            if  arrow_node_name in npath.name:
                npath.remove_node()
            else:
                idx+=1

        # draw speed arrow
        lines = LineSegs()
        lines.setThickness(2)  
        
        lines.setColor(1, 0, 0)
        
        lines.moveTo(0, 0, 0)
        lines.drawTo(self.speedVec.x * 0.3, self.speedVec.y* 0.3, self.speedVec.z* 0.3)
        line_node = lines.create()
        
        arrow_node = NodePath(line_node)
        arrow_node.name = "speed_arrow"
        arrow_node.reparentTo(self)
