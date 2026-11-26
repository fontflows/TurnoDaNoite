extends Node
## FERRAMENTA DE DESENVOLVIMENTO — não entra no build.
## VALIDADOR DAS ARTES E TEXTOS DO MAPA (AJUSTES V2.2 §3.1 a §3.3).
## Lista TODOS os planos Arte__<nome> e todos os textos 3D vindos do Blender e confere, um por um:
##   1. definição: a arte está no manifesto ou em ArteExterna.PROCEDURAIS (senão vira um cartaz
##      liso com o nome do arquivo — foi o que aconteceu com os cartazes das salas de festa);
##   2. material: a arte recebeu o material com a imagem; o texto 3D tem material;
##   3. tamanho maior que zero;
##   4. normal (a frente) virada para o lado de onde o jogador olha: nada colado na frente e
##      sem parede logo à frente;
##   5. não enterrada: a parede/moldura de trás fica a mais de 5 mm (artes) ou 2 mm (letras);
##   6. textos: cada letra existe na fonte usada (acentos!) e o texto escrito pelo jogo cabe
##      na área sem quebrar palavras; texto 3D não passa da placa onde está.
## Grava docs/progresso/relatorio_artes.txt.
## Rodar: godot --headless --path godot res://dev/validar_artes.tscn

const UTIL := preload("res://dev/artes_util.gd")
const CENA := "res://cenas/mundo_v2.tscn"
## Distância mínima até a superfície de trás (abaixo disso: z-fighting ou peça enterrada).
const MIN_ARTE := 0.005
const MIN_TEXTO := 0.002
## Espaço livre exigido na frente da peça (abaixo disso, a normal está virada para algo).
const LIVRE_FRENTE := 0.04
## Menor letra aceitável no texto desenhado pelo jogo (pixels, numa imagem de 768 px).
const LETRA_MINIMA := 14

var _linhas: Array[String] = []
var _erros := 0
var _avisos := 0
var _malhas: Array = []
var _cache := {}
var _fontes := {}  # nome do arquivo .ttf -> FontFile


func _ready() -> void:
	var t := Time.get_datetime_dict_from_system()
	Jogo.modo_captura = true
	_carregar_fontes()
	var mundo: Node3D = load(CENA).instantiate()
	add_child(mundo)
	var cenario := mundo.get_node("Navegacao/Cenario")
	var pecas := UTIL.listar(cenario)
	await _esperar_artes(pecas)
	_malhas = mundo.find_children("*", "MeshInstance3D", true, false)
	var arte := mundo.get_node("Montador").get("_arte") as ArteExterna
	_linhas.append("RELATÓRIO DAS ARTES E TEXTOS 3D — Turno da Noite (mapa V2)")
	_linhas.append("Gerado em %02d/%02d/%04d %02d:%02d por godot/dev/validar_artes.tscn" % [t.day, t.month, t.year, t.hour, t.minute])
	_linhas.append("Critérios: definição (manifesto/procedural), material, tamanho > 0, frente livre (%d cm), " % int(LIVRE_FRENTE * 100)
		+ "afastamento da superfície de trás > %d mm (letras > %d mm), letras existem na fonte, texto cabe sem quebrar palavra." % [
		int(MIN_ARTE * 1000), int(MIN_TEXTO * 1000)])
	_linhas.append("")
	var n_artes := 0
	var n_textos := 0
	_linhas.append("== ARTES (planos Arte__) ==")
	for p in pecas:
		if p["tipo"] == "arte":
			n_artes += 1
			_validar_arte(p, arte)
	_linhas.append("")
	_linhas.append("== TEXTOS 3D (letras modeladas no Blender) ==")
	for p in pecas:
		if p["tipo"] == "texto":
			n_textos += 1
			_validar_texto(p)
	_linhas.append("")
	_linhas.append("RESULTADO: %d artes e %d textos 3D conferidos — %s" % [n_artes, n_textos,
		"SEM ERROS" if _erros == 0 else "%d ERRO(S)" % _erros] + (" (%d aviso(s))" % _avisos if _avisos else ""))
	var caminho := ProjectSettings.globalize_path("res://").path_join("../docs/progresso/relatorio_artes.txt").simplify_path()
	var arq := FileAccess.open(caminho, FileAccess.WRITE)
	arq.store_string("\n".join(_linhas) + "\n")
	arq.close()
	print("\n".join(_linhas))
	get_tree().quit(1 if _erros else 0)


