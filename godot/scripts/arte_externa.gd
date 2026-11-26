class_name ArteExterna
extends Node
## Põe as artes nos planos "Arte__<nome>" que vêm do Blender (pôsteres, letreiros, painéis).
##
## 1. Se existir a imagem do Gemini (godot/assets/arte_externa/<pasta>/<nome>.jpg|png|webp,
##    conforme o manifesto_arte.json), usa ela.
## 2. Se não existir, desenha uma versão feita por código (fundo, desenho simples e texto).
## 3. Em cima, escreve os textos do jogo (título, linhas e itens do manifesto) com as fontes do projeto.
##    O tamanho da letra é AJUSTADO para caber na área sem quebrar palavras no meio.
## 4. Tudo passa pelo shader de envelhecimento (desbotado, sujeira, dobras).
## 5. Artes com "fundo_verde" (figura de papelão) têm o verde apagado (chroma key) e ganham
##    espessura de papelão feita com camadas recortadas pela mesma máscara.
##
## Para trocar uma arte: coloque a imagem com o nome certo e abra o jogo. Nada mais.
## Toda arte usada no Blender PRECISA estar no manifesto ou em PROCEDURAIS: se não estiver,
## aparece só um cartaz liso com o nome do arquivo (o validador dev/validar_artes.tscn acusa).

const PASTA := "res://assets/arte_externa"
const MANIFESTO := "res://assets/arte_externa/manifesto_arte.json"
const SHADER := preload("res://assets/shaders/arte_envelhecida.gdshader")
const SUJEIRA := "res://assets/texturas/sujeira_cantos/sujeira_cantos_cor.png"
const FONTES := {
	"titulo": preload("res://assets/fontes/Bungee/Bungee-Regular.ttf"),
	"documento": preload("res://assets/fontes/CourierPrime/CourierPrime-Regular.ttf"),
	"manuscrito": preload("res://assets/fontes/Caveat/Caveat-Variable.ttf"),
	"redonda": preload("res://assets/fontes/Fredoka/Fredoka-Variable.ttf"),
}
## Lado maior da imagem desenhada por código (pixels).
const RESOLUCAO := 768
## Espessura da figura de papelão (camadas de 1,5 mm atrás da arte).
const CAMADAS_PAPELAO := 4
const PASSO_PAPELAO := 0.0015

## Como desenhar as artes quando não há imagem (ou para as que só existem no jogo).
## Campos: titulo, linhas, fundo, cor (do texto), fonte_titulo, fonte_linhas, alinhar ("esquerda"),
## enfeite (desenho simples feito com formas: estrelas, piratas, princesas, baloes, mapa, urso).
## Os textos do manifesto (campo "texto" e "linhas") têm prioridade sobre os daqui.
const PROCEDURAIS := {
	"regras_vigia": {"titulo": "REGRAS DO VIGIA NOTURNO", "fundo": Color(0.86, 0.82, 0.7), "cor": Color(0.15, 0.12, 0.1),
		"linhas": ["1. Nunca deixe os animatrônicos te verem correndo.", "2. Se o Tito estiver olhando, olhe de volta.",
			"3. A lanterna é sua amiga. A bateria, nem tanto.", "4. Não abra a porta se ouvir música.",
			"5. Às 6h em ponto, o turno acaba. Seja pontual."], "fonte_linhas": "documento", "alinhar": "esquerda"},
	"funcionario_do_mes": {"titulo": "FUNCIONÁRIO DO MÊS", "fundo": Color(0.75, 0.72, 0.62), "cor": Color(0.2, 0.15, 0.1),
		"linhas": ["(a foto foi riscada com caneta)"], "fonte_linhas": "manuscrito", "enfeite": "foto_riscada"},
	"cartaz_regras_festa": {"titulo": "REGRAS DA FESTA", "fundo": Color(0.95, 0.9, 0.62), "cor": Color(0.35, 0.12, 0.1),
		"linhas": ["1. Crianças sempre com um adulto.", "2. Não suba no palco.", "3. Não mexa nos animatrônicos.",
			"4. Bolo só depois do parabéns!", "5. A festa acaba às 21h."], "fonte_linhas": "redonda", "alinhar": "esquerda"},
	"cartaz_festa_estrelas": {"fundo": Color(0.08, 0.1, 0.3), "enfeite": "estrelas"},
	"cartaz_festa_piratas": {"fundo": Color(0.55, 0.8, 0.95), "cor": Color(0.25, 0.1, 0.05), "enfeite": "piratas"},
	"cartaz_festa_princesas": {"fundo": Color(0.98, 0.72, 0.85), "cor": Color(0.45, 0.1, 0.35), "enfeite": "princesas"},
	"cartaz_parabens": {"fundo": Color(0.95, 0.3, 0.3), "enfeite": "baloes"},
	"pista_aniversario": {"fundo": Color(0.38, 0.55, 0.88), "cor": Color(1, 0.96, 0.82), "enfeite": "baloes"},
	"mapa_tesouro": {"titulo": "MAPA DO TESOURO", "fundo": Color(0.86, 0.76, 0.55), "cor": Color(0.35, 0.2, 0.08),
		"enfeite": "mapa"},
	"standee_tito": {"titulo": "", "fundo": Color(0, 1, 0), "enfeite": "urso"},
}

