from direct.showbase.ShowBase import ShowBase
from panda3d.core import AmbientLight, DirectionalLight, Vec3, Vec4, LMatrix4f
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


CONFIG = { 
        "tankAvoid":0.3,
        "fishCollisionRadius":10,
        "fishAlignRadius":20,
        "fishAttractdRadius":50,
        "catchMargin": 10,
        "cohesion" : 4,
        "escapeTimeout" : 30,
        "FOV": 110
        }

INTERACTION_MAX_RADIUS=800

def createFish( x, y, z, model, scalingRatio,  idx):
    fishActor = FishActor(model)
    fishActor.setPos(x, y, z)
    fishActor.setHpr(random.uniform(-8,8), 0, random.uniform(-5,5))
    
    fishActor.name = f"fish_{idx}"
    fishActor.setScale(scalingRatio *  fishActor.length)
    return fishActor



def convertDirectionToHpr(adjustment):
    adj_XY = Vec3(adjustment[0], adjustment[1], 0)
    adj_XZ = Vec3(adjustment[0],0,adjustment[2])
    angleH = normAngle(- adj_XY.normalized().signed_angle_deg(Vec3(1,0,0), Vec3(0,0,1)))
    angleR = normAngle(- adj_XZ.normalized().signed_angle_deg(Vec3(1,0,0), Vec3(0,1,0)))

    if abs(angleR) > 80 :
        # fish are not supposed to do loopings
        angleR = angleR / 10
    return Vec3(angleH, 0, angleR)

def normAngle(angle):
    angle = angle %360
    if angle==0:
        return 0
    sign = angle / abs(angle)
    if (abs(angle)>180):
        angle = - sign*(360- abs(angle))
    return angle

