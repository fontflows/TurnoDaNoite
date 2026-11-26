"""
verificar_arte.py — confere as artes externas (geradas no Gemini) que você colocou no projeto.

Uso (na pasta TurnoDaNoite):
    python ferramentas/verificar_arte.py             -> só mostra o relatório
    python ferramentas/verificar_arte.py --corrigir  -> também renomeia/move os arquivos com nome
                                                         quase certo (ex.: Poster_Celebre.JPG)

O que ele faz:
  - lê a lista oficial em godot/assets/arte_externa/manifesto_arte.json;
  - diz quais artes estão PRESENTES, quais FALTAM e quais estão com NOME ERRADO ou PARECIDO
    (maiúsculas, espaço no lugar de _, pasta errada, extensão diferente...);
  - avisa se a proporção da imagem está muito diferente da pedida (o jogo recorta, mas pode cortar demais);
  - grava o relatório em godot/assets/arte_externa/RELATORIO_ARTE.txt.

Só usa a biblioteca padrão do Python (não precisa instalar nada).
"""

import difflib
import json
import struct
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PASTA_ARTE = RAIZ / "godot" / "assets" / "arte_externa"
MANIFESTO = PASTA_ARTE / "manifesto_arte.json"
DOC_PROMPTS = RAIZ / "docs" / "PROMPTS_ARTE.md"
RELATORIO = PASTA_ARTE / "RELATORIO_ARTE.txt"
EXTENSOES = {".png", ".jpg", ".jpeg", ".webp"}
# Diferença de proporção a partir da qual vale avisar (25%).
TOLERANCIA_PROPORCAO = 0.25


def normalizar(nome):
    """'Pôster Celebre (1).PNG' -> 'poster_celebre' (sem acento, minúsculo, sem extensão nem cópia)."""
    base = Path(nome).stem
    base = unicodedata.normalize("NFD", base).encode("ascii", "ignore").decode()
    base = base.lower().replace(" ", "_").replace("-", "_")
    for lixo in ("(1)", "(2)", "(3)", "_copia", "_copy"):
        base = base.replace(lixo, "")
    while "__" in base:
        base = base.replace("__", "_")
    return base.strip("_")


def tamanho_imagem(caminho):
    """Lê largura e altura de PNG, JPEG ou WEBP sem bibliotecas extras. Devolve None se não souber."""
    try:
        with open(caminho, "rb") as f:
            cabeca = f.read(32)
            if cabeca.startswith(b"\x89PNG"):
                return struct.unpack(">II", cabeca[16:24])
            if cabeca[:4] == b"RIFF" and cabeca[8:12] == b"WEBP":
                f.seek(12)
                dados = f.read(30)
                if dados[:4] == b"VP8X":
                    w = 1 + int.from_bytes(dados[12:15], "little")
                    h = 1 + int.from_bytes(dados[15:18], "little")
                    return w, h
                return None
            if cabeca[:2] == b"\xff\xd8":
                f.seek(2)
                while True:
                    marca = f.read(2)
                    if len(marca) < 2 or marca[0] != 0xFF:
                        return None
                    tam = struct.unpack(">H", f.read(2))[0]
                    if marca[1] in (0xC0, 0xC1, 0xC2):
                        f.read(1)
                        h, w = struct.unpack(">HH", f.read(4))
                        return w, h
                    f.seek(tam - 2, 1)
    except OSError:
        return None
    return None


def proporcao_em_numero(texto):
    a, b = texto.split(":")
    return float(a) / float(b)


