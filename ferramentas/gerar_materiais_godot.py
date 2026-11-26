"""
gerar_materiais_godot.py — cria os materiais do Godot como arquivos .tres editáveis
e diz ao Godot para usá-los no lugar dos materiais que vêm dentro dos .glb.

Por que: quando o .glb é reexportado do Blender, o Godot reimporta tudo. Se os materiais
ficassem dentro do .glb, uma cor mudada no Inspetor se perderia. Com os materiais em
godot/assets/materiais/*.tres, a mudança fica guardada para sempre.

Uso (na pasta TurnoDaNoite, com o Python normal; não precisa de nada instalado):
    python ferramentas/gerar_materiais_godot.py            -> cria só os .tres que faltam
    python ferramentas/gerar_materiais_godot.py --forcar   -> recria todos (APAGA edições feitas no Godot)
Depois, abra o Godot (ou rode o import) para ele reimportar os .glb.
"""

import ast
import json
import struct
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SCRIPTS_BLENDER = RAIZ / "blender" / "scripts"
GODOT = RAIZ / "godot"
PASTA_MATERIAIS = GODOT / "assets" / "materiais"
PASTA_TEXTURAS = GODOT / "assets" / "texturas"
GLBS = sorted({str(p.relative_to(GODOT).as_posix()) for p in (GODOT / "assets").rglob("*.glb")}) or [  # todos os .glb do projeto
        "assets/cenario/predio.glb"]

sys.path.insert(0, str(SCRIPTS_BLENDER))
import materiais_v2  # noqa: E402


def ler_todas_as_cores():
    """Junta todos os dicionários CORES* de todos os scripts do Blender (cada gerador pode ter o seu)."""
    cores = {}
    for arquivo in sorted(SCRIPTS_BLENDER.glob("*.py")):
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
        for no in arvore.body:
            if isinstance(no, ast.Assign):
                for alvo in no.targets:
                    if getattr(alvo, "id", "").startswith("CORES"):
                        try:
                            cores.update(ast.literal_eval(no.value))
                        except ValueError:
                            pass
    return cores


def ler_dicionario(arquivo, nome):
    """Lê um dicionário de cores (ex.: CORES) direto do script do Blender, sem executar o Blender."""
    arvore = ast.parse((SCRIPTS_BLENDER / arquivo).read_text(encoding="utf-8"))
    for no in ast.walk(arvore):
        if isinstance(no, ast.Assign) and any(getattr(a, "id", None) == nome for a in no.targets):
            return ast.literal_eval(no.value)
    return {}


def hex_para_cor(hex_cor):
    h = hex_cor.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return f"Color({r:.4f}, {g:.4f}, {b:.4f}, 1)"


def materiais_do_glb(caminho):
    """Nomes dos materiais dentro de um .glb (lê o pedaço JSON do arquivo)."""
    dados = caminho.read_bytes()
    tamanho_json = struct.unpack_from("<I", dados, 12)[0]
    gltf = json.loads(dados[20:20 + tamanho_json])
    return [m.get("name", "") for m in gltf.get("materials", []) if m.get("name")]


def texto_material(nome, cores):
    """Conteúdo do .tres de um material."""
    externos, props = [], []

    def textura(arq):
        externos.append(arq)
        return f'ExtResource("{len(externos)}")'

    texturizado = materiais_v2.TEXTURIZADOS.get(nome)
    hex_cor, emissao = cores.get(nome, ("#b0b0b0", 0.0))
    if texturizado:
        pasta, _metros, tinta = texturizado
        base = PASTA_TEXTURAS / pasta / pasta
        cor = Path(f"{base}_cor.jpg")
        if cor.exists():
            props.append(f"albedo_color = {hex_para_cor(tinta)}")
            props.append(f"albedo_texture = {textura(cor)}")
            if Path(f"{base}_aspereza.jpg").exists():
                props.append(f"roughness_texture = {textura(Path(f'{base}_aspereza.jpg'))}")
            if Path(f"{base}_normal.jpg").exists():
                props.append("normal_enabled = true")
                props.append(f"normal_texture = {textura(Path(f'{base}_normal.jpg'))}")
            if Path(f"{base}_ao.jpg").exists():
                props.append("ao_enabled = true")
                props.append(f"ao_texture = {textura(Path(f'{base}_ao.jpg'))}")
        else:
            print(f"AVISO: {nome}: textura {cor.name} ainda não existe; ficou com a cor lisa da tinta")
            props.append(f"albedo_color = {hex_para_cor(tinta)}")
    else:
        props.append(f"albedo_color = {hex_para_cor(hex_cor)}")
        props.append("roughness = 0.8")
    if emissao and emissao > 0:
        props += ["emission_enabled = true", f"emission = {hex_para_cor(hex_cor)}",
                  f"emission_energy_multiplier = {emissao}"]

    linhas = [f'[gd_resource type="StandardMaterial3D" load_steps={len(externos) + 1} format=3]', ""]
    for i, arq in enumerate(externos, 1):
        rel = "res://" + arq.relative_to(GODOT).as_posix()
        linhas.append(f'[ext_resource type="Texture2D" path="{rel}" id="{i}"]')
    if externos:
        linhas.append("")
    linhas += ["[resource]", f'resource_name = "{nome}"'] + props
    return "\n".join(linhas) + "\n"


