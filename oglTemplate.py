"""
/*******************************************************************************
 *
 *            #, #,         CCCCCC  VV    VV MM      MM RRRRRRR
 *           %  %(  #%%#   CC    CC VV    VV MMM    MMM RR    RR
 *           %    %## #    CC        V    V  MM M  M MM RR    RR
 *            ,%      %    CC        VV  VV  MM  MM  MM RRRRRR
 *            (%      %,   CC    CC   VVVV   MM      MM RR   RR
 *              #%    %*    CCCCCC     VV    MM      MM RR    RR
 *             .%    %/
 *                (%.      Computer Vision & Mixed Reality Group
 *
 ******************************************************************************/
/**          @copyright:   Hochschule RheinMain,
 *                         University of Applied Sciences
 *              @author:   Prof. Dr. Ulrich Schwanecke
 *             @version:   0.91
 *                @date:   07.06.2022
 ******************************************************************************/
/**         oglTemplate.py
 *
 *          Simple Python OpenGL program that uses PyOpenGL + GLFW to get an
 *          OpenGL 3.2 core profile context and animate a colored triangle.
 ****
"""

import glfw
import numpy as np
import sys

from OpenGL.GL import *
from OpenGL.arrays.vbo import VBO
from OpenGL.GL.shaders import *

from mat4 import *

EXIT_FAILURE = -1


def load_obj(filename):
    vertices = []
    indices = []

    with open(filename, "r") as file:
        for line in file:
            parts = line.strip().split()

            if not parts:
                continue

            if parts[0] == "v":
                vertices.append([
                    float(parts[1]),
                    float(parts[2]),
                    float(parts[3])
                ])

            elif parts[0] == "f":
                face = []

                for v in parts[1:]:
                    face.append(int(v.split('/')[0]) - 1)

                indices.extend(face)

    vertices = np.array(vertices, dtype=np.float32)
    indices = np.array(indices, dtype=np.uint32)

    center = np.mean(vertices, axis=0)
    vertices -= center

    max_dist = np.max(np.linalg.norm(vertices, axis=1))
    vertices /= max_dist

    return vertices, indices

def calculate_normals(vertices, indices):
    normals = np.zeros(vertices.shape, dtype=np.float32)

    for i in range(0, len(indices), 3):
        i1 = indices[i]
        i2 = indices[i + 1]
        i3 = indices[i + 2]

        v1 = vertices[i1]
        v2 = vertices[i2]
        v3 = vertices[i3]

        normal = np.cross(v2 - v1, v3 - v1)

        length = np.linalg.norm(normal)
        if length > 0:
            normal /= length

        normals[i1] += normal
        normals[i2] += normal
        normals[i3] += normal

    for i in range(len(normals)):
        length = np.linalg.norm(normals[i])
        if length > 0:
            normals[i] /= length

    return normals

def project_on_sphere(
        x,
        y,
        width,
        height,
        radius=200):

    x = x - width / 2.0
    y = height / 2.0 - y

    a = min(
        radius * radius,
        x * x + y * y
    )

    z = np.sqrt(
        radius * radius - a
    )

    length = np.sqrt(
        x*x + y*y + z*z
    )

    return np.array([
        x / length,
        y / length,
        z / length
    ])

def shadow_matrix():
    return np.array([
        [1, 0, 0, 0],
        [0, 0, 0, -0.9],
        [0, 0, 1, 0],
        [0, 0, 0, 1]
    ], dtype=np.float32)


