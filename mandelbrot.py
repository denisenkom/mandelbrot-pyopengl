import glfw
import OpenGL.GL as gl
import numpy


vertex_shader_src = '''
#version 410 core
layout(location = 0) in vec3 vertexPosition_modelspace;

// Output data ; will be interpolated for each fragment.
out vec2 fragmentCoord;

void main(){
  gl_Position = vec4(vertexPosition_modelspace, 1);
  fragmentCoord = vec2(vertexPosition_modelspace.x, vertexPosition_modelspace.y);
}
'''

fragment_shader_src = '''
#version 410 core

in vec2 fragmentCoord;
out vec3 color;

uniform dmat3 transform;

uniform int max_iters = 1000;


vec3 hsv2rgb(vec3 c)
{
    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}


vec3 map_color(int i, float r, float c) {
    float di = i;
    float zn = sqrt(r + c);
    float hue = (di + 1 - log(log2(abs(zn))))/max_iters;
    return hsv2rgb(vec3(hue, 0.8, 1));
}


void main(){
    dvec3 pointCoord = dvec3(fragmentCoord.xy, 1);
    pointCoord *= transform;
    double cx = pointCoord.x;
    double cy = pointCoord.y;
    int iter = 0;
    double zx = 0;
    double zy = 0;
    while (iter < max_iters) {
        double nzx = zx * zx - zy * zy + cx;
        double nzy = 2 * zx * zy + cy;
        zx = nzx;
        zy = nzy;
        if (zx*zx + zy*zy > 4.0) {
            break;
        }
        iter += 1;
    }
    if (iter == max_iters) {
        color = vec3(0,0,0);
    } else {
        color = map_color(iter, float(zx*zx), float(zy*zy));
    }
}
'''


def make_shader(shader_type, src):
    shader = gl.glCreateShader(shader_type)
    gl.glShaderSource(shader, src)
    gl.glCompileShader(shader)
    status = gl.glGetShaderiv(shader, gl.GL_COMPILE_STATUS)
    if status == gl.GL_FALSE:
        # Note that getting the error log is much simpler in Python than in C/C++
        # and does not require explicit handling of the string buffer
        strInfoLog = gl.glGetShaderInfoLog(shader).decode('ascii')
        strShaderType = ""
        if shader_type is gl.GL_VERTEX_SHADER:
            strShaderType = "vertex"
        elif shader_type is gl.GL_GEOMETRY_SHADER:
            strShaderType = "geometry"
        elif shader_type is gl.GL_FRAGMENT_SHADER:
            strShaderType = "fragment"

        raise Exception("Compilation failure for " + strShaderType + " shader:\n" + strInfoLog)

    return shader


def make_program(shader_list):
    program = gl.glCreateProgram()

    for shader in shader_list:
        gl.glAttachShader(program, shader)

    gl.glLinkProgram(program)

    status = gl.glGetProgramiv(program, gl.GL_LINK_STATUS)
    if status == gl.GL_FALSE:
        # Note that getting the error log is much simpler in Python than in C/C++
        # and does not require explicit handling of the string buffer
        strInfoLog = gl.glGetProgramInfoLog(program)
        raise Exception("Linker failure: \n" + strInfoLog)

    for shader in shader_list:
        gl.glDetachShader(program, shader)

    return program