var _manifesto := {}  # nome sem extensão -> dados da arte
var _sujeira: Texture2D


func _ready() -> void:
	carregar_manifesto()


func carregar_manifesto() -> void:
	if not _manifesto.is_empty():
		return
	if FileAccess.file_exists(MANIFESTO):
		var dados: Variant = JSON.parse_string(FileAccess.get_file_as_string(MANIFESTO))
		if dados is Dictionary:
			for a: Dictionary in (dados as Dictionary).get("artes", []):
				_manifesto[String(a["arquivo"]).get_basename()] = a
	if ResourceLoader.exists(SUJEIRA):
		_sujeira = load(SUJEIRA)


## Nome da arte a partir do nome do nó ("Arte__lateral_arcade_001" -> "lateral_arcade").
func nome_da_arte(nome_no: String) -> String:
	var nome := nome_no.trim_prefix("Arte__")
	if not _manifesto.has(nome) and not PROCEDURAIS.has(nome):
		var partes := nome.rsplit("_", true, 1)
		if partes.size() == 2 and partes[1].is_valid_int():
			nome = partes[0]
	return nome


## A arte tem definição (no manifesto ou em PROCEDURAIS)? Sem definição vira um cartaz liso.
func definida(nome: String) -> bool:
	return _manifesto.has(nome) or PROCEDURAIS.has(nome)


## Caminho da imagem do Gemini, se ela existir (aceita .jpg, .jpeg, .png e .webp).
func caminho_imagem(nome: String) -> String:
	if not _manifesto.has(nome):
		return ""
	var pasta := "%s/%s" % [PASTA, _manifesto[nome]["pasta"]]
	for ext in ["jpg", "jpeg", "png", "webp"]:
		var c := "%s/%s.%s" % [pasta, nome, ext]
		if ResourceLoader.exists(c):
			return c
	return ""


## Tudo o que será escrito numa arte: [{texto, caixa (x0, y0, x1, y1 de 0 a 1), fonte, cor, contorno, alinhar}].
## 'com_imagem' = há imagem do Gemini (os textos vão por cima dela); senão, layout da versão por código.
func textos_da_arte(nome: String, com_imagem: bool) -> Array[Dictionary]:
	var dados: Dictionary = _manifesto.get(nome, {})
	var info: Dictionary = PROCEDURAIS.get(nome, {})
	var saida: Array[Dictionary] = []
	var cor: Color = info.get("cor", Color(1, 0.96, 0.88))
	var titulo := String(dados.get("texto", ""))
	if titulo == "" and not com_imagem:
		titulo = String(info.get("titulo", nome.replace("_", " ").to_upper()))
	var tem_enfeite := info.has("enfeite") and not com_imagem
	if titulo != "":
		var caixa: Array = dados.get("caixa_texto", [])
		if caixa.is_empty():
			var pos := String(dados.get("posicao_texto", "topo")) if com_imagem else "topo"
			caixa = {"topo": [0.05, 0.03, 0.95, 0.24], "base": [0.05, 0.76, 0.95, 0.97]}.get(pos, [0.05, 0.25, 0.95, 0.75])
		saida.append({"texto": titulo, "caixa": caixa, "fonte": String(info.get("fonte_titulo", "titulo")),
			"cor": Color(1, 0.95, 0.85) if com_imagem else cor, "contorno": true, "alinhar": "centro"})
	var linhas: Array = dados.get("linhas", info.get("linhas", []))
	if not linhas.is_empty():
		var texto := "\n".join(PackedStringArray(linhas))
		# {D3}/{D4}: dígitos da senha sorteada da partida (pistas do código da sala elétrica).
		if Jogo.codigo.length() == 4:
			texto = texto.replace("{D3}", Jogo.codigo[2]).replace("{D4}", Jogo.codigo[3])
		var caixa_l: Array = dados.get("caixa_linhas", [])
		if caixa_l.is_empty():
			caixa_l = [0.08, 0.74, 0.92, 0.96] if tem_enfeite or com_imagem else [0.08, 0.28, 0.92, 0.94]
		saida.append({"texto": texto, "caixa": caixa_l, "fonte": String(info.get("fonte_linhas", "titulo" if com_imagem else "redonda")),
			"cor": Color(1, 0.95, 0.85) if com_imagem else cor, "contorno": com_imagem,
			"alinhar": String(info.get("alinhar", "centro"))})
	for item: Dictionary in dados.get("itens", []):
		saida.append({"texto": String(item["texto"]), "caixa": item["caixa"], "fonte": String(item.get("fonte", "redonda")),
			"cor": Color.html(String(item.get("cor", "#5a1e14"))), "contorno": bool(item.get("contorno", false)),
			"alinhar": String(item.get("alinhar", "centro"))})
	return saida


