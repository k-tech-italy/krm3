#!/usr/bin/env python3

import re
from pathlib import Path
from collections import defaultdict

import djclick as click

# === CONFIG ===
DOCS_ROOT = (Path(__file__).parents[4] / 'docs').resolve()
IMAGE_EXTENSIONS = {'.png', '.svg', '.gif'}
MARKUP_EXTENSIONS = {'.md', '.html'}


def find_all_local_images():
    return [p for p in DOCS_ROOT.rglob('*') if p.suffix.lower() in IMAGE_EXTENSIONS]


def find_all_image_references():
    pattern = re.compile(r"""(?:!\[.*?\]\(|<img\s+[^>]*src=['"])([^'")]+)(?:['"])""", re.IGNORECASE)
    refs = []

    for file in DOCS_ROOT.rglob('*'):
        if file.suffix.lower() not in MARKUP_EXTENSIONS:
            continue
        try:
            content = file.read_text(encoding='utf-8')
        except Exception:
            continue

        for match in pattern.findall(content):
            ref = match.strip()
            if ref.startswith('http://') or ref.startswith('https://'):
                continue
            if '{{' in ref or '{%' in ref:  # exclude templating
                continue
            refs.append((file, ref))
    return refs


def normalize_path(ref, base_file):
    if ref.startswith('/'):
        return (DOCS_ROOT / 'docs' / ref.lstrip('/')).resolve()
    return (base_file.parent / ref).resolve()


@click.command()
def command():
    click.echo('🔍 Verifica immagini locali nel progetto...\n')

    all_images = find_all_local_images()
    all_image_paths = set(p.resolve() for p in all_images)

    refs = find_all_image_references()
    referenced_paths = set()
    image_to_sources = defaultdict(set)
    missing_refs = []

    for md_file, ref in refs:
        resolved = normalize_path(ref, md_file)
        if resolved in all_image_paths:
            referenced_paths.add(resolved)
            image_to_sources[resolved].add(md_file)
        elif not resolved.exists():
            missing_refs.append((md_file, ref, resolved))

    unused_images = all_image_paths - referenced_paths

    click.echo(f'📂 Immagini trovate: {len(all_images)}')

    click.echo(f'\n🔗 Immagini referenziate: {len(referenced_paths)}')
    for img in sorted(referenced_paths):
        rel_img = img.relative_to(DOCS_ROOT)
        sources = [p.relative_to(DOCS_ROOT) for p in sorted(image_to_sources[img])]
        for src in sources:
            click.echo(f'  - {rel_img} ← {src}')

    click.echo(f'\n🖼️ Immagini locali non usate: {len(unused_images)}')
    if unused_images:
        for img in sorted(unused_images):
            click.echo(f'  - {img.relative_to(DOCS_ROOT)}')
    else:
        click.echo('  ✅ Nessuna immagine inutilizzata')

    click.echo('\n❌ Riferimenti a immagini locali mancanti:')
    if missing_refs:
        for md_file, ref, resolved in missing_refs:
            click.echo(f'  - {ref} (in {md_file.relative_to(DOCS_ROOT)}) → NON TROVATO')
    else:
        click.echo('  ✅ Nessun riferimento rotto')
