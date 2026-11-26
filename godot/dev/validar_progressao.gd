extends Node
## FERRAMENTA DE DESENVOLVIMENTO: VALIDADOR DE PROGRESSÃO (docs/CONTRATOS.md, V2-8).
## Para cada dificuldade:
##   1. confere que cada peça da cadeia existe no mapa (disjuntores, máquinas, pistas, portas...);
##   2. confere, pela navegação do começo da noite (portas destrancadas abrem), que dá para chegar
##      nas fichas e que há fichas suficientes para a garra e o kart (e a regra anti-travamento);
##   3. roda o teste da cadeia inteira (dev/teste_cadeia.tscn) num processo separado.
## Grava o resultado em docs/progresso/relatorio_progressao.txt.
## Rodar: godot --headless --path godot res://dev/validar_progressao.tscn

const RELATORIO := "res://../docs/progresso/relatorio_progressao.txt"
const NOMES := ["Fácil", "Normal", "Pesadelo"]
const OBRIGATORIOS := ["Maquina_Garra", "Arcade_Tito_Kart", "Pista__aniversario", "Pista__quadro_avisos",
	"Pista__recado_gerente", "Teclado_Eletrica", "Gerador_Principal", "Botao_Porta_Seguranca", "Item__alicate",
	"Secretaria_Eletronica"]
const PORTAS := ["deposito", "gerente", "eletrica", "oficina", "seguranca", "camara", "cozinha", "oficina_1", "deposito_2"]
const MINIGAMES := ["garra", "kart", "space_pizza", "conserto"]

var _linhas: Array[String] = []
var _problemas := 0


func _ok(cond: bool, texto: String) -> void:
	if not cond:
		_problemas += 1
	_linhas.append(("  [ok]    " if cond else "  [ERRO]  ") + texto)


func _ready() -> void:
	var t := Time.get_datetime_dict_from_system()
	_linhas.append("RELATÓRIO DE PROGRESSÃO — Turno da Noite (mapa V2)")
	_linhas.append("Gerado em %02d/%02d/%04d %02d:%02d" % [t.day, t.month, t.year, t.hour, t.minute])
	_linhas.append("")
	Jogo.trocar_cena_ao_terminar = false
	for nivel in 3:
		await _validar(nivel)
	# Itens visíveis, alcançáveis e fora de colisores (validador separado, se existir).
	if ResourceLoader.exists("res://dev/validar_itens.tscn"):
		var saida: Array = []
		var codigo := OS.execute(OS.get_executable_path(), ["--headless", "--path", ProjectSettings.globalize_path("res://"),
			"res://dev/validar_itens.tscn", "--quit-after", "20000"], saida, true)
		var linhas_itens := "
".join(saida).split("
")
		var resumo := ""
		for l in linhas_itens:
			if l.to_lower().contains("problema") or l.to_lower().contains("falha") or l.to_lower().contains("resumo"):
				resumo = l.strip_edges()
		_ok(codigo == 0, "itens coletáveis visíveis e alcançáveis (dev/validar_itens.tscn) %s" % resumo)
	_linhas.append("")
	_linhas.append("RESULTADO: %s" % ("SEM ERROS — a noite pode ser vencida nas 3 dificuldades." if _problemas == 0
		else "%d problema(s) — veja as linhas [ERRO]." % _problemas))
	var arquivo := FileAccess.open(ProjectSettings.globalize_path("res://").path_join("../docs/progresso/relatorio_progressao.txt"), FileAccess.WRITE)
	arquivo.store_string("\n".join(_linhas) + "\n")
	arquivo.close()
	print("\n".join(_linhas))
	Config.dificuldade = 1
	Jogo.trocar_cena_ao_terminar = true
	get_tree().quit(1 if _problemas else 0)


