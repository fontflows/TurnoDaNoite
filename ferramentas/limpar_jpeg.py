"""
limpar_jpeg.py — tira dos arquivos JPEG os blocos de metadados EXIF (APP1) e de perfil
de cor ICC (APP2) que o Blender grava. Por que: o leitor de JPEG do Godot recusa esses
arquivos ("Error loading image"). A imagem em si não é recomprimida: nenhum pixel muda.

Uso:  python ferramentas/limpar_jpeg.py <pasta ou arquivo> [...]
(o gerar_texturas.py já chama isto sozinho no final)
"""

import sys
from pathlib import Path

REMOVER = {0xE1, 0xE2}  # APP1 (EXIF) e APP2 (ICC)


def limpar(caminho):
    """Devolve True se o arquivo foi alterado."""
    dados = Path(caminho).read_bytes()
    if dados[:2] != b"\xff\xd8":
        return False
    saida = bytearray(dados[:2])
    i = 2
    mudou = False
    while i + 4 <= len(dados) and dados[i] == 0xFF:
        marca = dados[i + 1]
        if marca == 0xDA:  # início dos dados da imagem: copia o resto como está
            break
        tamanho = int.from_bytes(dados[i + 2:i + 4], "big")
        if marca in REMOVER:
            mudou = True
        else:
            saida += dados[i:i + 2 + tamanho]
        i += 2 + tamanho
    if not mudou:
        return False
    saida += dados[i:]
    Path(caminho).write_bytes(bytes(saida))
    return True


def limpar_tudo(alvos):
    total = 0
    for alvo in alvos:
        p = Path(alvo)
        arquivos = list(p.rglob("*.jpg")) + list(p.rglob("*.jpeg")) if p.is_dir() else [p]
        total += sum(limpar(a) for a in arquivos)
    return total


if __name__ == "__main__":
    print(f"limpar_jpeg: {limpar_tudo(sys.argv[1:] or ['.'])} arquivo(s) limpo(s)")
