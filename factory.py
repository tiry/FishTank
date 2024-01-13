from panda3d.core import LineSegs, NodePath
import numpy as np
from panda3d.core import AmbientLight, DirectionalLight, Vec3, Vec4
from panda3d.core import Geom, GeomNode, GeomVertexFormat, GeomVertexData
from panda3d.core import GeomVertexWriter, GeomTriangles, TransparencyAttrib
from panda3d.core import NodePath

import math


def _computeCubeMapping(dimensions, segments=10):

    min_width = min(int(dimensions.x), int(dimensions.y), int(dimensions.z))
    cube_width = math.ceil(min_width/segments)
    cube_width = max(cube_width, 100)
    return [cube_width, 
            math.ceil(2*dimensions.x/cube_width), 
            math.ceil(2*dimensions.y/cube_width),
            math.ceil(2*dimensions.z/cube_width)]


def mkSpatialGrid(dimensions, min_segments=6 ):

    # dimentions represent the half lenth for the X,Y,Z axis
    root = NodePath("3dGrid")

    # we want to fill the content of the rectangular parallelepiped
    # with cubes 
    # we want to find the most optimized size so that
    # we have at least {segments} cubes for the smallest dimention.
    print(f"compute cubeSize with {min_segments} segments" )

    cubeSize = _computeCubeMapping(dimensions, min_segments)
    print(f"cubeSize = {cubeSize}")

    print(f" total number of cubes = {cubeSize[1]*cubeSize[2]*cubeSize[3]}")

    cubGrid = [[[None for _ in range(cubeSize[3])] for _ in range(cubeSize[2])] for _ in range(cubeSize[1])]

    for x in range(0, len(cubGrid)):
        for y in range(0, len(cubGrid[0])):
            for z in range(0, len(cubGrid[0][0])):

                cubGrid[x][y][z] = mkCube(Vec3(cubeSize[0]/2, cubeSize[0]/2, cubeSize[0]/2), 1, [0.8,0.8,1, 0.1], wire_frame=False)
                cub = cubGrid[x][y][z]
                cub.reparentTo(root)
                cub.setPos(x*cubeSize[0], y*cubeSize[0], z*cubeSize[0])
                cub.hide()

    dx = cubeSize[0]/2 - int((len(cubGrid) * cubeSize[0])/2) 
    dy = cubeSize[0]/2 - int((len(cubGrid[0]) * cubeSize[0])/2)
    dz = cubeSize[0]/2- int((len(cubGrid[0][0]) * cubeSize[0])/2)
    root.setPos(dx,dy,dz)
    return (root, cubGrid, cubeSize)


def mkCube(dimensions,thickness=2.0, col=[1,1,1,1],wire_frame=True):

    if wire_frame:
        return mkCubeWireframe(dimensions, thickness, col[:3])
    else:
        return mkCube3D(dimensions, col)


def mkCube3D(dimensions, col=[1,1,1,1]):  # Added alpha to color
    format = GeomVertexFormat.getV3()  # Format for vertices only
    vdata = GeomVertexData('cube', format, Geom.UHStatic)

    # Vertex writers
    vertex = GeomVertexWriter(vdata, 'vertex')

    # Define the vertices of the cube
    vertices = [
        [-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],  # Bottom vertices
        [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]  # Top vertices
    ]

    vertices = (np.array(vertices) * dimensions).tolist()

    # Add vertices to the vertex data
    for v in vertices:
        vertex.addData3(*v)

    # Create the cube's geometry
    geom = Geom(vdata)

    # Define the faces of the cube (each as a triangle pair)
    # Ensure counter-clockwise winding order for proper face orientation
    faces = [
        [2, 1, 0, 3], [4, 5, 6, 7],  # Bottom, Top
        [1, 2, 6, 5], [3, 0, 4, 7],  # Front, Back
        [0, 1, 5, 4], [2, 3, 7, 6]   # Right, Left
    ]

    # Create the triangles for each face
    for face in faces:
        tri = GeomTriangles(Geom.UHStatic)
        tri.addVertices(face[0], face[1], face[2])
        tri.addVertices(face[0], face[2], face[3])
        tri.closePrimitive()
        geom.addPrimitive(tri)

    # Create a node and add geometry to it
    cube_node = GeomNode('cube')
    cube_node.addGeom(geom)

    # Create a node path and attach the node
    cube_np = NodePath(cube_node)

    # Set color and transparency
    cube_np.setColor(col[0], col[1], col[2], col[3])  # Use RGBA color
    cube_np.setTransparency(TransparencyAttrib.MAlpha)

    return cube_np


def mkCubeWireframe(dimensions,thickness=2.0, col=[1,1,1]):
        # Define the vertices of a cube
    vertices = [
        [-1, -1, -1],  # Vertex 0
        [1, -1, -1],  # Vertex 1
        [1, 1, -1],  # Vertex 2
        [-1, 1, -1],  # Vertex 3
        [-1, -1, 1],  # Vertex 4
        [1, -1, 1],  # Vertex 5
        [1, 1, 1],  # Vertex 6
        [-1, 1, 1]  # Vertex 7
    ]

    vertices=(np.array(vertices)*dimensions).tolist()

    
    # Define the edges between vertices to form a cube
    edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),  # Bottom edges
        (4, 5), (5, 6), (6, 7), (7, 4),  # Top edges
        (0, 4), (1, 5), (2, 6), (3, 7)  # Side edges connecting top and bottom
    ]
    
    # Create a line segment object
    lines = LineSegs()
    lines.setThickness(thickness)  # Set the thickness of lines
    lines.setColor(col[0], col[1], col[2])
    
    # Draw each edge
    for (vi0, vi1) in edges:
        v0 = vertices[vi0]
        v1 = vertices[vi1]
        lines.moveTo(v0[0], v0[1], v0[2])
        lines.drawTo(v1[0], v1[1], v1[2])
    
    
    # Create a node path and attach the line segment object
    line_node = lines.create()
    

    return NodePath(line_node)
