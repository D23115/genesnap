"""截图保存 + 自动编号"""

import os
import re
from PySide6.QtGui import QPixmap


def save_screenshot(pixmap: QPixmap, folder_path: str, order_id: str, gene_name: str) -> str:
    """
    保存截图到指定文件夹，自动递增编号。

    命名规则: {order_id}_{gene_name}_{N}.png
    示例: TSP20260421-021-00312_POLR2H_1.png
    返回保存的完整路径。
    """
    os.makedirs(folder_path, exist_ok=True)

    pattern = re.compile(
        re.escape(f"{order_id}_{gene_name}_") + r"(\d+)\.png$",
        re.IGNORECASE
    )

    max_n = 0
    try:
        for fname in os.listdir(folder_path):
            m = pattern.match(fname)
            if m:
                n = int(m.group(1))
                if n > max_n:
                    max_n = n
    except OSError:
        pass

    new_n = max_n + 1
    filename = f"{order_id}_{gene_name}_{new_n}.png"
    full_path = os.path.join(folder_path, filename)
    pixmap.save(full_path, "PNG")
    return full_path
