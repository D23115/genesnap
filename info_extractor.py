"""从 OCR 文本提取订单号、基因名、订单类型"""

import re

# 订单号格式：TSP 或 TSS 开头，后跟数字-数字-数字
ORDER_ID_PATTERN = re.compile(r"(TSP\d+-\d+-\d+|TSS\d+-\d+-\d+)", re.IGNORECASE)

# 非基因名的常见英文单词（OCR 可能误识别为基因名）
NON_GENE_WORDS = {
    "SAMPLE", "NAME", "GENE", "ORDER", "PAGE", "DATE", "TYPE",
    "PRIMER", "NO", "ID", "SEQ", "NOTE", "TOTAL", "TABLE",
}

# 引物命名格式：基因名-数字-方向(F/R)  如 POLR2H-1-F
PRIMER_GENE_PATTERN = re.compile(r"([A-Za-z0-9]+)-\d+-[FR][^A-Za-z]?")


def _extract_gene_from_primer(text: str) -> str | None:
    """从引物命名中提取基因名，如 POLR2H-1-F → POLR2H"""
    match = PRIMER_GENE_PATTERN.search(text)
    if match:
        return match.group(1).upper()
    return None


def _is_order_id_line(text: str) -> bool:
    """判断该行是否包含订单号"""
    return bool(ORDER_ID_PATTERN.search(text))


def _extract_gene_from_line(text: str, order_id: str = "") -> str | None:
    """
    从单行文本提取基因名。
    跳过：包含订单号的行、纯数字、日期。
    优先：标签格式 > 引物格式 > 纯基因名。
    """
    # 跳过包含订单号的行
    if _is_order_id_line(text):
        return None
    # 纯数字或日期行直接跳过
    if re.match(r"^\d+$", text.strip()):
        return None
    if re.match(r"^\d{4}[-/]\d{2}", text):
        return None

    # 1. 标签格式："Sample: GENENAME" / "样品: GENENAME"（可能含中文）
    sample_m = re.search(r"(?:Sample|样品|样本|基因)[：:\s]+([A-Za-z0-9]+)", text.strip(), re.IGNORECASE)
    if sample_m:
        gene = sample_m.group(1).upper()
        if gene not in NON_GENE_WORDS and not gene.startswith(("TSP", "TSS")):
            return gene

    # 2. 引物格式：GENENAME-数字-F/R → GENENAME
    gene = _extract_gene_from_primer(text)
    if gene:
        if not gene.upper().startswith(("TSP", "TSS")):
            return gene

    # 3. 纯文本基因名
    # 跳过只含中文的行（标签已处理过）
    if re.search(r"^[一-鿿\s]+$", text):
        return None

    m = re.match(r"^([A-Za-z]{2,}[A-Za-z0-9]*)\b", text.strip())
    if m:
        gene = m.group(1).upper()
        if gene.startswith(("TSP", "TSS")):
            return None
        if gene in NON_GENE_WORDS:
            return None
        return gene

    return None


def extract_order_info(raw_text: str) -> dict:
    """
    从 OCR 原始文本提取订单信息。

    返回:
        {"order_id": str, "gene_name": str, "order_type": "primer"|"sequencing"} 或 None
    """
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]

    # 1. 提取订单号
    order_id = None
    order_type = None
    for line in lines:
        m = ORDER_ID_PATTERN.search(line)
        if m:
            order_id = m.group(1).upper()
            order_type = "primer" if order_id.startswith("TSP") else "sequencing"
            break

    if not order_id:
        return None

    # 2. 提取基因名 — 遍历行寻找第一个有效基因名
    gene_name = None
    for line in lines:
        gene = _extract_gene_from_line(line)
        if gene:
            gene_name = gene
            break

    if not gene_name:
        return None

    return {
        "order_id": order_id,
        "gene_name": gene_name,
        "order_type": order_type,
    }
