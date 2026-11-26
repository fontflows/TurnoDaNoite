"""
verificar_fontes.py — confere se as fontes do jogo têm TODAS as letras usadas nos textos
(acentos do português: á à â ã é ê í ó ô õ ú ç, maiúsculas e minúsculas, e símbolos).

Uso (na pasta TurnoDaNoite):
    python ferramentas/verificar_fontes.py

O que ele faz:
  1. junta todos os caracteres que aparecem entre aspas nos scripts, cenas e temas do Godot,
     no manifesto das artes e nos textos 3D dos scripts do Blender;
  2. para cada fonte de godot/assets/fontes/, lista os caracteres que ela NÃO tem
     e diz se a fonte reserva (campo "fallbacks" do .import) cobre cada um;
  3. grava docs/progresso/relatorio_fontes.txt.
Os textos 3D já exportados também são conferidos letra a letra pelo godot/dev/validar_artes.tscn.

Precisa da biblioteca fontTools (vem com o matplotlib; se faltar: o relatório avisa e para).
"""

import re
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
GODOT = RAIZ / "godot"
FONTES = GODOT / "assets" / "fontes"
RELATORIO = RAIZ / "docs" / "progresso" / "relatorio_fontes.txt"
# Letras que o português precisa (o pedido do playtest), conferidas sempre.
OBRIGATORIAS = "áàâãéêíóôõúçÁÀÂÃÉÊÍÓÔÕÚÇ"


def caracteres_usados():
    """{caractere: {arquivos}} de tudo o que está entre aspas (fora do ASCII simples)."""
    arquivos = []
    for padrao in ("**/*.gd", "**/*.tscn", "**/*.tres", "assets/**/*.json"):
        arquivos += [p for p in GODOT.glob(padrao) if ".godot" not in p.parts]
    arquivos += list((RAIZ / "blender" / "scripts").glob("moveis_v2_*.py"))
    usados = {}
    for arq in arquivos:
        texto = arq.read_text(encoding="utf-8", errors="ignore")
        for trecho in re.findall(r'"((?:[^"\n]|\\")*)"', texto):
            for c in trecho:
                if ord(c) > 126:
                    usados.setdefault(c, set()).add(arq.name)
    for c in OBRIGATORIAS:
        usados.setdefault(c, set()).add("(acentos do português)")
    return usados


def fallbacks_do_import(ttf):
    """Fontes reserva declaradas no .import (só os .ttf/.otf do projeto; SystemFont fica como 'sistema')."""
    imp = Path(str(ttf) + ".import")
    if not imp.exists():
        return [], False
    linha = next((l for l in imp.read_text(encoding="utf-8").splitlines() if l.startswith("fallbacks=")), "")
    caminhos = re.findall(r'"(res://[^"]+)"', linha)
    fontes = [GODOT / c.removeprefix("res://") for c in caminhos if c.endswith((".ttf", ".otf"))]
    sistema = any(c.endswith(".tres") for c in caminhos)
    return fontes, sistema


def main():
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        print("fontTools não encontrado: não dá para ler as fontes. (pip install fonttools)")
        return 1
    usados = caracteres_usados()
    cmaps = {f: set(TTFont(f).getBestCmap()) for f in sorted(FONTES.glob("*/*.ttf"))}
    linhas = ["RELATÓRIO DAS FONTES — Turno da Noite (ferramentas/verificar_fontes.py)",
              f"Gerado em {datetime.now():%d/%m/%Y %H:%M}", "",
              "Caracteres fora do ASCII usados nos textos do jogo: " + "".join(sorted(usados)), ""]
    sem_cobertura = 0
    for ttf, cmap in cmaps.items():
        reservas, sistema = fallbacks_do_import(ttf)
        faltam = [c for c in sorted(usados) if ord(c) not in cmap]
        acentos = [c for c in OBRIGATORIAS if ord(c) not in cmap]
        linhas.append(f"{ttf.parent.name}/{ttf.name}")
        linhas.append(f"  acentos do português: {'TODOS' if not acentos else 'FALTAM ' + ''.join(acentos)}")
        if not faltam:
            linhas.append("  todos os caracteres usados existem na fonte")
        for c in faltam:
            cobre = [r.name for r in reservas if r in cmaps and ord(c) in cmaps[r]]
            if cobre:
                onde = "coberto pela reserva " + cobre[0]
            elif sistema:
                onde = "coberto pela fonte do sistema (simbolos_sistema.tres)"
            else:
                onde = "SEM COBERTURA"
                sem_cobertura += 1
            linhas.append(f"  falta {c} (U+{ord(c):04X}): {onde}  — usado em {', '.join(sorted(usados[c]))[:80]}")
        linhas.append("")
    linhas.append("RESULTADO: " + ("todas as letras têm fonte (própria ou reserva)." if sem_cobertura == 0
                                   else f"{sem_cobertura} caractere(s) sem fonte nenhuma."))
    RELATORIO.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print("\n".join(linhas))
    print(f"\nRelatório salvo em {RELATORIO}")
    return 1 if sem_cobertura else 0


if __name__ == "__main__":
    sys.exit(main())
