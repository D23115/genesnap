"""PaddleOCR 封装"""

from PySide6.QtGui import QPixmap, QImage
import tempfile
import os


_ocr_instance = None


def _get_ocr():
    global _ocr_instance
    if _ocr_instance is None:
        from paddleocr import PaddleOCR
        import config
        _ocr_instance = PaddleOCR(lang=config.get("ocr_lang"), use_angle_cls=True)
    return _ocr_instance


def _save_temp_png(pixmap: QPixmap) -> str:
    """QPixmap 保存为临时 PNG 文件，返回路径"""
    image = pixmap.toImage()
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        path = f.name
    image.save(path, "PNG")
    return path


def ocr_image(pixmap: QPixmap) -> str:
    """
    对截图进行 OCR 识别，返回原始文本。

    输入：QPixmap 截图
    输出：识别出的全部文本（换行分隔）
    异常：OCR 失败时抛出
    """
    path = _save_temp_png(pixmap)
    try:
        ocr = _get_ocr()
        results = ocr.ocr(path)
        if not results or not results[0]:
            return ""

        lines = []
        for line_info in results[0]:
            text = line_info[1][0]
            lines.append(text)
        return "\n".join(lines)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