func _esperar_artes(pecas: Array[Dictionary]) -> void:
	for i in 400:
		var faltam := 0
		for p in pecas:
			if p["tipo"] == "arte":
				var m := (p["no"] as MeshInstance3D).material_override as ShaderMaterial
				if m == null or m.get_shader_parameter("arte") == null:
					faltam += 1
		if faltam == 0:
			return
		await get_tree().process_frame


func _carregar_fontes() -> void:
	for pasta in DirAccess.get_directories_at("res://assets/fontes"):
		for arq in DirAccess.get_files_at("res://assets/fontes".path_join(pasta)):
			if arq.get_extension() == "ttf":
				_fontes[arq] = load("res://assets/fontes".path_join(pasta).path_join(arq))


# ---------------------------------------------------------------------------

func _validar_arte(p: Dictionary, arte: ArteExterna) -> void:
	var m := p["no"] as MeshInstance3D
	var nome := arte.nome_da_arte(String(m.name))
	var g := UTIL.geometria(m)
	var problemas: Array[String] = []
	var avisos: Array[String] = []
	var caminho := arte.caminho_imagem(nome)
	var origem := ("imagem " + caminho.get_file()) if caminho != "" else "desenho por código"
	if not arte.definida(nome):
		problemas.append("SEM DEFINIÇÃO no manifesto nem em PROCEDURAIS: aparece só um cartaz liso com o nome do arquivo")
	var mat := m.material_override as ShaderMaterial
	if mat == null or mat.get_shader_parameter("arte") == null:
		problemas.append("material/imagem não aplicado")
	_tamanho_ok(g, problemas)
	_frente_e_fundo(m, g, MIN_ARTE, problemas, avisos)
	# Textos que o jogo escreve por cima: cabem sem quebrar palavra? letras existem?
	var prop := maxf(float(g["largura"]), 0.01) / maxf(float(g["altura"]), 0.01)
	var px: Vector2i = arte._tamanho(prop)
	for d in arte.textos_da_arte(nome, caminho != ""):
		var c: Array = d["caixa"]
		var area := Vector2(px.x * (float(c[2]) - float(c[0])), px.y * (float(c[3]) - float(c[1])))
		var fonte: Font = ArteExterna.FONTES.get(d["fonte"], ArteExterna.FONTES["titulo"])
		var texto := String(d["texto"])
		var tam := ArteExterna.tamanho_que_cabe(texto, fonte, area, maxi(int(area.y * 0.8), 12))
		if not ArteExterna.cabe(texto, fonte, area, tam):
			problemas.append("texto \"%s\" não cabe na área nem com letra mínima" % texto.replace("\n", " / "))
		elif tam < LETRA_MINIMA:
			avisos.append("texto \"%s\" ficou pequeno (%d px)" % [texto.replace("\n", " / ").left(40), tam])
		var faltam := _letras_faltando(texto, fonte)
		if faltam != "":
			problemas.append("letras sem glifo na fonte: " + faltam)
	_registrar(String(m.name), "%s · %.2f x %.2f m · %s · %s" % [origem, g["largura"], g["altura"],
		_comodo(g), _resumo_distancias(g)], problemas, avisos)