class Scene:
    """
        OpenGL scene class that render a RGB colored tetrahedron.
    """

    def __init__(self, width, height, scenetitle="Hello Triangle"):
        self.scenetitle         = scenetitle
        self.width              = width
        self.height             = height
        self.angle              = 0
        self.angle_increment    = 1
        self.animate            = False
        self.shading_mode       = 0
        self.use_perspective    = True
        self.rot_x              = 0
        self.rot_y              = 0
        self.rot_z              = 0
        self.zoom               = 2.0
        self.tx                 = 0.0
        self.ty                 = 0.0
        self.arcball_rotation   = np.eye(4)
        self.shadow_enabled     = True


    def init_GL(self):
        # setup buffer (vertices, colors, normals, ...)
        self.gen_buffers()

        # setup shader
        glBindVertexArray(self.vertex_array)
        vertex_shader       = open("shader.vert","r").read()
        fragment_shader     = open("shader.frag","r").read()
        vertex_prog         = compileShader(vertex_shader, GL_VERTEX_SHADER)
        frag_prog           = compileShader(fragment_shader, GL_FRAGMENT_SHADER)
        self.shader_program = compileProgram(vertex_prog, frag_prog)

        vertex_shader = open(
            "shader_phong.vert",
            "r"
        ).read()

        fragment_shader = open(
            "shader_phong.frag",
            "r"
        ).read()

        vertex_prog = compileShader(
            vertex_shader,
            GL_VERTEX_SHADER
        )

        frag_prog = compileShader(
            fragment_shader,
            GL_FRAGMENT_SHADER
        )

        self.phong_program = compileProgram(
            vertex_prog,
            frag_prog
        )

        vertex_shader = open(
            "shader_wire.vert",
            "r"
        ).read()

        fragment_shader = open(
            "shader_wire.frag",
            "r"
        ).read()

        vertex_prog = compileShader(
            vertex_shader,
            GL_VERTEX_SHADER
        )

        frag_prog = compileShader(
            fragment_shader,
            GL_FRAGMENT_SHADER
        )

        self.wire_program = compileProgram(
            vertex_prog,
            frag_prog
        )

        vertex_shader = open(
            "shader_shadow.vert",
            "r"
        ).read()

        fragment_shader = open(
            "shader_shadow.frag",
            "r"
        ).read()

        vertex_prog = compileShader(
            vertex_shader,
            GL_VERTEX_SHADER
        )

        frag_prog = compileShader(
            fragment_shader,
            GL_FRAGMENT_SHADER
        )

        self.shadow_program = compileProgram(
            vertex_prog,
            frag_prog
        )

        # unbind vertex array to bind it again in method draw
        glBindVertexArray(0)


    def gen_buffers(self):
        # TODO: 
        # 1. Load geometry from file and calc normals if not available
        # 2. Load geometry and normals in buffer objects

        # generate vertex array object
        self.vertex_array = glGenVertexArrays(1)
        glBindVertexArray(self.vertex_array)

        # generate and fill buffer with vertex positions (attribute 0)
        positions, self.indices = load_obj(sys.argv[1])
        normals = calculate_normals(
            positions,
            self.indices
        )
        pos_buffer = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, pos_buffer)
        glBufferData(GL_ARRAY_BUFFER, positions.nbytes, positions, GL_STATIC_DRAW)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)
        glEnableVertexAttribArray(0)

        normal_buffer = glGenBuffers(1)

        glBindBuffer(GL_ARRAY_BUFFER, normal_buffer)

        glBufferData(
            GL_ARRAY_BUFFER,
            normals.nbytes,
            normals,
            GL_STATIC_DRAW
        )

        glVertexAttribPointer(
            1,
            3,
            GL_FLOAT,
            GL_FALSE,
            0,
            None
        )

        glEnableVertexAttribArray(1)

        # generate index buffer (for triangle strip)      
        ind_buffer_object = glGenBuffers(1)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ind_buffer_object)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, self.indices.nbytes, self.indices, GL_STATIC_DRAW)
        
        # unbind buffers to bind again in draw()
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)



    def set_size(self, width, height):
        self.width = width
        self.height = height


    def draw(self):
        # TODO:
        # 1. Render geometry 
        #    (a) just as a wireframe model and 
        #    with 
        #    (b) a shader that realize Gouraud Shading
        #    (c) a shader that realize Phong Shading
        # 2. Rotate object around the x, y, z axis using the keys x, y, z
        # 3. Rotate object with the mouse by realizing the arcball metaphor as 
        #    well as scaling an translation
        # 4. Realize Shadow Mapping
        # 
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        if self.animate:
            # increment rotation angle in each frame
            self.angle += self.angle_increment
    
        # setup matrices
        aspect = self.width / self.height

        if self.use_perspective:

            projection = perspective(
                45.0,
                aspect,
                1.0,
                5.0
            )

        else:

            size = 1.5

            projection = ortho(
                -size * aspect,
                size * aspect,
                -size,
                size,
                1.0,
                5.0
            )
        view = look_at(
            0,0,self.zoom,
            0,0,0,
            0,1,0
        )
        model = (
            translate(
                self.tx,
                self.ty,
                0
            )
            @ self.arcball_rotation
            @ rotate_x(self.rot_x)
            @ rotate_y(self.rot_y + self.angle)
            @ rotate_z(self.rot_z)
        )
        mvp_matrix = projection @ view @ model

        # enable shader & set uniforms
        if self.shading_mode == 0:
            glPolygonMode(
                GL_FRONT_AND_BACK,
                GL_LINE
            )
        else:
            glPolygonMode(
                GL_FRONT_AND_BACK,
                GL_FILL
            )
        
        if self.shading_mode == 0:
            program = self.wire_program
        elif self.shading_mode == 2:
            program = self.phong_program
        else:
            program = self.shader_program

        glEnable(GL_BLEND)
        glBlendFunc(
            GL_SRC_ALPHA,
            GL_ONE_MINUS_SRC_ALPHA
        )
        if self.shadow_enabled:

            shadow_model = (
                translate(
                    self.tx,
                    self.ty,
                    0
                )
                @ shadow_matrix()
                @ self.arcball_rotation
                @ rotate_x(self.rot_x)
                @ rotate_y(self.rot_y + self.angle)
                @ rotate_z(self.rot_z)
            )

            shadow_mvp = (
                projection
                @ view
                @ shadow_model
            )

            glUseProgram(
                self.shadow_program
            )

            loc = glGetUniformLocation(
                self.shadow_program,
                "modelview_projection_matrix"
            )

            glUniformMatrix4fv(
                loc,
                1,
                GL_TRUE,
                shadow_mvp
            )

            glBindVertexArray(
                self.vertex_array
            )

            glDrawElements(
                GL_TRIANGLES,
                len(self.indices),
                GL_UNSIGNED_INT,
                None
            )
        glUseProgram(program)
        
        # determine location of uniform variable varName
        varLocation = glGetUniformLocation(
            program,
            'modelview_projection_matrix'
        )
        # pass value to shader
        glUniformMatrix4fv(varLocation, 1, GL_TRUE, mvp_matrix)

        # enable vertex array & draw triangle(s)
        glBindVertexArray(self.vertex_array)
        # glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

        glDrawElements(
            GL_TRIANGLES,
            len(self.indices),
            GL_UNSIGNED_INT,
            None
        )

        # unbind the shader and vertex array state
        glUseProgram(0)
        glBindVertexArray(0)
        


