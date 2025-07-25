#!/usr/bin/env python3

import os
import sys
import re
from pathlib import Path
from collections import defaultdict

# === CONFIG ===
PROJECT_ROOT = Path(__file__).parent.resolve()
IGNORE_DIRS = {"node_modules", ".venv", "dist", "build", "__pycache__", ".cache", "~build"}
IMAGE_EXTENSIONS = {".png", ".svg", ".gif"}
MARKUP_EXTENSIONS = {".md", ".html"}

def is_ignored(path: Path):
    return any(part in IGNORE_DIRS for part in path.parts)

def find_all_local_images():
    return [
        p for p in PROJECT_ROOT.rglob("*")
        if not is_ignored(p) and p.suffix.lower() in IMAGE_EXTENSIONS
    ]

def find_all_image_references():
    pattern = re.compile(r"""(?:!\[.*?\]\(|<img\s+[^>]*src=['"])([^'")]+)(?:['"])""", re.IGNORECASE)
    refs = []

    for file in PROJECT_ROOT.rglob("*"):
        if is_ignored(file) or file.suffix.lower() not in MARKUP_EXTENSIONS:
            continue
        try:
            content = file.read_text(encoding="utf-8")
        except Exception:
            continue

        for match in pattern.findall(content):
            ref = match.strip()
            if ref.startswith("http://") or ref.startswith("https://"):
                continue
            if "{{" in ref or "{%" in ref:  # exclude templating
                continue
            refs.append((file, ref))
    return refs

def normalize_path(ref, base_file):
    if ref.startswith("/"):
        return (PROJECT_ROOT / "docs" / ref.lstrip("/")).resolve()
    return (base_file.parent / ref).resolve()

def img_check():
    print("🔍 Verifica immagini locali nel progetto...\n")

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

    print(f"📂 Immagini trovate: {len(all_images)}")

    print(f"\n🔗 Immagini referenziate: {len(referenced_paths)}")
    for img in sorted(referenced_paths):
        rel_img = img.relative_to(PROJECT_ROOT)
        sources = [p.relative_to(PROJECT_ROOT) for p in sorted(image_to_sources[img])]
        for src in sources:
            print(f"  - {rel_img} ← {src}")

    print(f"\n🖼️ Immagini locali non usate: {len(unused_images)}")
    if unused_images:
        for img in sorted(unused_images):
            print(f"  - {img.relative_to(PROJECT_ROOT)}")
    else:
        print("  ✅ Nessuna immagine inutilizzata")

    print("\n❌ Riferimenti a immagini locali mancanti:")
    if missing_refs:
        for md_file, ref, resolved in missing_refs:
            print(f"  - {ref} (in {md_file.relative_to(PROJECT_ROOT)}) → NON TROVATO")
    else:
        print("  ✅ Nessun riferimento rotto")

def main():
    img_check()

if __name__ == "__main__":
    main()
