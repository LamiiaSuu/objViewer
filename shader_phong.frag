#version 330

in vec3 normal;

out vec4 f_color;

void main()
{
    vec3 lightDir =
        normalize(vec3(1.0,1.0,1.0));

    float diffuse =
        max(dot(normalize(normal),
                lightDir), 0.0);

    vec3 ambient = vec3(0.2);

    vec3 color =
        ambient +
        diffuse * vec3(0.8);

    f_color = vec4(color,1.0);
}