func _validar_texto(p: Dictionary) -> void:
	var m := p["no"] as MeshInstance3D
	var g := UTIL.geometria(m)
	var problemas: Array[String] = []
	var avisos: Array[String] = []
	if m.mesh == null or m.get_active_material(0) == null:
		problemas.append("sem material")
	_tamanho_ok(g, problemas)
	_frente_e_fundo(m, g, MIN_TEXTO, problemas, avisos)
	var corpo := String(p["texto"])
	var arq_fonte := ""
	var extras: Variant = m.get_meta("extras", {})
	if extras is Dictionary:
		arq_fonte = String((extras as Dictionary).get("texto_fonte", ""))
	var fonte: Font = _fontes.get(arq_fonte)
	if fonte == null:
		avisos.append("fonte desconhecida (%s)" % arq_fonte)
	else:
		var faltam := _letras_faltando(corpo, fonte)
		if faltam != "":
			problemas.append("letras sem glifo na fonte %s: %s" % [arq_fonte, faltam])
	_dentro_da_placa(m, g, problemas, avisos)
	_registrar(String(m.name), "\"%s\" · %s · %.2f x %.2f m · %s" % [corpo.replace("\n", " / "), arq_fonte,
		g["largura"], g["altura"], _resumo_distancias(g)], problemas, avisos)


# ---------------------------------------------------------------------------

func _tamanho_ok(g: Dictionary, problemas: Array[String]) -> void:
	if float(g["largura"]) < 0.005 or float(g["altura"]) < 0.005:
		problemas.append("tamanho zero (%.3f x %.3f m)" % [g["largura"], g["altura"]])


## Raios ao longo da normal, em 5 pontos da peça (centro e 4 pontos a 1/4 das bordas):
## - para a FRENTE (a partir de 2 mm): a primeira superfície tem que estar a mais de LIVRE_FRENTE;
## - de TRÁS para a frente: a superfície de trás mais próxima tem que estar a mais de 'minimo'.
func _frente_e_fundo(m: MeshInstance3D, g: Dictionary, minimo: float, problemas: Array[String], avisos: Array[String]) -> void:
	var c: Vector3 = g["centro"]
	var n: Vector3 = g["normal"]
	var dir: Vector3 = g["direita"]
	var cima: Vector3 = g["cima"]
	var w := float(g["largura"])
	var h := float(g["altura"])
	var caixa := AABB(c, Vector3.ZERO)
	for sx in [-0.5, 0.5]:
		for sy in [-0.5, 0.5]:
			caixa = caixa.expand(c + dir * w * sx + cima * h * sy)
	caixa = caixa.grow(0.02).merge(AABB(c - n * 0.32, Vector3.ZERO)).merge(AABB(c + n * 0.32, Vector3.ZERO)).grow(0.05)
	var tri := UTIL.triangulos_perto(_malhas, caixa, m, _cache)
	var amostras := [c]
	for sx in [-0.25, 0.25]:
		for sy in [-0.25, 0.25]:
			amostras.append(c + dir * w * sx + cima * h * sy)
	var menor_tras := INF
	var colados := 0
	var bloqueados := 0
	var menor_frente := INF
	for a: Vector3 in amostras:
		# para a frente
		var f := UTIL.raio(tri, a + n * 0.002, n, 0.3)
		menor_frente = minf(menor_frente, f + 0.002)
		if f + 0.002 < LIVRE_FRENTE:
			bloqueados += 1
		# de trás para a frente (de 0,3 m atrás até a peça): a primeira superfície atrás
		var t := UTIL.raio(tri, a + n * 0.3, -n, 0.6)
		if t < INF:
			var atras := t - 0.3  # > 0: atrás da peça; < 0: na frente dela
			menor_tras = minf(menor_tras, atras)
			if atras < minimo - 0.0002 and atras > -LIVRE_FRENTE:  # (0,2 mm de tolerância de arredondamento)
				colados += 1
	g["frente"] = menor_frente
	g["tras"] = menor_tras
	if bloqueados >= 2:
		problemas.append("frente bloqueada a %.1f cm (normal virada para a parede ou algo colado na frente)" % (menor_frente * 100.0))
	elif bloqueados == 1:
		avisos.append("um canto tem algo a %.1f cm na frente" % (menor_frente * 100.0))
	if colados >= 2:
		problemas.append("enterrada/colada: superfície a %.1f mm (z-fighting)" % (menor_tras * 1000.0))
	elif colados == 1:
		avisos.append("um ponto encosta numa superfície a %.1f mm" % (menor_tras * 1000.0))
	elif minimo == MIN_ARTE and menor_tras > 0.015 and menor_tras < 0.1:
		avisos.append("solta: %.1f cm entre a arte e a superfície de trás" % (menor_tras * 100.0))


