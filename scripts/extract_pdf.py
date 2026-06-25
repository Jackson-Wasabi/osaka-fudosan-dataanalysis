# -*- coding: utf-8 -*-
import os
from pypdf import PdfReader

# マニュアルPDFはリポジトリ外（親フォルダ）に置く想定。環境変数で上書き可。
_PARENT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
src = os.environ.get("MANUAL_PDF", os.path.join(_PARENT, "osaka_fudosan_dataanalysis_manual_v9.pdf"))
dst = os.environ.get("MANUAL_TXT", os.path.join(_PARENT, "manual_v9_extracted.txt"))

r = PdfReader(src)
print("pages:", len(r.pages))
out = []
for i, p in enumerate(r.pages):
    out.append(f"===== PAGE {i+1} =====")
    out.append(p.extract_text() or "(no text)")
text = "\n".join(out)
with open(dst, "w", encoding="utf-8") as f:
    f.write(text)
print("chars:", len(text))
