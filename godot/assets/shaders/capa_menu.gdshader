shader_type canvas_item;
// Capa do menu com DUAS versões (fofa e sombria) e o efeito de fita VHS que troca uma pela outra.
//   mistura: 0 = capa fofa, 1 = capa sombria
//   glitch:  0 = imagem limpa, 1 = fita embolando (faixas deslocadas, cores separadas, chiado)
// Se não houver a imagem sombria, ela é feita aqui mesmo a partir da fofa (escura, fria, com vinheta).

uniform sampler2D capa_fofa : filter_linear_mipmap, repeat_disable;
uniform sampler2D capa_sombria : filter_linear_mipmap, repeat_disable;
uniform bool tem_sombria = false;
uniform float mistura : hint_range(0.0, 1.0) = 0.0;
uniform float glitch : hint_range(0.0, 1.0) = 0.0;
// Recorte da arte (x0, y0, x1, y1 em 0..1): tira a moldura de papel das imagens.
uniform vec4 recorte = vec4(0.0, 0.0, 1.0, 1.0);
// Tamanho da tela em pixels (para a imagem cobrir a tela sem esticar).
uniform vec2 tamanho_tela = vec2(1280.0, 720.0);

float aleatorio(vec2 p) {
	return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

// UV da tela -> UV da imagem, "cobrindo" a tela (corta o que sobra, sem esticar).
vec2 uv_cobrindo(vec2 uv, sampler2D img) {
	vec2 tam = vec2(textureSize(img, 0)) * (recorte.zw - recorte.xy);
	float a_tela = tamanho_tela.x / tamanho_tela.y;
	float a_img = tam.x / tam.y;
	if (a_tela > a_img) {
		uv.y = 0.5 + (uv.y - 0.5) * (a_img / a_tela);
	} else {
		uv.x = 0.5 + (uv.x - 0.5) * (a_tela / a_img);
	}
	return recorte.xy + uv * (recorte.zw - recorte.xy);
}

// Lê a imagem com as cores levemente separadas (o vermelho e o azul "escorregam" na fita).
vec3 ler(sampler2D img, vec2 uv, float separacao) {
	vec2 base = uv_cobrindo(uv, img);
	return vec3(texture(img, base + vec2(separacao, 0.0)).r, texture(img, base).g, texture(img, base - vec2(separacao, 0.0)).b);
}

// Versão sombria feita por código: quase sem cor, bem escura, puxada para o vermelho, com vinheta.
vec3 sombria_por_codigo(vec3 c, vec2 uv) {
	float l = dot(c, vec3(0.299, 0.587, 0.114));
	vec3 d = mix(vec3(l), c, 0.2) * 0.5;
	d *= vec3(1.15, 0.72, 0.78);
	d = pow(d, vec3(1.4));
	float vinheta = smoothstep(0.95, 0.2, distance(uv, vec2(0.62, 0.45)));
	return d * vinheta;
}

void fragment() {
	vec2 uv = UV;
	float t = TIME;
	// Faixas horizontais deslocadas (só algumas, sorteadas a cada instante).
	float banda = floor(uv.y * 36.0);
	float sorteio = aleatorio(vec2(banda, floor(t * 24.0)));
	float desloca = (aleatorio(vec2(banda * 1.7, floor(t * 31.0))) - 0.5) * 0.14 * glitch * step(0.55, sorteio);
	uv.x += desloca;
	uv.y += sin(uv.y * 260.0 + t * 45.0) * 0.0025 * glitch;
	float separacao = 0.0012 + 0.008 * glitch;

	vec3 fofa = ler(capa_fofa, uv, separacao);
	vec3 sombra = tem_sombria ? ler(capa_sombria, uv, separacao) : sombria_por_codigo(fofa, UV);
	vec3 cor = mix(fofa, sombra, mistura);

	// Chiado de fita e a barra escura que "rola" na tela durante o glitch.
	float chiado = aleatorio(UV * vec2(640.0, 360.0) + vec2(t * 13.0, t * 7.0));
	cor = mix(cor, vec3(chiado), glitch * 0.45);
	float barra = smoothstep(0.0, 0.04, abs(fract(UV.y - t * 0.8) - 0.5));
	cor *= mix(1.0, 0.55 + 0.45 * barra, glitch);
	// Linhas de varredura bem leves o tempo todo.
	cor *= 0.94 + 0.06 * sin(UV.y * tamanho_tela.y * 3.14159);
	COLOR = vec4(cor, 1.0);
}
