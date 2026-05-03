"""文件夹管理：拼接路径、创建文件夹"""

import os
import config


def build_folder_path(serial: str, bom: str, gene: str) -> str:
    """
    根据流水号、实验BOM、基因名 拼接完整路径:
      桌面/项目管理/{流水号}-{实验BOM}-{基因名}/
    """
    folder_name = f"{serial}-{bom}-{gene}"
    return os.path.join(config.get("project_root"), folder_name)


def ensure_subfolder(base_path: str, subfolder: str) -> str:
    """确保子文件夹存在，返回完整路径"""
    full = os.path.join(base_path, subfolder)
    os.makedirs(full, exist_ok=True)
    return full


def get_subfolder(base_path: str, order_type: str) -> str:
    """根据订单类型获取默认子文件夹名称"""
    if order_type == "primer":
        sub = config.SUBFOLDER_PRIMER
    else:
        sub = config.SUBFOLDER_SEQUENCING
    return ensure_subfolder(base_path, sub)


def find_gene_folder(gene_name: str) -> str | None:
    """
    在项目管理目录中搜索包含基因名的文件夹。
    返回匹配的文件夹路径，找不到返回 None。
    """
    root = config.get("project_root")
    if not os.path.isdir(root):
        return None

    gene_upper = gene_name.upper()
    for entry in os.listdir(root):
        full = os.path.join(root, entry)
        if os.path.isdir(full) and gene_upper in entry.upper():
            return full
    return None
