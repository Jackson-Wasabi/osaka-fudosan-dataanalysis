# -*- coding: utf-8 -*-
from pypdf import PdfReader

src = r"C:\Users\sn\Documents\データ分析\osaka_fudosan_dataanalysis_manual_v9.pdf"
dst = r"C:\Users\sn\Documents\データ分析\manual_v9_extracted.txt"

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
