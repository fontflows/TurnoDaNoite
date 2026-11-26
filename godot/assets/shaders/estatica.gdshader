// Estática de TV (chiado preto e branco) para fundos de tela, monitor de câmeras e susto.
// Funciona no renderer Compatibility.
shader_type canvas_item;

// 0 = sem chiado (só a cor de fundo), 1 = chiado total.
uniform float intensidade : hint_range(0.0, 1.0) = 0.5;
// Cor por baixo do chiado.
uniform vec4 cor_fundo : source_color = vec4(0.0, 0.0, 0.0, 1.0);
// Quantas vezes por segundo o chiado muda.
uniform float velocidade = 24.0;
// Tamanho do "grão" em pixels.
uniform float tamanho_grao = 2.0;

float aleatorio(vec2 c) {
	return fract(sin(dot(c, vec2(12.9898, 78.233))) * 43758.5453);
}

void fragment() {
	float quadro = floor(TIME * velocidade);
	vec2 grao = floor(FRAGCOORD.xy / tamanho_grao);
	float ruido = aleatorio(grao + quadro * 1.618);
	// Faixa clara que desce devagar, como numa TV velha.
	float faixa = 1.0 - smoothstep(0.0, 0.08, abs(fract(UV.y * 0.8 - TIME * 0.25) - 0.5));
	float linhas = 0.85 + 0.15 * sin(FRAGCOORD.y * 3.14159);
	vec3 cor = mix(cor_fundo.rgb, vec3(ruido), intensidade * linhas);
	cor += faixa * 0.12 * intensidade;
	COLOR = vec4(cor, cor_fundo.a);
}
