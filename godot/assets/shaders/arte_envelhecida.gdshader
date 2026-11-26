// Arte impressa e envelhecida: pôsteres, letreiros, painéis, capas.
// Pega uma imagem "limpa" (do Gemini ou feita por código) e deixa com cara de papel velho:
// desbotada, amarelada, com sujeira, dobras e bordas gastas. Por cima, o texto colocado pelo jogo.
// Figuras de papelão (fundo_verde): o verde chapado do fundo é apagado (chroma key) e o
// recorte é feito com ALPHA SCISSOR (o pixel some ou fica; não há meio-transparente, então
// a figura continua no passe opaco, com profundidade e sombra certas).
shader_type spatial;
render_mode cull_disabled;

uniform sampler2D arte : source_color, filter_linear_mipmap, repeat_disable;
// Texto do jogo (com fundo transparente) desenhado por cima da arte.
uniform sampler2D texto : source_color, filter_linear_mipmap, repeat_disable;
uniform bool tem_texto = false;
// Pedaço da imagem que aparece (x0, y0, x1, y1), para recortar bordas (ex.: lateral do fliperama).
uniform vec4 recorte = vec4(0.0, 0.0, 1.0, 1.0);
uniform sampler2D sujeira : hint_default_black, filter_linear_mipmap;
// 0 = imagem nova; 1 = muito velha.
uniform float idade : hint_range(0.0, 1.0) = 0.55;
// Brilho próprio (letreiros iluminados do fliperama); 0 = só reflete a luz da cena.
uniform float brilho_proprio = 0.0;
// Semente para cada cópia ter manchas e dobras em lugares diferentes.
uniform float semente = 0.0;
// Chroma key: apaga o fundo verde (#00FF00) da imagem (figura de papelão recortada).
uniform bool fundo_verde = false;
// Camada de espessura da figura de papelão: usa só o recorte e pinta de papelão.
uniform bool so_papelao = false;
uniform vec3 cor_papelao : source_color = vec3(0.56, 0.43, 0.29);

float aleatorio(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233)) + semente) * 43758.5453); }

void fragment() {
	// O exportador glTF já entrega a UV no padrão do Godot (V cresce para baixo): usamos direto.
	vec2 uv = mix(recorte.xy, recorte.zw, UV);
	vec3 cor = texture(arte, uv).rgb;
	float alfa = 1.0;
	if (fundo_verde) {
		// Quanto o verde "ganha" dos outros canais: alto no fundo chapado, baixo na figura.
		float verde = cor.g - max(cor.r, cor.b);
		alfa = 1.0 - smoothstep(0.2, 0.35, verde);
		// Tira o verde que "vaza" na borda da figura (despill).
		cor.g = min(cor.g, max(cor.r, cor.b) + 0.04);
	}
	if (so_papelao) {
		float s0 = texture(sujeira, UV * 3.1 + semente).r;
		cor = cor_papelao * (0.9 + 0.15 * s0);
	} else if (tem_texto) {
		vec4 t = texture(texto, UV);
		cor = mix(cor, t.rgb, t.a);
	}
	// Desbotar: menos saturação e um amarelado de papel velho.
	float cinza = dot(cor, vec3(0.299, 0.587, 0.114));
	cor = mix(cor, vec3(cinza), 0.35 * idade);
	cor = mix(cor, cor * vec3(1.0, 0.93, 0.78), 0.6 * idade);
	// Sujeira: máscara repetida + mais escuro perto das bordas (não na figura recortada).
	float s = texture(sujeira, UV * 1.7 + semente * 0.37).r;
	float borda = smoothstep(0.0, 0.08, min(min(UV.x, 1.0 - UV.x), min(UV.y, 1.0 - UV.y)));
	if (!fundo_verde) {
		cor *= mix(1.0, 0.55 + 0.45 * borda, idade);
	}
	cor *= 1.0 - s * 0.45 * idade;
	// Dobras: linhas finas em 1/2 e 1/3, como papel que ficou dobrado.
	if (!fundo_verde) {
		float dobra = 1.0 - 0.18 * idade * (smoothstep(0.004, 0.0, abs(UV.x - 0.5)) + smoothstep(0.004, 0.0, abs(UV.y - 0.33)));
		cor *= dobra;
	}
	// Pontinhos de mofo.
	cor *= 1.0 - 0.25 * idade * step(0.997, aleatorio(floor(UV * 180.0)));
	ALBEDO = cor;
	ROUGHNESS = 0.85;
	EMISSION = cor * brilho_proprio;
	ALPHA = alfa;
	ALPHA_SCISSOR_THRESHOLD = 0.5;
}
