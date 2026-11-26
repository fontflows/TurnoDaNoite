extends Node
## FERRAMENTA DE DESENVOLVIMENTO: estima quanto tempo leva o CAMINHO CRÍTICO (partida ideal, sem mortes).
## Mede o comprimento real de cada trecho pela navegação e soma o tempo dos minigames e interações.
## Grava docs/progresso/relatorio_tempo.txt. Rodar: godot --headless --path godot res://dev/estimar_tempo.tscn

## Velocidade média andando/correndo de quem joga com atenção (m/s).
const VELOCIDADE := 3.2
## Quem joga pela primeira vez anda, para, olha, volta: multiplica o tempo de deslocamento.
const FATOR_PRIMEIRA_VEZ := 1.8

## [nome do passo, alvo (nó ou ponto da planta), segundos parado fazendo a ação]
var _passos := [
	["Sala de segurança → disjuntor da cozinha (fios)", "Disjuntores/Disjuntor_Cozinha", 12.0],
	["→ máquina de garra (chave)", "Maquina_Garra", 25.0],
	["→ sala do gerente: fusível + bilhete", "Disjuntores/Disjuntor_Gerente", 18.0],
	["→ TITO KART (recorde)", "Arcade_Tito_Kart", 60.0],
	["→ duto da sala dos piratas (rastejar)", "Duto_Entrada_Festa_Piratas", 6.0],
	["(sai na oficina) → alicate", "Item__alicate", 3.0],
	["→ porta de mão única → corrente do depósito + disjuntor", "Disjuntores/Disjuntor_Deposito", 6.0],
	["→ teclado da sala elétrica", "Teclado_Eletrica", 8.0],
	["→ disjuntor da sala elétrica", "Disjuntores/Disjuntor_Eletrica", 3.0],
	["→ gerador principal", "Gerador_Principal", 3.0],
	["→ CORRE para a sala de segurança e fecha a porta", "spawn", 3.0],
]


func _ready() -> void:
	Jogo.modo_captura = true
	var mundo: Node3D = load("res://cenas/mundo_v2.tscn").instantiate()
	add_child(mundo)
	for i in 10:
		await get_tree().physics_frame
	for porta in get_tree().get_nodes_in_group("porta"):
		porta.abrir_para_teste()
	for i in 5:
		await get_tree().physics_frame
	mundo.get_node("Navegacao").bake_navigation_mesh(false)
	for i in 5:
		await get_tree().physics_frame
	var mapa: RID = mundo.get_node("Navegacao").get_navigation_map()
	var prog: ProgressaoV2 = mundo.get_node("Montador/ProgressaoV2")
	var spawn: Vector3 = mundo.get_node("Marcadores/SpawnJogador").global_position
	var atual := spawn
	var linhas: Array[String] = ["TEMPO DO CAMINHO CRÍTICO (estimativa, sem mortes)", ""]
	var total_metros := 0.0
	var total_acoes := 0.0
	for p in _passos:
		var alvo: Vector3
		if p[1] == "spawn":
			alvo = spawn
		elif p[1] == "Duto_Entrada_Festa_Piratas":
			alvo = prog.get_node(p[1]).global_position
		else:
			var no := mundo.get_node_or_null(p[1]) as Node3D
			if no == null:
				no = mundo.find_child(p[1], true, false) as Node3D
			alvo = no.global_position
		var de := NavigationServer3D.map_get_closest_point(mapa, atual)
		var ate := NavigationServer3D.map_get_closest_point(mapa, alvo)
		var caminho := NavigationServer3D.map_get_path(mapa, de, ate, true)
		var metros := 0.0
		for i in range(1, caminho.size()):
			metros += caminho[i - 1].distance_to(caminho[i])
		if p[1] == "Duto_Entrada_Festa_Piratas":
			# Depois do duto o vigia aparece na oficina.
			alvo = PlantaV2.mundo(11.0, 15.2)
		total_metros += metros
		total_acoes += float(p[2])
		linhas.append("  %-58s %5.1f m  +%4.0f s" % [p[0], metros, p[2]])
		atual = alvo
	var desloc := total_metros / VELOCIDADE
	linhas.append("")
	linhas.append("Distância total: %.0f m  ·  deslocamento: %.1f min  ·  ações e minigames: %.1f min" % [total_metros, desloc / 60.0, total_acoes / 60.0])
	var ideal := (desloc + total_acoes) / 60.0
	var primeira := (desloc * FATOR_PRIMEIRA_VEZ + total_acoes * 1.3) / 60.0
	linhas.append("Jogador que já sabe o caminho: ~%.1f min  ·  primeira vez (anda, procura, se esconde): ~%.1f min" % [ideal, primeira])
	linhas.append("")
	for nome in ["facil", "normal", "pesadelo"]:
		var d: Dificuldade = load("res://assets/dificuldade/%s.tres" % nome)
		var noite := d.segundos_por_hora * 6.0 / 60.0
		linhas.append("  %-9s noite de %4.1f min  ·  folga sobre a 1ª vez: %+.1f min" % [d.nome, noite, noite - primeira])
	var arq := FileAccess.open(ProjectSettings.globalize_path("res://").path_join("../docs/progresso/relatorio_tempo.txt"), FileAccess.WRITE)
	arq.store_string("\n".join(linhas) + "\n")
	arq.close()
	print("\n".join(linhas))
	get_tree().quit()
