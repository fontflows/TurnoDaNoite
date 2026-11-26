"""
exportar_para_godot.py — reexporta para o Godot o arquivo .blend que está ABERTO,
mantendo as mudanças feitas à mão (cor, posição...). Não regenera nada.

Use quando editar um .blend direto no Blender (por exemplo, mudar a cor da cortina):
  Dentro do Blender: aba "Scripting" > Open (abrir este arquivo) > Run Script (Alt+P)
  Ou pelo terminal, a partir da pasta TurnoDaNoite:
      blender --background blender/moveis.blend --python blender/scripts/exportar_para_godot.py

O que ele exporta, conforme o arquivo aberto:
  predio.blend                  -> godot/assets/cenario/predio.glb
  moveis.blend                  -> godot/assets/cenario/moveis.glb e disjuntores.glb
  personagens_placeholder.blend -> godot/assets/personagens/tito.glb e pipoca.glb

ATENÇÃO: o gerar_tudo.py recria os .blend a partir dos scripts e APAGA mudanças
feitas à mão. Para uma mudança de cor ficar para sempre, mude também em comum.py (CORES).
"""

import pathlib
import sys

import bpy

# O .blend aberto fica em TurnoDaNoite/blender/; os scripts ficam em blender/scripts/.
# (Calculamos pelo .blend porque, dentro do Blender, __file__ nem sempre é o caminho real.)
PASTA_SCRIPTS = pathlib.Path(bpy.data.filepath).resolve().parent / "scripts"
sys.path.insert(0, str(PASTA_SCRIPTS))

import comum  # noqa: E402


def exportar():
    nome = pathlib.Path(bpy.data.filepath).name
    if nome == "predio.blend":
        comum.exportar_glb(comum.PASTA_CENARIO / "predio.glb")
    elif nome == "moveis.blend":
        import gerar_moveis
        disjuntores = list(bpy.data.collections["Disjuntores"].all_objects)
        nomes_disj = {o.name for o in disjuntores}
        moveis = [o for o in bpy.context.scene.objects if o.name not in nomes_disj]
        comodos = {c.name for c in bpy.context.scene.collection.children if c.name != "Disjuntores"}
        gerar_moveis.exportar_so(comum.PASTA_CENARIO / "moveis.glb", moveis, comodos)
        gerar_moveis.exportar_so(comum.PASTA_CENARIO / "disjuntores.glb", disjuntores, {"Disjuntores"})
    elif nome == "personagens_placeholder.blend":
        import gerar_placeholders
        gerar_placeholders.exportar_personagem(comum.PASTA_PERSONAGENS / "tito.glb", bpy.data.objects["Tito"])
        gerar_placeholders.exportar_personagem(comum.PASTA_PERSONAGENS / "pipoca.glb", bpy.data.objects["Pipoca"])
    else:
        raise RuntimeError(f"Não sei exportar '{nome}'. Abra predio.blend, moveis.blend ou personagens_placeholder.blend.")
    print(f"[exportar_para_godot] {nome} exportado. Volte para o Godot: ele reimporta sozinho.")


exportar()
