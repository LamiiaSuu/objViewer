#version 330

layout(location=0) in vec3 v_position;
layout(location=1) in vec3 v_normal;

uniform mat4 modelview_projection_matrix;

out vec3 normal;

void main()
{
    normal = normalize(v_normal);

    gl_Position =
        modelview_projection_matrix *
        vec4(v_position, 1.0);
}