def main():
    if not glfw.init():
        return

    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 1)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.DOUBLEBUFFER, 0)
    glfw.window_hint(glfw.SAMPLES, 16)

    width = 1920
    height = 1080
    aspect = 1.0 * width / height

    window = glfw.create_window(width, height, "Mandelbrot", None, None)
    if not window:
        glfw.terminate()
        return

    glfw.make_context_current(window)

    # print(f"opengl version: {gl.glGetString(gl.GL_VERSION).decode('ascii')}")
    # print(f"opengl vendor: {gl.glGetString(gl.GL_VENDOR).decode('ascii')}")
    # print(f"opengl renderer: {gl.glGetString(gl.GL_RENDERER).decode('ascii')}")

    vertex_shader = make_shader(gl.GL_VERTEX_SHADER, vertex_shader_src)
    fragment_shader = make_shader(gl.GL_FRAGMENT_SHADER, fragment_shader_src)

    program = make_program([vertex_shader, fragment_shader])

    vert_values = numpy.array([-1, -1 * aspect, 0,
                               1, -1 * aspect, 0,
                               -1, 1 * aspect, 0,
                               -1, 1 * aspect, 0,
                               1, -1 * aspect, 0,
                               1, 1 * aspect, 0,
                               ], dtype='float64')

    # creating vertex array
    vert_array = gl.glGenVertexArrays(1)
    gl.glBindVertexArray(vert_array)

    vert_buffer = gl.glGenBuffers(1)
    gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vert_buffer)
    gl.glBufferData(gl.GL_ARRAY_BUFFER, vert_values, gl.GL_STATIC_DRAW)

    gl.glClearColor(0, 0, 0, 0)
    gl.glClear(gl.GL_COLOR_BUFFER_BIT)
    gl.glUseProgram(program)

    # setup coordinate buffer
    gl.glEnableVertexAttribArray(0)
    gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vert_buffer)
    gl.glVertexAttribPointer(0, 3, gl.GL_DOUBLE, gl.GL_FALSE, 0, None)

    # setup uniforms for fragment shader
    transform_loc = gl.glGetUniformLocation(program, 'transform')
    max_iters_loc = gl.glGetUniformLocation(program, 'max_iters')

    # setup color buffer
    # gl.glEnableVertexAttribArray(1)
    # gl.glBindBuffer(gl.GL_ARRAY_BUFFER, color_buffer)
    # gl.glVertexAttribPointer(1, 3, gl.GL_FLOAT, gl.GL_FALSE, 0, None)

    state = {
        'zoom': 1,
        'pos_x': -0.7600189058857209,
        'pos_y': 0.0799516080512771,
        'max_iters': 100,
    }

    def char_callback(window, char):
        ch = chr(char)
        change = False
        if ch == '-':
            state['zoom'] *= 1.1
            state['zoom'] = min(10, state['zoom'])
            change = True
        elif ch in ('+', '='):
            state['zoom'] *= 0.9
            change = True
        elif ch == ']':
            state['max_iters'] *= 1.1
            change = True
        elif ch == '[':
            state['max_iters'] *= 0.9
            change = True
        if change:
            print('Current zoom:', state['zoom'])
            print('Current max_iters:', state['max_iters'])

    def key_callback(window, key, scancode, action, mods):
        change = False
        if action in (glfw.PRESS, glfw.REPEAT):
            if key == glfw.KEY_UP:
                state['pos_y'] += state['zoom'] * 0.02
                change = True
            elif key == glfw.KEY_DOWN:
                state['pos_y'] -= state['zoom'] * 0.02
                change = True
            elif key == glfw.KEY_RIGHT:
                state['pos_x'] += state['zoom'] * 0.02
                change = True
            elif key == glfw.KEY_LEFT:
                state['pos_x'] -= state['zoom'] * 0.02
                change = True
        if change:
            print('Current center:', state['pos_x'], state['pos_y'])


    glfw.set_char_callback(window, char_callback)
    glfw.set_key_callback(window, key_callback)
    time_before = glfw.get_time()

    print("use +/- to zoom in/out")
    print("use [/] to increase/decrease max_iters")
    print("use arrows to pan")

    while not glfw.window_should_close(window):
        zoom = state['zoom']
        pos_x = state['pos_x']
        pos_y = state['pos_y']
        gl.glUniformMatrix3dv(transform_loc, 1, False,
                              numpy.array([aspect * zoom, 0, pos_x, 0, 1 * zoom, pos_y, 0, 0, 1 * zoom], dtype='float64'))
        gl.glUniform1i(max_iters_loc, int(state['max_iters']))

        gl.glDrawArrays(gl.GL_TRIANGLES, 0, int(len(vert_values) / 3))
        time = glfw.get_time()
        print("frame render time", time - time_before)
        time_before = time

        gl.glFlush()

        glfw.wait_events()

    glfw.terminate()


if __name__ == '__main__':
    main()