## Aplica a arte certa num plano. 'semente' muda a posição das manchas entre cópias.
func aplicar(malha: MeshInstance3D, semente := 0.0) -> void:
	carregar_manifesto()
	var nome := nome_da_arte(malha.name)
	var aabb := malha.get_aabb()
	var proporcao := maxf(aabb.size.x, 0.01) / maxf(aabb.size.y, 0.01)
	var dados: Dictionary = _manifesto.get(nome, {})
	var mat := ShaderMaterial.new()
	mat.shader = SHADER
	mat.set_shader_parameter("semente", semente)
	if _sujeira:
		mat.set_shader_parameter("sujeira", _sujeira)
	var caminho := caminho_imagem(nome)
	var fundo_verde := bool(dados.get("fundo_verde", false))
	mat.set_shader_parameter("fundo_verde", fundo_verde)
	malha.material_override = mat
	if caminho != "":
		mat.set_shader_parameter("arte", load(caminho))
		var textos := textos_da_arte(nome, true)
		if not textos.is_empty():
			mat.set_shader_parameter("texto", await _desenhar_textos(textos, proporcao))
			mat.set_shader_parameter("tem_texto", true)
	else:
		mat.set_shader_parameter("arte", await _desenhar_procedural(nome, proporcao))
	if dados.has("recorte"):
		var r: Array = dados["recorte"]
		mat.set_shader_parameter("recorte", Vector4(r[0], r[1], r[2], r[3]))
	# Letreiros de fliperama brilham um pouco sozinhos (são caixas iluminadas).
	if nome.begins_with("marquee_") or nome == "painel_maquina_garra":
		mat.set_shader_parameter("brilho_proprio", 0.35)
		mat.set_shader_parameter("idade", 0.35)
	if fundo_verde:
		mat.set_shader_parameter("idade", 0.3)
		_criar_espessura(malha, mat)


## Figura de papelão: cópias do plano, 1,5 mm atrás uma da outra, pintadas de papelão e
## recortadas pela MESMA máscara do chroma key. De lado, elas formam a borda grossa do recorte;
## de trás, aparece o verso de papelão (e não a arte espelhada).
func _criar_espessura(malha: MeshInstance3D, mat_frente: ShaderMaterial) -> void:
	for k in range(1, CAMADAS_PAPELAO + 1):
		var camada := MeshInstance3D.new()
		camada.name = "Espessura_Papelao_%d" % k
		camada.mesh = malha.mesh
		var m := mat_frente.duplicate() as ShaderMaterial
		m.set_shader_parameter("so_papelao", true)
		m.set_shader_parameter("tem_texto", false)
		camada.material_override = m
		camada.position = Vector3(0, 0, -PASSO_PAPELAO * k)  # a frente do plano é +Z local
		malha.add_child(camada)


# ---------------------------------------------------------------------------
# Texto que cabe: maior letra possível sem quebrar palavras no meio
# ---------------------------------------------------------------------------

## Maior tamanho de fonte (de 'maximo' para baixo) em que 'texto' cabe na área 'area' (pixels),
## quebrando linha só entre palavras. É o que evita "CARDÁ/PIO" e o "PIZZA" cortado ao meio.
static func tamanho_que_cabe(texto: String, fonte: Font, area: Vector2, maximo: int, minimo := 10) -> int:
	var t := maximo
	while t > minimo:
		if cabe(texto, fonte, area, t):
			return t
		t -= maxi(1, t / 14)
	return minimo


static func cabe(texto: String, fonte: Font, area: Vector2, tamanho: int) -> bool:
	var contorno := maxf(tamanho / 5.0, 3.0) * 2.0
	for palavra in texto.replace("\n", " ").split(" ", false):
		if fonte.get_string_size(palavra, HORIZONTAL_ALIGNMENT_LEFT, -1, tamanho).x + contorno > area.x:
			return false
	var bloco := fonte.get_multiline_string_size(texto, HORIZONTAL_ALIGNMENT_CENTER, area.x - contorno, tamanho, -1,
		TextServer.BREAK_MANDATORY | TextServer.BREAK_WORD_BOUND)
	# folga de 12% para o espaçamento entre linhas do Label
	return bloco.y * 1.12 + contorno <= area.y


