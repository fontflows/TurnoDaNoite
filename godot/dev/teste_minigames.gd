extends Node
## FERRAMENTA DE DESENVOLVIMENTO: confere o contrato dos minigames (docs/CONTRATOS.md, V2-9).
## Para cada cena que existir: abre, deixa rodar 1 s, confere vencer_agora() e cancelar().
## Rodar: godot --headless --path godot res://dev/teste_minigames.tscn

const CASOS := [
	# [cena, dados, chave que o resultado precisa ter ao vencer, valor esperado (ou null)]
	["res://cenas/minigames/garra.tscn", {}, "premio", "chave_gerente"],
	["res://cenas/minigames/kart.tscn", {"codigo": "4712"}, "digitos", "47"],
	["res://cenas/minigames/space_pizza.tscn", {"codigo": "4712"}, "digitos", "47"],
	["res://cenas/minigames/conserto.tscn", {"modo": "fios"}, "", null],
	["res://cenas/minigames/conserto.tscn", {"modo": "fusivel"}, "", null],
]

var _falhas := 0
var _ultimo: Array = []


func _ready() -> void:
	var camada := CanvasLayer.new()
	camada.layer = 20
	add_child(camada)
	for caso in CASOS:
		if not ResourceLoader.exists(caso[0]):
			print("[teste] (ainda não existe) ", caso[0])
			continue
		for nome_dif in ["facil", "normal", "pesadelo"]:
			var dif: Dificuldade = load("res://assets/dificuldade/%s.tres" % nome_dif)
			for modo in ["vencer", "cancelar"]:
				var m: Minigame = load(caso[0]).instantiate()
				camada.add_child(m)
				_ultimo = []
				m.terminado.connect(func(v: bool, r: Dictionary) -> void: _ultimo = [v, r])
				m.iniciar(dif, caso[1])
				for i in 60:
					await get_tree().process_frame
				if _ultimo.size() > 0:
					_falhar("%s (%s): terminou sozinho em 1 s sem ninguém jogar" % [caso[0], nome_dif])
					continue
				if modo == "vencer":
					m.vencer_agora()
				else:
					m.cancelar()
				await get_tree().process_frame
				await get_tree().process_frame
				var rotulo := "%s %s %s %s" % [caso[0].get_file(), caso[1], nome_dif, modo]
				if _ultimo.is_empty():
					_falhar(rotulo + ": não emitiu terminado")
				elif modo == "vencer" and (not _ultimo[0] or (caso[2] != "" and _ultimo[1].get(caso[2]) != caso[3])):
					_falhar(rotulo + ": resultado errado " + str(_ultimo))
				elif modo == "cancelar" and (_ultimo[0] or not _ultimo[1].get("cancelado", false)):
					_falhar(rotulo + ": cancelar deveria dar venceu=false e cancelado=true " + str(_ultimo))
				elif is_instance_valid(m) and not m.is_queued_for_deletion():
					_falhar(rotulo + ": não se apagou depois de terminar")
				else:
					print("[teste] ok    ", rotulo)
	# Venceu e apertou E (ou ESC) durante a mensagem final: a vitória tem que valer.
	for caso in [["res://cenas/minigames/conserto.tscn", {"modo": "fusivel"}], ["res://cenas/minigames/conserto.tscn", {"modo": "fios"}]]:
		var m: Minigame = load(caso[0]).instantiate()
		camada.add_child(m)
		_ultimo = []
		m.terminado.connect(func(v: bool, r: Dictionary) -> void: _ultimo = [v, r])
		m.iniciar(load("res://assets/dificuldade/normal.tres"), caso[1])
		await get_tree().process_frame
		m._concluir("teste")
		m.cancelar()
		await get_tree().process_frame
		if _ultimo.is_empty() or not _ultimo[0]:
			_falhar("conserto %s: venceu e apertou E na mensagem final, mas a vitória foi perdida %s" % [caso[1], _ultimo])
		else:
			print("[teste] ok    conserto %s: E na mensagem final mantém a vitória" % caso[1])
	print("[teste] %d falha(s)" % _falhas)
	get_tree().quit(1 if _falhas > 0 else 0)


func _falhar(texto: String) -> void:
	_falhas += 1
	print("[teste] FALHA ", texto)