def configurar_import(glb, nomes):
    """Faz o .glb.import usar os .tres externos (o Godot lê isso ao reimportar)."""
    arq_import = GODOT / (glb + ".import")
    if not arq_import.exists():
        print(f"AVISO: {arq_import.name} não existe ainda (abra o Godot uma vez para importar o .glb)")
        return
    subrecursos = {"materials": {
        n: {"use_external/enabled": True, "use_external/path": f"res://assets/materiais/{n}.tres"} for n in nomes
    }}
    texto = arq_import.read_text(encoding="utf-8").splitlines()
    novo = [l for l in texto if not l.startswith("_subresources=")]
    i = novo.index("[params]") + 1
    novo.insert(i, "_subresources=" + json.dumps(subrecursos, ensure_ascii=False))
    arq_import.write_text("\n".join(novo) + "\n", encoding="utf-8")


def desatualizado(destino, nome):
    """
    O .tres existe mas ficou para trás: o material entrou em TEXTURIZADOS (ou mudou de textura)
    depois que o .tres foi criado com cor lisa. Esses são recriados mesmo sem --forcar.
    (Edições feitas à mão no Godot em materiais com cor lisa se perdem só nesse caso.)
    """
    dados = materiais_v2.TEXTURIZADOS.get(nome)
    if not dados:
        return False
    pasta = dados[0]
    if not (PASTA_TEXTURAS / pasta / f"{pasta}_cor.jpg").exists():
        return False
    return f"res://assets/texturas/{pasta}/{pasta}_cor.jpg" not in destino.read_text(encoding="utf-8")


def relatorio_materiais(uso):
    """
    Lista os materiais dos .glb do mapa V2 SEM textura e fora da lista LISOS (cor lisa de propósito).
    A meta é zero. Grava docs/progresso/relatorio_materiais.txt.
    """
    tex = sorted(n for n in uso if n in materiais_v2.TEXTURIZADOS)
    lisos = sorted(n for n in uso if n not in materiais_v2.TEXTURIZADOS and n in materiais_v2.LISOS)
    faltam = sorted(n for n in uso if n not in materiais_v2.TEXTURIZADOS and n not in materiais_v2.LISOS)
    linhas = ["RELATÓRIO DE MATERIAIS — mapa V2 (gerado por ferramentas/gerar_materiais_godot.py)", "",
              f"Com textura: {len(tex)} · Cor lisa de propósito: {len(lisos)} · SEM TEXTURA (a corrigir): {len(faltam)}", ""]
    linhas.append("== SEM TEXTURA (inclua em materiais_v2.TEXTURIZADOS ou, se for de propósito, em LISOS) ==")
    for n in faltam:
        linhas.append(f"  {n:34s} usado em: {', '.join(sorted(set(uso[n]))[:5])}")
    if not faltam:
        linhas.append("  (nenhum)")
    linhas += ["", "== COR LISA DE PROPÓSITO (motivo) =="]
    linhas += [f"  {n:34s} {materiais_v2.LISOS[n]}" for n in lisos]
    linhas += ["", "== COM TEXTURA (material -> textura) =="]
    linhas += [f"  {n:34s} {materiais_v2.TEXTURIZADOS[n][0]}" for n in tex]
    destino = RAIZ / "docs" / "progresso" / "relatorio_materiais.txt"
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"Sem textura: {len(faltam)} (relatório em {destino})")
    for n in faltam:
        print("  SEM TEXTURA:", n)


def usos_do_mapa_v2():
    """{material: [objetos]} dos .glb do mapa V2."""
    uso = {}
    for glb in sorted((GODOT / "assets" / "cenario").glob("v2_*.glb")):
        dados = glb.read_bytes()
        tamanho_json = struct.unpack_from("<I", dados, 12)[0]
        gltf = json.loads(dados[20:20 + tamanho_json])
        mats = [m.get("name", "") for m in gltf.get("materials", [])]
        for no in gltf.get("nodes", []):
            if "mesh" not in no:
                continue
            for prim in gltf["meshes"][no["mesh"]]["primitives"]:
                if "material" in prim:
                    uso.setdefault(mats[prim["material"]], []).append(no.get("name", ""))
    return uso


def main():
    forcar = "--forcar" in sys.argv
    cores = ler_todas_as_cores()
    PASTA_MATERIAIS.mkdir(parents=True, exist_ok=True)
    criados = mantidos = atualizados = 0
    for glb in GLBS:
        caminho = GODOT / glb
        if not caminho.exists():
            continue
        nomes = materiais_do_glb(caminho)
        for nome in nomes:
            destino = PASTA_MATERIAIS / f"{nome}.tres"
            if destino.exists() and not forcar:
                if not desatualizado(destino, nome):
                    mantidos += 1
                    continue
                atualizados += 1
            else:
                criados += 1
            destino.write_text(texto_material(nome, cores), encoding="utf-8")
        configurar_import(glb, nomes)
    print(f"Materiais: {criados} criados/recriados, {atualizados} atualizados (ganharam textura), "
          f"{mantidos} mantidos (já existiam). Pasta: {PASTA_MATERIAIS}")
    relatorio_materiais(usos_do_mapa_v2())


if __name__ == "__main__":
    main()
