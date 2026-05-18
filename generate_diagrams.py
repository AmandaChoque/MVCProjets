#!/usr/bin/env python
"""
Genera archivos PNG desde los .puml usando el servidor online de PlantUML.
No requiere instalación local de PlantUML ni Java.

Uso:
    python generate_diagrams.py                    # procesa todos los .puml
    python generate_diagrams.py docs/diagrama.puml # procesa un archivo específico
    python generate_diagrams.py --out docs/imgs/   # directorio de salida personalizado

Los PNG se guardan junto al .puml (o en --out si se especifica).
"""
import sys
import zlib
import argparse
import urllib.request
from pathlib import Path


# ---------------------------------------------------------------------------
# Encoding PlantUML (compatible con plantuml.com/plantuml/png/<encoded>)
# ---------------------------------------------------------------------------

def _encode6bit(b: int) -> str:
    if b < 10:
        return chr(48 + b)
    b -= 10
    if b < 26:
        return chr(65 + b)
    b -= 26
    if b < 26:
        return chr(97 + b)
    b -= 26
    return '-' if b == 0 else '_'


def _append3bytes(b1: int, b2: int, b3: int) -> str:
    return (
        _encode6bit(b1 >> 2)
        + _encode6bit(((b1 & 0x3) << 4) | (b2 >> 4))
        + _encode6bit(((b2 & 0xF) << 2) | (b3 >> 6))
        + _encode6bit(b3 & 0x3F)
    )


def plantuml_encode(text: str) -> str:
    """Codifica texto PlantUML para el servidor plantuml.com."""
    raw = zlib.compress(text.encode('utf-8'), 9)[2:-4]  # raw DEFLATE sin cabecera zlib
    result = ''
    for i in range(0, len(raw), 3):
        chunk = raw[i:i + 3]
        b1 = chunk[0]
        b2 = chunk[1] if len(chunk) > 1 else 0
        b3 = chunk[2] if len(chunk) > 2 else 0
        result += _append3bytes(b1, b2, b3)
    return result


# ---------------------------------------------------------------------------
# Generación
# ---------------------------------------------------------------------------

BASE_URL = 'http://www.plantuml.com/plantuml/png/'


def generate_png(puml_path: Path, out_dir: Path | None = None) -> Path:
    text = puml_path.read_text(encoding='utf-8')
    encoded = plantuml_encode(text)
    url = BASE_URL + encoded

    target_dir = out_dir if out_dir else puml_path.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    png_path = target_dir / puml_path.with_suffix('.png').name

    print(f'  → {puml_path.name}  ...  ', end='', flush=True)
    with urllib.request.urlopen(url, timeout=30) as resp:
        png_path.write_bytes(resp.read())
    print(f'guardado en {png_path}')
    return png_path


def main() -> None:
    parser = argparse.ArgumentParser(description='Genera PNG desde archivos PlantUML.')
    parser.add_argument('files', nargs='*', help='Archivos .puml (por defecto: todos)')
    parser.add_argument('--out', metavar='DIR', help='Directorio de salida para los PNG')
    args = parser.parse_args()

    root = Path(__file__).parent
    out_dir = Path(args.out) if args.out else None

    if args.files:
        files = [Path(f) for f in args.files]
    else:
        files = sorted(root.glob('**/*.puml'))
        # Excluir la carpeta venv
        files = [f for f in files if 'venv' not in f.parts]

    if not files:
        print('No se encontraron archivos .puml')
        return

    print(f'Procesando {len(files)} archivo(s)...\n')
    errors: list[tuple[Path, str]] = []

    for puml_path in files:
        try:
            generate_png(puml_path, out_dir)
        except Exception as exc:
            errors.append((puml_path, str(exc)))
            print(f'ERROR: {exc}')

    total = len(files)
    ok = total - len(errors)
    print(f'\n{ok}/{total} archivos generados correctamente.')

    if errors:
        print('\nErrores:')
        for path, err in errors:
            print(f'  {path.name}: {err}')
        sys.exit(1)


if __name__ == '__main__':
    main()
