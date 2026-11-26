// Papel de planta azul (blueprint) velho, usado na tela do mapa (MapaVigia).
// Tudo é calculado no fragment shader a partir do UV, então não precisa de textura:
//  - manchas grandes e suaves (ruído de valor em duas escalas), como papel desbotado;
//  - fibras finas do papel (ruído por pixel);
//  - duas dobras (o papel foi dobrado em quatro e guardado no bolso do vigia);
//  - bordas mais escuras e gastas.
shader_type canvas_item;

// Azul claro e azul escuro do papel; as manchas misturam os dois.
uniform vec4 cor_clara : source_color = vec4(0.13, 0.29, 0.53, 1.0);
uniform vec4 cor_escura : source_color = vec4(0.06, 0.15, 0.32, 1.0);
// Força das dobras (0 = papel liso).
uniform float forca_dobras : hint_range(0.0, 1.0) = 0.6;

// Número pseudoaleatório entre 0 e 1 para cada ponto.
float aleatorio(vec2 c) {
	return fract(sin(dot(c, vec2(12.9898, 78.233))) * 43758.5453);
}

// Ruído de valor: sorteia um número em cada canto da célula e interpola suavemente.
float ruido(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	float a = aleatorio(i);
	float b = aleatorio(i + vec2(1.0, 0.0));
	float c = aleatorio(i + vec2(0.0, 1.0));
	float d = aleatorio(i + vec2(1.0, 1.0));
	return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}

void fragment() {
	vec2 uv = UV;

	// Manchas: duas camadas de ruído (grande + média).
	float manchas = ruido(uv * vec2(5.0, 4.0)) * 0.65 + ruido(uv * vec2(13.0, 10.0) + 7.3) * 0.35;
	vec3 cor = mix(cor_escura.rgb, cor_clara.rgb, 0.45 + 0.55 * manchas);

	// Fibras do papel: um ruído bem fino, fixo (não muda com o tempo).
	float fibra = aleatorio(floor(FRAGCOORD.xy * 0.5)) - 0.5;
	cor += fibra * 0.035;

	// Dobras: uma linha clara (o vinco) com um lado um pouco mais escuro (a sombra).
	float dx = uv.x - 0.5;
	float dy = uv.y - 0.5;
	float vinco = (1.0 - smoothstep(0.0, 0.003, abs(dx))) + (1.0 - smoothstep(0.0, 0.004, abs(dy)));
	float sombra = smoothstep(0.0, 0.03, dx) * (1.0 - smoothstep(0.03, 0.08, dx))
		+ smoothstep(0.0, 0.04, dy) * (1.0 - smoothstep(0.04, 0.1, dy));
	cor += vinco * 0.07 * forca_dobras;
	cor -= sombra * 0.035 * forca_dobras;

	// Bordas gastas: escurece perto das beiradas.
	vec2 c = abs(uv - 0.5);
	float borda = smoothstep(0.38, 0.5, max(c.x, c.y));
	cor *= 1.0 - 0.35 * borda;

	COLOR = vec4(cor, 1.0);
}
