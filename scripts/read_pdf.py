# -*- coding: utf-8 -*-
import sys, pypdf
path = r"C:\Users\sn\Documents\データ分析\osaka-fudosan-dataanalysis\tableau\dashboard_wireframes\osaka_real_estate_dashboard_revised.pdf"
r = pypdf.PdfReader(path)
print("pages:", len(r.pages))
for i, pg in enumerate(r.pages):
    print("===== page", i, "=====")
    try:
        print(pg.extract_text())
    except Exception as e:
        print("[extract error]", e)