## Texto 3D preso numa placa/letreiro: o desenho das letras não pode passar da borda da placa.
func _dentro_da_placa(m: MeshInstance3D, g: Dictionary, problemas: Array[String], avisos: Array[String]) -> void:
	var pai := m.get_parent() as MeshInstance3D
	if pai == null or pai.mesh == null:
		return
	var nome_pai := String(pai.name)
	var e_placa := nome_pai.contains("Placa") or nome_pai.contains("Letreiro") or nome_pai.contains("Aviso") \
		or nome_pai.contains("Cartao") or nome_pai.contains("Faixa")
	if not e_placa:
		return
	var gp := UTIL.geometria(pai)
	var c: Vector3 = g["centro"]
	var dir: Vector3 = g["direita"]
	var cima: Vector3 = g["cima"]
	var mn := Vector2(INF, INF)
	var mx := -mn
	for v in pai.mesh.get_faces():
		var d := pai.global_transform * v - c
		var l := Vector2(d.dot(dir), d.dot(cima))
		mn = mn.min(l)
		mx = mx.max(l)
	var meio := Vector2(float(g["largura"]), float(g["altura"])) / 2.0
	var folga := 0.003
	if -meio.x < mn.x - folga or meio.x > mx.x + folga or -meio.y < mn.y - folga or meio.y > mx.y + folga:
		var msg := "texto passa da borda de %s (texto %.2f x %.2f m, placa %.2f x %.2f m)" % [nome_pai, g["largura"], g["altura"],
			mx.x - mn.x, mx.y - mn.y]
		if float(gp["espessura"]) < 0.1:
			problemas.append(msg)
		else:
			avisos.append(msg)


func _letras_faltando(texto: String, fonte: Font) -> String:
	var faltam := ""
	for i in texto.length():
		var ch := texto.unicode_at(i)
		if ch <= 32 or ch == 10:
			continue
		if not fonte.has_char(ch) and not faltam.contains(char(ch)):
			faltam += char(ch)
	return faltam


func _comodo(g: Dictionary) -> String:
	var frente: Vector3 = g["centro"] + g["normal"] * 0.4
	var c := PlantaV2.comodo_em(frente)
	var n: Vector3 = g["normal"]
	var lado: String = "virada para " + ("cima" if n.y > 0.7 else ("baixo" if n.y < -0.7 else
		["leste", "sul", "oeste", "norte"][wrapi(int(round(atan2(n.z, n.x) / (PI / 2.0))), 0, 4)]))
	return "%s, %s" % [c if c != "" else "fora da planta", lado]


func _resumo_distancias(g: Dictionary) -> String:
	var tras := float(g.get("tras", INF))
	var frente := float(g.get("frente", INF))
	return "atrás: %s · frente livre: %s" % ["nada (solta)" if tras == INF else "%.1f mm" % (tras * 1000.0),
		"> 30 cm" if frente >= 0.3 else "%.1f cm" % (frente * 100.0)]


func _registrar(nome: String, detalhe: String, problemas: Array[String], avisos: Array[String]) -> void:
	_erros += 1 if not problemas.is_empty() else 0
	_avisos += avisos.size()
	var marca := "[ERRO] " if not problemas.is_empty() else ("[aviso]" if not avisos.is_empty() else "[ok]   ")
	_linhas.append("  %s %s — %s" % [marca, nome, detalhe])
	for pr in problemas:
		_linhas.append("           ERRO: " + pr)
	for av in avisos:
		_linhas.append("           aviso: " + av)
