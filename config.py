"""GeneSnap 配置管理"""

import os
import json

CONFIG_FILE = os.path.expanduser("~/.genesnap_config.json")

DESKTOP = os.path.expanduser("~/Desktop")
PROJECT_ROOT = os.path.join(DESKTOP, "项目管理")
WORK_DIR = os.path.join(DESKTOP, "自动生成shRNA")
PROGRESS_XLSX = os.path.join(WORK_DIR, "项目进度表.xlsx")
HOTKEY = "Ctrl+Shift+X"
OCR_LANG = "ch"

# Column mapping in Excel (1-based)
COL_GENE_NAME = "D"       # 基因名
COL_SERIAL = "B"          # 流水号
COL_BOM = "C"             # 实验BOM
COL_PRIMER_CONFIRM = "X"  # 引物到货确认
COL_SEQ_CONFIRM = "Y"     # 测序确认

# Subfolders
SUBFOLDER_PRIMER = "引物到货确认"
SUBFOLDER_SEQUENCING = "测序确认"

DEFAULTS = {
    "desktop": DESKTOP,
    "project_root": PROJECT_ROOT,
    "work_dir": WORK_DIR,
    "progress_xlsx": PROGRESS_XLSX,
    "hotkey": HOTKEY,
    "ocr_lang": OCR_LANG,
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_config(cfg: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def get(key):
    saved = load_config()
    if key in saved:
        return saved[key]
    return DEFAULTS.get(key)


def set_(key, value):
    cfg = load_config()
    cfg[key] = value
    save_config(cfg)
