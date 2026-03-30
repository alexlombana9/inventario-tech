#!/usr/bin/env python3
"""Minifica CSS y JS para produccion."""
import os
import re


def minify_css(content):
    """Minificacion basica de CSS."""
    # Eliminar comentarios
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    # Eliminar espacios innecesarios
    content = re.sub(r'\s+', ' ', content)
    content = re.sub(r'\s*([{}:;,>~+])\s*', r'\1', content)
    content = re.sub(r';\s*}', '}', content)
    return content.strip()


def minify_js(content):
    """Minificacion basica de JS (solo espacios y comentarios)."""
    # Eliminar comentarios de linea (cuidado con URLs)
    lines = content.split('\n')
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('//'):
            continue
        result.append(line)
    content = '\n'.join(result)
    # Eliminar comentarios de bloque
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    # Reducir espacios multiples a uno
    content = re.sub(r'[ \t]+', ' ', content)
    # Eliminar lineas vacias
    content = re.sub(r'\n\s*\n', '\n', content)
    return content.strip()


def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # CSS
    css_file = os.path.join(base, 'static', 'css', 'style.css')
    if os.path.exists(css_file):
        with open(css_file, 'r', encoding='utf-8') as f:
            original = f.read()
        minified = minify_css(original)
        out = os.path.join(base, 'static', 'css', 'style.min.css')
        with open(out, 'w', encoding='utf-8') as f:
            f.write(minified)
        savings = (1 - len(minified) / len(original)) * 100
        print(f"CSS: {len(original):,}B -> {len(minified):,}B ({savings:.0f}% reducido)")

    # JS
    js_dir = os.path.join(base, 'static', 'js')
    for fname in sorted(os.listdir(js_dir)):
        if fname.endswith('.js') and not fname.endswith('.min.js'):
            path = os.path.join(js_dir, fname)
            with open(path, 'r', encoding='utf-8') as f:
                original = f.read()
            minified = minify_js(original)
            out = os.path.join(js_dir, fname.replace('.js', '.min.js'))
            with open(out, 'w', encoding='utf-8') as f:
                f.write(minified)
            savings = (1 - len(minified) / len(original)) * 100
            print(f"JS {fname}: {len(original):,}B -> {len(minified):,}B ({savings:.0f}% reducido)")

    print("\nMinificacion completada.")


if __name__ == '__main__':
    main()