def main():
    corrigir = "--corrigir" in sys.argv
    manifesto = json.loads(MANIFESTO.read_text(encoding="utf-8"))["artes"]
    arquivos = [p for p in PASTA_ARTE.rglob("*") if p.is_file() and p.suffix.lower() in EXTENSOES]
    usados = set()
    linhas = []
    contagem = {"ok": 0, "parecido": 0, "faltando": 0}

    def log(texto=""):
        print(texto)
        linhas.append(texto)

    log(f"Verificação das artes externas — {datetime.now():%d/%m/%Y %H:%M}")
    log(f"Pasta: {PASTA_ARTE}")
    log("")

    for arte in manifesto:
        esperado = PASTA_ARTE / arte["pasta"] / arte["arquivo"]
        rotulo = f'{arte["id"]} [{arte["prioridade"]}] {arte["pasta"]}/{arte["arquivo"]}'
        alvo = None
        situacao = ""

        if esperado.exists():
            alvo, situacao = esperado, "OK"
        else:
            # Mesmo nome com outra extensão de imagem (o jogo aceita .jpg, .jpeg, .png e .webp).
            for ext in sorted(EXTENSOES - {esperado.suffix}):
                alt = esperado.with_suffix(ext)
                if alt.exists():
                    alvo, situacao = alt, f"OK (está em {ext.upper()[1:]}, funciona)"
                    break

        if alvo:
            usados.add(alvo.resolve())
            contagem["ok"] += 1
            aviso = ""
            tam = tamanho_imagem(alvo)
            if tam:
                real = tam[0] / tam[1]
                pedida = proporcao_em_numero(arte["proporcao"])
                if abs(real - pedida) / pedida > TOLERANCIA_PROPORCAO:
                    aviso = f"  ! proporção {tam[0]}x{tam[1]} bem diferente de {arte['proporcao']}: o jogo vai recortar bastante"
                else:
                    aviso = f"  ({tam[0]}x{tam[1]})"
            log(f"[PRESENTE] {rotulo} — {situacao}{aviso}")
            continue

        # Procura nomes parecidos em qualquer subpasta.
        chave = normalizar(arte["arquivo"])
        candidatos = []
        for p in arquivos:
            if p.resolve() in usados:
                continue
            n = normalizar(p.name)
            nota = 1.0 if n == chave else difflib.SequenceMatcher(None, n, chave).ratio()
            if nota >= 0.75:
                candidatos.append((nota, p))
        candidatos.sort(key=lambda c: -c[0])

        if candidatos:
            nota, p = candidatos[0]
            relativo = p.relative_to(PASTA_ARTE).as_posix()
            certeza = nota == 1.0
            if corrigir and certeza:
                destino = esperado.with_suffix(p.suffix.lower())  # mantém o formato que veio (jpg, png...)
                destino.parent.mkdir(parents=True, exist_ok=True)
                if not destino.exists():
                    p.rename(destino)
                    usados.add(destino.resolve())
                    contagem["ok"] += 1
                    log(f"[CORRIGIDO] {rotulo} — '{relativo}' foi renomeado/movido para o nome certo")
                    continue
            usados.add(p.resolve())
            contagem["parecido"] += 1
            dica = "rode com --corrigir para arrumar sozinho" if certeza else "confira se é esta mesmo e renomeie"
            log(f"[NOME ERRADO] {rotulo} — achei '{relativo}' ({dica})")
        else:
            contagem["faltando"] += 1
            log(f"[FALTANDO] {rotulo} — {arte['onde']}")

    sobras = [p for p in arquivos if p.resolve() not in usados]
    if sobras:
        log("")
        log("Arquivos que não correspondem a nenhuma arte da lista (o jogo ignora):")
        for p in sobras:
            log(f"  - {p.relative_to(PASTA_ARTE).as_posix()}")

    # Confere se a lista bate com o documento de prompts (evita ficha esquecida).
    if DOC_PROMPTS.exists():
        doc = DOC_PROMPTS.read_text(encoding="utf-8")
        sem_ficha = [a["arquivo"] for a in manifesto if a["arquivo"] not in doc]
        if sem_ficha:
            log("")
            log("AVISO: artes do manifesto sem ficha no PROMPTS_ARTE.md: " + ", ".join(sem_ficha))

    log("")
    log(f"Resumo: {contagem['ok']} presentes, {contagem['parecido']} com nome errado/parecido, "
        f"{contagem['faltando']} faltando (de {len(manifesto)}).")
    log("Artes que faltam não quebram o jogo: ele usa a versão feita por código no lugar.")
    RELATORIO.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"\nRelatório salvo em {RELATORIO}")


if __name__ == "__main__":
    main()
