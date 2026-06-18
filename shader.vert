#version 330

layout(location=0) in vec3 v_position;
layout(location=1) in vec3 v_normal;

uniform mat4 modelview_projection_matrix;

out vec3 v2f_color;

void main()
{
    vec3 lightDir = normalize(vec3(1.0, 1.0, 1.0));

    float diffuse = max(dot(normalize(v_normal), lightDir), 0.0);

    vec3 ambient = vec3(0.2);
    vec3 color = ambient + diffuse * vec3(0.8);

    v2f_color = color;

    gl_Position = modelview_projection_matrix *
                  vec4(v_position, 1.0);
}