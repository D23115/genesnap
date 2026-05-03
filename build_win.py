# PyInstaller 打包脚本（用于本地 Windows 打包测试）
# 用法: python build_win.py

import PyInstaller.__main__
import os

PyInstaller.__main__.run([
    "main.py",
    "--name=GeneSnap",
    "--onefile",
    "--windowed",
    "--add-data=config.py:.",
    "--add-data=ocr_engine.py:.",
    "--add-data=info_extractor.py:.",
    "--add-data=excel_manager.py:.",
    "--add-data=folder_manager.py:.",
    "--add-data=image_saver.py:.",
    "--add-data=dialogs.py:.",
    "--add-data=screenshot_overlay.py:.",
    "--hidden-import=paddleocr",
    "--hidden-import=paddle",
    "--hidden-import=openpyxl",
    "--hidden-import=keyboard",
    "--hidden-import=PySide6",
    "--clean",
    "--noconfirm",
])
