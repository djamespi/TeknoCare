"""Rasterize the SVG using PyMuPDF; install it in a separate tooling environment."""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parent
svg = ROOT / "teknocare_improved_erd.svg"
tree = ET.parse(svg)
ns = {"s": "http://www.w3.org/2000/svg"}
nodes = tree.findall('.//s:g[@class="node"]', ns)
edges = tree.findall('.//s:g[@class="edge"]', ns)
assert len(nodes) == 20, f"Expected 20 entity boxes, got {len(nodes)}"
assert len(edges) == 25, f"Expected 25 FK connectors, got {len(edges)}"
doc = fitz.open(svg)
pdf = fitz.open("pdf", doc.convert_to_pdf())
page = pdf[0]
# Large enough to zoom into individual columns without an excessive bitmap.
scale = 8000 / max(page.rect.width, page.rect.height)
pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
output = ROOT / "teknocare_improved_erd.png"
pix.save(output)
print(f"Verified 20 nodes / 25 edges. PNG: {pix.width} x {pix.height}; {output.stat().st_size:,} bytes.")
if len(sys.argv) > 1:
    page.get_pixmap(matrix=fitz.Matrix(1700 / max(page.rect.width, page.rect.height),
                                     1700 / max(page.rect.width, page.rect.height)),
                    alpha=False).save(sys.argv[1])
