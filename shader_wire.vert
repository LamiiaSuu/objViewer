#version 330

layout(location=0) in vec3 v_position;

uniform mat4 modelview_projection_matrix;

void main()
{
    gl_Position =
        modelview_projection_matrix *
        vec4(v_position,1.0);
}