def normAngleVec(angleVec):
    return Vec3(normAngle(angleVec[0]), normAngle(angleVec[1]), normAngle(angleVec[2]))

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

        self.escapeTimeout=0
    

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
            hpr[i] = normAngle(hpr[i])
        self.setHpr(hpr)
        return hpr

    def _fastestPath(self, target, start):
        return min(target-start, target-start+2*180, target-start-2*180, key=abs)

    def stayInTank(self, tankDimensions, rootNode, globalSpeedVec):

        # Get fish position
        fishPos = self.getPos()

        ##########################################
        # Catch fish before they exit the tank !
        escapeHpr = Vec3(0,0,0)
        escapeXYZ= Vec3(0,0,0)
        for dim, sign in [(0, 1), (0, -1), (1, 1), (1, -1), (2, 1), (2, -1)]:

            # Calculate distance to the current face
            #distance = abs(sign* tankDimensions[dim] - fishPos[dim])
            distance = tankDimensions[dim] - sign*fishPos[dim]
            #print(f"distance {dim} {sign} = {distance}")
            # check if we are already outside of the limit
            # and still moving in the wrong direction
            hpr=self.getHpr()
            margin = CONFIG["catchMargin"]
            if (distance < margin) and sign*globalSpeedVec[dim]>0:
                if dim==0:
                    escapeHpr[0]+= (180-2*hpr[0])
                    escapeXYZ+= Vec3(-sign*margin, 0,0)
                elif dim==1:
                    escapeHpr[0]+=-2*hpr[0]
                    escapeXYZ+= Vec3(0,-sign*margin, 0)
                elif dim==2:
                    escapeHpr[2]+=-2*hpr[2]
                    escapeXYZ+= Vec3(0,0,-sign*margin)
        if escapeHpr.length()>0:
            self.setHpr(normAngleVec(self.getHpr() + escapeHpr))
            self.setPos(self.getPos() + escapeXYZ)
            self.storeTargetIncidence(dim,sign, [0,0])
            self.escapeTimeout=CONFIG["escapeTimeout"]
            return    
            
        ##################################
        # compute move to avoid the borders
        # Check each face of the tank
        for dim, sign in [(0, 1), (0, -1), (1, 1), (1, -1), (2, 1), (2, -1)]:

            hpr=self._normHpr()

            # Calculate distance to the current face
            distance = abs(sign* tankDimensions[dim] - fishPos[dim])
            debug=False

            if distance < tankDimensions[dim]*CONFIG["tankAvoid"]:

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
                    
                    target_incidence = [normAngle(target_degree_head), normAngle(target_degree_roll)]
                    if debug: print(f"computed target = {target_incidence}")
                    self.storeTargetIncidence(dim,sign, target_incidence)
                else:
                    if debug: print(f"retrieved target = {target_incidence}")
                    

                degrees_to_rotate_head=self._fastestPath(target_incidence[0],incidence_degree_head)
                degrees_to_rotate_roll=self._fastestPath(target_incidence[1],incidence_degree_roll)
   

                if debug: print(f"degrees_to_rotate head = {degrees_to_rotate_head}")
                if debug: print(f"degrees_to_rotate roll = {degrees_to_rotate_roll}")

                #  compute step size depending on remaining speed and distance*0.7
                multiplier = max(5, 10* self.speedVec.length() / distance)
                #print(f"multiplier = {multiplier}")
                dt = globalClock.getDt() 
                rotate_step_head = degrees_to_rotate_head * dt * multiplier
                rotate_step_roll = degrees_to_rotate_roll * dt * multiplier

                if debug: print(f"rotate_step head {rotate_step_head}")
                if debug: print(f"rotate_step roll {rotate_step_roll}")

                hpr=self.getHpr()
                hpr[0]+= rotate_step_head
                hpr[2]+= rotate_step_roll
                self.setHpr(hpr)

            else:
                # clear incidence
                self.storeTargetIncidence(dim,sign, None)


    def computeInfluence(self, neighbours, environment):
        #print(f" fish {self.name} neighbours => {neighbours}")
        
        adjustment = Vec3(0,0,0)
        adjustHPR = Vec3(0,0,0)
        transMat = self.getTransform().getMat()
        iTransMat=LMatrix4f(transMat)
        iTransMat.invert_in_place()  

        attractors = []
        attractors.extend(environment["attractors"])

        repulsors = []
        repulsors.extend(environment["repulsors"])

        aligners = []
        aligners.extend(environment["aligners"])

        for f in neighbours:
            d = self.get_distance(f)
            if d < CONFIG["fishCollisionRadius"]:
                repulsors.append(f)
            elif d < CONFIG["fishAlignRadius"]:
                aligners.append(f)
            elif d < CONFIG["fishAttractdRadius"]:
                attractors.append(f)

        #print(f"fish {self.name}=> neighbours:{len(neighbours)}; attractors={len(attractors)}; repulsors={len(repulsors)}; :aligners = {len(aligners)}")
        
        # Aligners
        idx=0
        self.deleteArrows("aligner_")
        for aligner in aligners:
            # compiute aligner position : to know if we need to take into account
            adjustmentG = aligner.getPos()-self.getPos()
            adjustment = iTransMat.xformVec(adjustmentG)
            # convert to HPR
            adjustmentHPR = convertDirectionToHpr(adjustment)
            adjustmentHPR = normAngleVec(adjustmentHPR)
            arrow_name = f"aligner_{self.name}_{idx}"
            if abs(adjustmentHPR[0])>CONFIG["FOV"]:
                self.deleteArrow(arrow_name)
                continue
            # Align native HPR (not derived from displacement)
            adjustHPR += (aligner.getHpr() - self.getHpr())*globalClock.getDt()                   
            # display arrow
            self.displayArrow(arrow_name, adjustment, 1, Vec3(0,1,1))
            idx+=1
        
        # Attractors
        idx=0
        self.deleteArrows("attractor_")
        for attractor in attractors:
            # initial positions are in the global referential
            adjustmentG = attractor.getPos()-self.getPos()
            # translate in the fish referential to be able to draw the arrow
            adjustment = iTransMat.xformVec(adjustmentG)
            # convert to HPR
            adjustmentHPR = convertDirectionToHpr(adjustment)
            adjustmentHPR = normAngleVec(adjustmentHPR)
            #print(f"adjustmentHPR => {adjustmentHPR} Current HPR = {self.getHpr()}")
            arrow_name = f"attractor_{self.name}_{idx}"
            # only attracted by what the fish can see: forward and not too far
            #if adjustment[0]<0 or adjustmentG.length()>INTERACTION_MAX_RADIUS:
            if abs(adjustmentHPR[0])>CONFIG["FOV"] or adjustmentG.length()>INTERACTION_MAX_RADIUS:
                self.deleteArrow(arrow_name)
                continue
            # display arrow
            self.displayArrow(arrow_name, adjustment, 1, Vec3(0,1,0))
            adjustHPR += adjustmentHPR*globalClock.getDt()
            idx+=1

        # Repulsors
        idx=0
        self.deleteArrows("repulsor_")
        for repulsor in repulsors:
            # initial positions are in the global referential
            adjustmentG = -(repulsor.getPos()-self.getPos())
            # translate in the fish referential to be able to draw the arrow
            adjustment = iTransMat.xformVec(adjustmentG)
            # convert to HPR
            adjustmentHPR = convertDirectionToHpr(adjustment)
            adjustmentHPR = normAngleVec(adjustmentHPR)
            arrow_name = f"repulsor_{self.name}_{idx}"
            # only attracted by what the fish can see: forward and not too far
            #if adjustment[0]>0 or adjustmentG.length()>INTERACTION_MAX_RADIUS:
            if (adjustmentHPR[0])>CONFIG["FOV"] or adjustmentG.length()>INTERACTION_MAX_RADIUS:
                self.deleteArrow(arrow_name)
                continue
            # display arrow
            self.displayArrow(arrow_name, adjustment*-1, 1, Vec3(1,0,0))
            #print(f"adjustmentHPR => {adjustmentHPR} Current HPR = {self.getHpr()}")
            adjustHPR += adjustmentHPR*globalClock.getDt()
            idx+=1

        # Apply changes
        self.safeSetHpr(self.getHpr() + adjustHPR*CONFIG["cohesion"])

    def safeSetHpr(self, hpr):

        roll = normAngle(hpr[2])
        if (roll < -45):
            roll = -45
        if (roll > 45):
            roll = 45           
        self.setHpr(hpr[0], hpr[1], roll)


    def swim(self, rootNode, neighbours, tankDimensions, environment):
    
        ############################################
        # Need to translate speed to the fish referencial
        transMat = self.getTransform().getMat()
        # Transform the local speed vector to the global coordinate system
        globalSpeedVec = transMat.xformVec(self.speedVec)
        
        #print(f"Tranformation Matrix = {transMat}")

        if self.escapeTimeout>0:
            # do not distruct trajectory when fish is escaping collision
            self.escapeTimeout-=1
        else:
            ############################################
            # Compute influence from neighbours
            self.computeInfluence(neighbours, environment) 

            ############################################
            # Collision avoidance
            self.stayInTank(tankDimensions, rootNode, globalSpeedVec)

        ############################################
        # Move with the resulting speed 
        # Scale the speed by the time delta for consistent movement over time
        globalSpeedVec *= globalClock.getDt()
        # Update the fish's position by the global speed vector
        self.setPos(self.getPos() + globalSpeedVec)
        self.displayArrow("speed_arrow", self.speedVec, 0.3, Vec3(0,0,1))


    def deleteArrows(self, arrow_node_name_prefix):
        for npath in self.getChildren():
            if  npath.name.startswith(arrow_node_name_prefix):
                npath.remove_node()
    
    def deleteArrow(self, arrow_node_name):
        # get child the hard way since find does not work
        #arrow_node = self.find(f"render/{self.name}/{arrow_node_name}")
        for npath in self.getChildren():
            if  arrow_node_name in npath.name:
                npath.remove_node()
                break
            
    def displayArrow(self, arrow_node_name, vect, ratio, color):

        self.deleteArrow(arrow_node_name)

        # draw speed arrow
        lines = LineSegs()
        lines.setThickness(2)  
        
        lines.setColor(color)
        
        lines.moveTo(0, 0, 0)
        lines.drawTo(vect.x * ratio, vect.y* ratio, vect.z* ratio)
        line_node = lines.create()
        
        arrow_node = NodePath(line_node)
        arrow_node.name = arrow_node_name
        arrow_node.reparentTo(self)
