# -*- coding: utf-8 -*-
"""画面キャプチャ（PIL ImageGrab・子プロセスでも安定）。
使い方: python scripts/shot.py
出力: %TEMP%\tab_shot.png （パスを標準出力に表示）
"""
import os
from PIL import ImageGrab

path = os.path.join(os.environ.get("TEMP", "."), "tab_shot.png")
img = ImageGrab.grab()
img.save(path)
print(path)
