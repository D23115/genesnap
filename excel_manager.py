"""项目进度表.xlsx 读写操作"""

import os
import openpyxl

import config


def _open_workbook():
    path = config.get("progress_xlsx")
    if not os.path.exists(path):
        raise FileNotFoundError(f"找不到项目进度表: {path}")
    return openpyxl.load_workbook(path)


_COL_IDX = {}  # column letter → 1-based index cache


def _col_letter_to_index(letter: str) -> int:
    """列字母转 1-based 列号：D→4, X→24, Y→25"""
    if letter in _COL_IDX:
        return _COL_IDX[letter]
    idx = 0
    for ch in letter.upper():
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    _COL_IDX[letter] = idx
    return idx


def _col_index_to_letter(idx: int) -> str:
    """1-based 列号转字母：4→D, 24→X"""
    result = ""
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        result = chr(rem + ord("A")) + result
    return result


def find_gene_row(gene_name: str) -> int | None:
    """
    在 D 列查找完全匹配的基因名。
    返回行号（1-based），找不到返回 None。
    跳过 D 列为 'CTRL' 的行、空白行、表头行。
    """
    wb = _open_workbook()
    ws = wb.active
    col_d = _col_letter_to_index(config.COL_GENE_NAME)

    for row in range(2, ws.max_row + 1):
        cell_val = ws.cell(row=row, column=col_d).value
        if cell_val and str(cell_val).strip().upper() == gene_name.upper():
            wb.close()
            return row

    wb.close()
    return None


def get_row_data(row: int) -> dict:
    """获取指定行的 B、C、D 列数据"""
    wb = _open_workbook()
    ws = wb.active
    data = {
        "serial": ws.cell(row=row, column=_col_letter_to_index(config.COL_SERIAL)).value,
        "bom": ws.cell(row=row, column=_col_letter_to_index(config.COL_BOM)).value,
        "gene": ws.cell(row=row, column=_col_letter_to_index(config.COL_GENE_NAME)).value,
    }
    wb.close()
    return data


def write_order_to_cell(row: int, order_type: str, order_id: str):
    """
    写入订单号到 X 列（引物）或 Y 列（测序）。
    追加规则：空则直接写，已有内容则追加 "; order_id"。
    """
    col = config.COL_PRIMER_CONFIRM if order_type == "primer" else config.COL_SEQ_CONFIRM

    wb = _open_workbook()
    ws = wb.active
    cell = ws.cell(row=row, column=_col_letter_to_index(col))
    existing = cell.value

    if existing:
        cell.value = f"{existing}; {order_id}"
    else:
        cell.value = order_id

    wb.save(config.get("progress_xlsx"))
    wb.close()
