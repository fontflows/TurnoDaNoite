// Filtro de tela "fita VHS": granulação, linhas de scan, aberração cromática leve,
// vinheta e uma tremida horizontal de vez em quando.
// Também aplica o BRILHO (gamma) das opções, que vale mesmo com o VHS desligado.
// Funciona no renderer Compatibility (lê a tela com hint_screen_texture).
shader_type canvas_item;

uniform sampler2D tela : hint_screen_texture, filter_linear_mipmap;

// Força dos efeitos de VHS (0 = imagem limpa, 1 = máximo).
uniform float intensidade : hint_range(0.0, 1.0) = 0.6;
// Brilho: 1 = normal, maior = mais claro, menor = mais escuro.
uniform float gamma : hint_range(0.3, 2.0) = 1.0;

float aleatorio(vec2 c) {
	return fract(sin(dot(c, vec2(12.9898, 78.233))) * 43758.5453);
}

void fragment() {
	vec2 uv = SCREEN_UV;
	float k = intensidade;

	// Tremida: algumas vezes por segundo sorteamos se uma faixa da tela "pula" para o lado.
	float sorteio = floor(TIME * 6.0);
	float tremendo = step(0.96, aleatorio(vec2(sorteio, 1.7)));
	float altura_faixa = aleatorio(vec2(sorteio, 3.1));
	float na_faixa = 1.0 - smoothstep(0.0, 0.05, abs(uv.y - altura_faixa));
	uv.x += (tremendo * na_faixa * 0.025 + sin(uv.y * 180.0 + TIME * 15.0) * 0.0005) * k;

	// Aberração cromática: vermelho e azul ficam um pouquinho deslocados.
	float desvio = 0.0028 * k;
	vec3 cor;
	cor.r = texture(tela, uv + vec2(desvio, 0.0)).r;
	cor.g = texture(tela, uv).g;
	cor.b = texture(tela, uv - vec2(desvio, 0.0)).b;

	// Brilho (gamma): sempre aplicado.
	cor = pow(max(cor, vec3(0.0)), vec3(1.0 / max(gamma, 0.01)));

	// Linhas de scan (linhas horizontais escuras alternadas).
	float linha = 0.5 + 0.5 * sin(FRAGCOORD.y * 3.14159);
	cor *= 1.0 - k * 0.16 * linha;

	// Granulação que muda a cada quadro.
	float grao = aleatorio(floor(FRAGCOORD.xy) + fract(TIME * 7.13) * 91.7) - 0.5;
	cor += grao * 0.11 * k;

	// Vinheta: cantos mais escuros.
	vec2 centro = SCREEN_UV - 0.5;
	float vinheta = smoothstep(0.85, 0.3, length(centro * vec2(1.0, 1.15)));
	cor *= mix(1.0, vinheta, 0.8 * k);

	COLOR = vec4(cor, 1.0);
}
