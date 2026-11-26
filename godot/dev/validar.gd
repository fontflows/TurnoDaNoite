extends Node
## FERRAMENTA DE DESENVOLVIMENTO — não entra no build.
## Carrega todos os scripts e cenas do projeto (com os autoloads ativos) e mostra
## quais têm erro. Uso (na pasta godot/):
##   godot --headless --path . res://dev/validar.tscn
## Sai com código 0 se tudo estiver ok, ou 1 se algo falhar.

const PASTAS_IGNORADAS := [".godot", "dev"]


func _ready() -> void:
	var arquivos: Array[String] = []
	_listar("res://", arquivos)
	var falhas := 0
	for caminho in arquivos:
		var recurso := ResourceLoader.load(caminho, "", ResourceLoader.CACHE_MODE_IGNORE)
		var ok := recurso != null
		if ok and recurso is GDScript:
			ok = (recurso as GDScript).can_instantiate()
		elif ok and recurso is PackedScene:
			var instancia := (recurso as PackedScene).instantiate()
			ok = instancia != null
			if instancia:
				instancia.free()
		if not ok:
			falhas += 1
		print("[validar] ", "ok   " if ok else "ERRO ", caminho)
	print("[validar] %d arquivos, %d com erro" % [arquivos.size(), falhas])
	get_tree().quit(1 if falhas > 0 else 0)


func _listar(pasta: String, saida: Array[String]) -> void:
	for sub in DirAccess.get_directories_at(pasta):
		if sub in PASTAS_IGNORADAS:
			continue
		_listar(pasta.path_join(sub), saida)
	for arq in DirAccess.get_files_at(pasta):
		if arq.get_extension() in ["gd", "tscn"]:
			saida.append(pasta.path_join(arq))