# ---------------------------------------------------------------------------
# Desenho por código (com SubViewport: desenha uma vez e guarda como imagem)
# ---------------------------------------------------------------------------

func _tamanho(proporcao: float) -> Vector2i:
	return Vector2i(RESOLUCAO, int(RESOLUCAO / proporcao)) if proporcao >= 1.0 else Vector2i(int(RESOLUCAO * proporcao), RESOLUCAO)


func _novo_visor(tamanho: Vector2i, transparente: bool) -> SubViewport:
	var v := SubViewport.new()
	v.size = tamanho
	v.transparent_bg = transparente
	v.render_target_update_mode = SubViewport.UPDATE_ONCE
	v.disable_3d = true
	add_child(v)
	return v


func _rotulo(d: Dictionary, t: Vector2i) -> Label:
	var c: Array = d["caixa"]
	var area := Rect2(t.x * float(c[0]), t.y * float(c[1]), t.x * (float(c[2]) - float(c[0])), t.y * (float(c[3]) - float(c[1])))
	var fonte: Font = FONTES.get(d["fonte"], FONTES["titulo"])
	var texto := String(d["texto"])
	var maximo := int(area.size.y * 0.8)
	var tamanho := tamanho_que_cabe(texto, fonte, area.size, maxi(maximo, 12))
	var l := Label.new()
	l.text = texto
	l.add_theme_font_override("font", fonte)
	l.add_theme_font_size_override("font_size", tamanho)
	l.add_theme_color_override("font_color", d["cor"])
	if d.get("contorno", true):
		# contorno grosso: o texto continua legível em cima de fundo claro ou desenhado
		l.add_theme_color_override("font_outline_color", Color(0.08, 0.05, 0.04, 0.95))
		l.add_theme_constant_override("outline_size", maxi(tamanho / 5, 3))
	l.add_theme_constant_override("line_spacing", 0)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD  # só quebra entre palavras
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT if d.get("alinhar") == "esquerda" else HORIZONTAL_ALIGNMENT_CENTER
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	l.position = area.position
	l.size = area.size
	return l


func _capturar(v: SubViewport) -> Texture2D:
	var img: Image = null
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
		await RenderingServer.frame_post_draw
		img = v.get_texture().get_image()
	v.queue_free()
	if img == null or img.is_empty():
		# Sem tela (modo --headless dos testes): nada é desenhado; fica uma textura cinza de 4x4.
		img = Image.create(4, 4, false, Image.FORMAT_RGBA8)
		img.fill(Color(0.5, 0.5, 0.5))
	img.generate_mipmaps()
	return ImageTexture.create_from_image(img)


## Textos do jogo por cima da arte do Gemini (fundo transparente).
func _desenhar_textos(textos: Array[Dictionary], proporcao: float) -> Texture2D:
	var t := _tamanho(proporcao)
	var v := _novo_visor(t, true)
	for d in textos:
		# Texto escrito pelo jogo por cima de uma IMAGEM: faixa escura translúcida atrás, para ler
		# mesmo sobre partes claras da arte (o envelhecimento do shader ainda clareia tudo um pouco).
		if bool(d.get("contorno", false)) and not d.has("sem_faixa"):
			var c: Array = d["caixa"]
			var faixa := ColorRect.new()
			faixa.color = Color(0.05, 0.03, 0.06, 0.42)
			faixa.position = Vector2(t.x * float(c[0]) - t.x * 0.02, t.y * float(c[1]))
			faixa.size = Vector2(t.x * (float(c[2]) - float(c[0])) + t.x * 0.04, t.y * (float(c[3]) - float(c[1])))
			v.add_child(faixa)
		v.add_child(_rotulo(d, t))
	return await _capturar(v)


## Versão feita por código quando não há imagem (ou para as artes que só existem no jogo).
func _desenhar_procedural(nome: String, proporcao: float) -> Texture2D:
	var t := _tamanho(proporcao)
	var v := _novo_visor(t, false)
	var info: Dictionary = PROCEDURAIS.get(nome, {})
	var fundo := ColorRect.new()
	fundo.size = Vector2(t)
	# Cor de fundo estável por nome (cada pôster sem arte ganha uma cor diferente).
	fundo.color = info.get("fundo", Color.from_hsv(float(hash(nome) % 360) / 360.0, 0.55, 0.6))
	v.add_child(fundo)
	if info.has("enfeite"):
		var desenho := Control.new()
		desenho.size = Vector2(t)
		var tipo := String(info["enfeite"])
		var cor_fundo: Color = fundo.color
		desenho.draw.connect(func() -> void: Enfeites.desenhar(desenho, tipo, Vector2(t), cor_fundo, hash(nome)))
		v.add_child(desenho)
	for d in textos_da_arte(nome, false):
		v.add_child(_rotulo(d, t))
	return await _capturar(v)
