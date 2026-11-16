"""Rasterize the SVG using PyMuPDF; install it in a separate tooling environment."""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import fitz
from generate_erd import RELATIONS, TABLES, validate

ROOT = Path(__file__).resolve().parent
svg = ROOT / "teknocare_improved_erd.svg"
tree = ET.parse(svg)
ns = {"s": "http://www.w3.org/2000/svg"}
nodes = tree.findall('.//s:g[@class="node"]', ns)
edges = tree.findall('.//s:g[@class="edge"]', ns)
validate()
assert len(nodes) == len(TABLES), f"Expected {len(TABLES)} entity boxes, got {len(nodes)}"
assert len(edges) == len(RELATIONS), f"Expected {len(RELATIONS)} FK connectors, got {len(edges)}"
assert {n.find('s:title', ns).text for n in nodes} == set(TABLES)
expected_edges = {f'{parent}->{child}' for child, _, parent, _, _ in RELATIONS}
assert {e.find('s:title', ns).text for e in edges} == expected_edges
doc = fitz.open(svg)
pdf = fitz.open("pdf", doc.convert_to_pdf())
page = pdf[0]
# Large enough to zoom into individual columns without an excessive bitmap.
scale = 8000 / max(page.rect.width, page.rect.height)
pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
output = ROOT / "teknocare_improved_erd.png"
pix.save(output)
print(f"Verified {len(nodes)} nodes / {len(edges)} edges. PNG: {pix.width} x {pix.height}; {output.stat().st_size:,} bytes.")
if len(sys.argv) > 1:
    page.get_pixmap(matrix=fitz.Matrix(1700 / max(page.rect.width, page.rect.height),
                                     1700 / max(page.rect.width, page.rect.height)),
                    alpha=False).save(sys.argv[1])
