"""
gerar_tudo.py — regenera TODO o conteúdo do Blender e reexporta os .glb.

Rodar a partir da pasta TurnoDaNoite:
    blender --background --python blender/scripts/gerar_tudo.py

O que ele faz, em ordem:
  1. gerar_predio.py       -> blender/predio.blend + godot/assets/cenario/predio.glb
  2. gerar_moveis.py       -> blender/moveis.blend + moveis.glb + disjuntores.glb
  3. gerar_placeholders.py -> blender/personagens_placeholder.blend + tito.glb + pipoca.glb
  4. ferramentas/gerar_sons.py -> godot/assets/sons/*.wav

Depois é só abrir (ou voltar para) o Godot: ele percebe que os arquivos mudaram
e reimporta sozinho. A lógica do jogo fica em cenas separadas, então nada se perde.
"""

import pathlib
import runpy
import sys
import time

PASTA = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(PASTA))

import gerar_moveis  # noqa: E402
import gerar_placeholders  # noqa: E402
import gerar_predio  # noqa: E402

# Quando os modelos FINAIS do Tito e da Pipoca estiverem em godot/assets/personagens/,
# troque para False. Senão este script escreve os provisórios por cima deles!
GERAR_PERSONAGENS_PROVISORIOS = True


def main():
    inicio = time.time()
    etapas = [
        ("Prédio", gerar_predio.gerar),
        ("Móveis e disjuntores", gerar_moveis.gerar),
    ]
    if GERAR_PERSONAGENS_PROVISORIOS:
        etapas.append(("Personagens provisórios", gerar_placeholders.gerar))
    else:
        print("[gerar_tudo] pulando personagens provisórios (modelos finais em uso)")
    for nome, funcao in etapas:
        print(f"\n===== {nome} =====")
        funcao()

    print("\n===== Sons =====")
    script_sons = PASTA.parents[1] / "ferramentas" / "gerar_sons.py"
    runpy.run_path(str(script_sons), run_name="__main__")

    print(f"\n[gerar_tudo] pronto em {time.time() - inicio:.1f} s")


if __name__ == "__main__":
    main()