class RenderWindow:
    """
        GLFW Rendering window class
    """

    def __init__(self, scene):
        # initialize GLFW
        if not glfw.init():
            sys.exit(EXIT_FAILURE)

        # request window with old OpenGL 3.2
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 2)

        # make a window
        self.width, self.height = scene.width, scene.height
        self.aspect = self.width / self.height
        self.window = glfw.create_window(self.width, self.height, scene.scenetitle, None, None)
        if not self.window:
            glfw.terminate()
            sys.exit(EXIT_FAILURE)

        # Make the window's context current
        glfw.make_context_current(self.window)

        # initialize GL
        self.init_GL()

        # set window callbacks
        glfw.set_mouse_button_callback(self.window, self.on_mouse_button)
        glfw.set_cursor_pos_callback(
            self.window,
            self.on_mouse_move
        )
        glfw.set_key_callback(self.window, self.on_keyboard)
        glfw.set_window_size_callback(self.window, self.on_size)

        # create scene
        self.scene = scene  
        if not self.scene:
            glfw.terminate()
            sys.exit(EXIT_FAILURE)

        self.scene.init_GL()

        # exit flag
        self.exitNow = False

        self.last_x = 0
        self.last_y = 0

        self.left_pressed = False
        self.middle_pressed = False
        self.right_pressed = False
        self.arcball_start = None


    def init_GL(self):
        # debug: print GL and GLS version
        # print('Vendor       : %s' % glGetString(GL_VENDOR))
        # print('OpenGL Vers. : %s' % glGetString(GL_VERSION))
        # print('GLSL Vers.   : %s' % glGetString(GL_SHADING_LANGUAGE_VERSION))
        # print('Renderer     : %s' % glGetString(GL_RENDERER))

        # set background color to gray
        glClearColor(0.1, 0.1, 0.1, 1.0) 

        # Enable depthtest
        glEnable(GL_DEPTH_TEST)


    def on_mouse_button(
            self,
            win,
            button,
            action,
            mods):

        if button == glfw.MOUSE_BUTTON_LEFT:

            self.left_pressed = (
                action == glfw.PRESS
            )

            if action == glfw.PRESS:

                x, y = glfw.get_cursor_pos(win)

                self.arcball_start = (
                    project_on_sphere(
                        x,
                        y,
                        self.scene.width,
                        self.scene.height
                    )
                )

        if button == glfw.MOUSE_BUTTON_MIDDLE:
            self.middle_pressed = (
                action == glfw.PRESS
            )

        if button == glfw.MOUSE_BUTTON_RIGHT:
            self.right_pressed = (
                action == glfw.PRESS
            )

        self.last_x, self.last_y = (
            glfw.get_cursor_pos(win)
        )

    def on_mouse_move(
            self,
            win,
            xpos,
            ypos):

        dx = xpos - self.last_x
        dy = ypos - self.last_y

        self.last_x = xpos
        self.last_y = ypos

        if self.middle_pressed:

            self.scene.zoom += dy * 0.01

            self.scene.zoom = max(
                0.5,
                self.scene.zoom
            )

        if self.right_pressed:

            self.scene.tx += dx * 0.005
            self.scene.ty -= dy * 0.005
        if self.left_pressed:

            current = project_on_sphere(
                xpos,
                ypos,
                self.scene.width,
                self.scene.height
            )

            start = self.arcball_start

            axis = np.cross(
                start,
                current
            )

            axis_length = np.linalg.norm(axis)

            if axis_length > 1e-6:

                axis /= axis_length

                angle = np.degrees(
                    np.arccos(
                        np.clip(
                            np.dot(
                                start,
                                current
                            ),
                            -1.0,
                            1.0
                        )
                    )
                )

                rotation = rotate(
                    angle,
                    axis
                )

                self.scene.arcball_rotation = (
                    rotation
                    @ self.scene.arcball_rotation
                )

            self.arcball_start = current

    def on_keyboard(self, win, key, scancode, action, mods):
        print("keyboard: ", win, key, scancode, action, mods)
        if action == glfw.PRESS:
            # ESC to quit
            if key == glfw.KEY_ESCAPE:
                self.exitNow = True
            if key == glfw.KEY_A:
                self.scene.animate = not self.scene.animate
            if key == glfw.KEY_P:
                self.scene.use_perspective = (
                    not self.scene.use_perspective
                )

                print(
                    "Perspective:"
                    if self.scene.use_perspective
                    else "Orthographic"
                )
            if key == glfw.KEY_S:
                self.scene.shading_mode = (
                    self.scene.shading_mode + 1
                ) % 3

                print("Shading:",
                    self.scene.shading_mode)
            if key == glfw.KEY_X:
                self.scene.rot_x += 10
            if key == glfw.KEY_Y:
                self.scene.rot_y += 10
            if key == glfw.KEY_Z:
                self.scene.rot_z += 10


    def on_size(self, win, width, height):
        self.scene.set_size(width, height)


    def run(self):
        while not glfw.window_should_close(self.window) and not self.exitNow:
            # poll for and process events
            glfw.poll_events()

            # setup viewport
            width, height = glfw.get_framebuffer_size(self.window)
            glViewport(0, 0, width, height);

            # call the rendering function
            self.scene.draw()
            
            # swap front and back buffer
            glfw.swap_buffers(self.window)

        # end
        glfw.terminate()



# main function
if __name__ == '__main__':

    print("presse 'a' to toggle animation...")

    # set size of render viewport
    width, height = 640, 480

    # instantiate a scene
    scene = Scene(width, height)

    # pass the scene to a render window ... 
    rw = RenderWindow(scene)

    # ... and start main loop
    rw.run()
