class_name PlantaV2
extends RefCounted
## Acesso rápido à planta do mapa da V2 (gerada pelo Blender em assets/dados/planta_v2.json).
## Godot: X = x − 30, Z = z − 22,5 (x e z são as coordenadas da planta, em metros).

const ARQUIVO := "res://assets/dados/planta_v2.json"

## Tipo de piso de cada cômodo (muda o som e o barulho dos passos).
const PISO := {
	"Salao": "carpete", "Fliperama": "carpete", "Festa_Estrelas": "carpete", "Festa_Piratas": "madeira",
	"Festa_Princesas": "carpete", "Cozinha": "azulejo", "Camara_Fria": "metal", "Banheiros": "azulejo",
	"Copa": "azulejo", "Oficina": "concreto", "Deposito": "concreto", "Sala_Eletrica": "concreto",
	"Sala_Gerente": "madeira", "Arquivo": "concreto", "Vestiario": "azulejo", "Sala_Seguranca": "azulejo",
	"Armario_Limpeza": "concreto", "Recepcao": "azulejo", "Corredor_Principal": "azulejo",
	"Corredor_Festas": "azulejo", "Corredor_Funcionarios": "concreto",
}

## Por tipo de piso: [multiplicador do raio do barulho, tom do som, volume extra em dB]
const SOM_PISO := {
	"carpete": [0.6, 0.85, -6.0],
	"madeira": [1.0, 0.8, 0.0],
	"azulejo": [1.2, 1.15, 1.0],
	"concreto": [0.9, 0.95, -1.0],
	"metal": [1.5, 1.35, 3.0],
}

static var _dados := {}


static func dados() -> Dictionary:
	if _dados.is_empty():
		_dados = JSON.parse_string(FileAccess.get_file_as_string(ARQUIVO))
	return _dados


## Nome do cômodo onde fica um ponto do mundo ("" se fora do prédio).
static func comodo_em(pos: Vector3) -> String:
	var x := pos.x + 30.0
	var z := pos.z + 22.5
	# Cômodos pequenos primeiro (a sala de segurança fica "dentro" do retângulo de outros na lista).
	var melhor := ""
	var menor_area := INF
	for c in dados()["comodos"]:
		if x >= c["x0"] and x <= c["x1"] and z >= c["z0"] and z <= c["z1"]:
			var area: float = (c["x1"] - c["x0"]) * (c["z1"] - c["z0"])
			if area < menor_area:
				menor_area = area
				melhor = c["nome"]
	return melhor


## Converte um ponto da planta (x, z, altura) para o mundo do Godot.
static func mundo(x: float, z: float, altura := 0.0) -> Vector3:
	return Vector3(x - 30.0, altura, z - 22.5)


static func piso_em(pos: Vector3) -> String:
	return PISO.get(comodo_em(pos), "azulejo")