func _validar(nivel: int) -> void:
	Config.dificuldade = nivel
	Jogo.checkpoint = {}
	var mundo: Node3D = load("res://cenas/mundo_v2.tscn").instantiate()
	add_child(mundo)
	for i in 20:
		await get_tree().physics_frame
	var dif: Dificuldade = Jogo.dificuldade
	_linhas.append("== %s ==" % NOMES[nivel])
	# 1. Peças da cadeia
	var faltando: Array[String] = []
	for nome in OBRIGATORIOS:
		if mundo.find_child(nome, true, false) == null:
			faltando.append(nome)
	_ok(faltando.is_empty(), "peças da cadeia no mapa (%d/%d)%s" % [OBRIGATORIOS.size() - faltando.size(), OBRIGATORIOS.size(),
		"" if faltando.is_empty() else " — faltam: " + ", ".join(faltando)])
	var disj := mundo.get_node("Disjuntores").get_child_count()
	_ok(disj == 4, "4 disjuntores com lógica (%d)" % disj)
	var prog: ProgressaoV2 = mundo.get_node("Montador/ProgressaoV2")
	var portas_ok := PORTAS.filter(func(p: String) -> bool: return prog._portas.has(p))
	_ok(portas_ok.size() == PORTAS.size(), "portas especiais com lógica (%d/%d)" % [portas_ok.size(), PORTAS.size()])
	var mg := MINIGAMES.filter(func(m: String) -> bool: return ResourceLoader.exists("res://cenas/minigames/%s.tscn" % m))
	_ok(mg.size() == MINIGAMES.size(), "cenas dos minigames (%s)" % ", ".join(mg))
	_ok(Jogo.codigo.length() == 4 and Jogo.codigo[2] != "0", "senha sorteada válida (%s)" % Jogo.codigo)
	# 2. Fichas: quantas existem e quantas dá para alcançar no começo da noite
	var mapa: RID = mundo.get_node("Navegacao").get_navigation_map()
	var inicio := NavigationServer3D.map_get_closest_point(mapa, mundo.get_node("Jogador").global_position)
	var alcancaveis := 0
	var fichas := get_tree().get_nodes_in_group("ficha")
	for f in fichas:
		var alvo := NavigationServer3D.map_get_closest_point(mapa, (f as Node3D).global_position)
		var caminho := NavigationServer3D.map_get_path(mapa, inicio, alvo, true)
		if not caminho.is_empty() and caminho[caminho.size() - 1].distance_to(alvo) < 0.6:
			alcancaveis += 1
	_ok(fichas.size() == dif.fichas_no_mapa, "fichas no mapa = %d (dificuldade pede %d)" % [fichas.size(), dif.fichas_no_mapa])
	_ok(alcancaveis >= 2, "fichas alcançáveis no começo da noite: %d (precisa de pelo menos 2: garra + kart)" % alcancaveis)
	_ok(dif.reaparecer_ficha_s > 0.0, "anti-travamento: ficha reaparece a cada %.0f s se o vigia ficar sem nenhuma" % dif.reaparecer_ficha_s)
	# V2.2: cada passo do caminho crítico tem objetivo escrito e lugar no mapa.
	var alvos := ["disjuntor_cozinha", "maquina_garra", "disjuntor_gerente", "maquina_kart", "duto_piratas", "alicate",
		"disjuntor_deposito", "teclado_eletrica", "disjuntor_eletrica", "gerador", "botao_porta"]
	var sem_lugar := alvos.filter(func(a: String) -> bool: return prog.posicao_alvo(a) == null)
	_ok(sem_lugar.is_empty(), "passos do caminho crítico com lugar no mapa (%d/%d)%s" % [alvos.size() - sem_lugar.size(), alvos.size(),
		"" if sem_lugar.is_empty() else " — sem lugar: " + ", ".join(sem_lugar)])
	var objetivo := Jogo.objetivo_estruturado()
	_ok(String(objetivo["titulo"]) != "" and not objetivo["passos"].is_empty() and objetivo["alvo"] in alvos,
		"objetivo inicial escrito e com alvo (%s)" % objetivo["alvo"])
	var dados := prog.dados_mapa()
	var faltam_chaves := ["jogador", "visitados", "disjuntores", "portas", "objetivo", "marcacao", "diario", "itens", "fichas", "senha"].filter(
		func(k: String) -> bool: return not dados.has(k))
	_ok(faltam_chaves.is_empty(), "dados do mapa (M) completos%s" % ("" if faltam_chaves.is_empty() else " — faltam: " + ", ".join(faltam_chaves)))
	_ok(Jogo.fichas == dif.fichas_iniciais, "fichas no bolso no começo da noite: %d" % Jogo.fichas)
	var pilhas := mundo.get_node("Pilhas").get_child_count()
	_linhas.append("  [info]  pilhas no mapa: %d · bateria %.0f s · stamina %.1f s · garra força %.2f · checkpoint: %s" % [
		mini(pilhas, dif.pilhas_no_mapa), dif.duracao_bateria_s, dif.duracao_stamina_s, dif.forca_garra,
		"sim" if dif.checkpoint_por_disjuntor else "não"])
	mundo.queue_free()
	await get_tree().process_frame
	# 3. A cadeia inteira, jogada pelo teste automático (processo separado)
	var saida: Array = []
	var codigo := OS.execute(OS.get_executable_path(), ["--headless", "--path", ProjectSettings.globalize_path("res://"),
		"res://dev/teste_cadeia.tscn", "--quit-after", "40000", "--", "dificuldade=%d" % nivel], saida, true)
	var texto: String = "\n".join(saida)
	var falhas := texto.count("[cadeia] FALHA")
	# (só a parte em ASCII da linha "ok    VITÓRIA (06:00)": o acento pode chegar trocado pelo terminal)
	var venceu := texto.contains("(06:00)") and texto.contains("[cadeia] 0 falha(s)")
	_ok(codigo == 0 and falhas == 0 and venceu, "cadeia completa jogada do começo à vitória (%d falha(s)%s)" % [falhas,
		", vitória" if venceu else ", SEM vitória"])
	for l in texto.split("\n"):
		if l.contains("[cadeia] FALHA"):
			_linhas.append("          " + l.strip_edges())
	_linhas.append("")
