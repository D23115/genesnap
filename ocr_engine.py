"""PaddleOCR 封装 + 后台初始化"""

import os
import tempfile

from PySide6.QtCore import QObject, Signal

from PySide6.QtGui import QPixmap

import config

_ocr_instance = None
_init_error = None


class OcrInitWorker(QObject):
    """后台线程初始化 PaddleOCR，避免主线程卡死"""

    status_updated = Signal(str)
    finished = Signal(bool, str)  # success, error_msg

    def run(self):
        global _ocr_instance, _init_error
        try:
            self._check_models()
            _ocr_instance = self._create_ocr()
            self.status_updated.emit("OCR 引擎就绪")
            self.finished.emit(True, "")
        except Exception as e:
            _init_error = str(e)
            self.finished.emit(False, str(e))

    def _check_models(self):
        """检查模型是否已缓存"""
        cache_dir = os.path.expanduser("~/.paddlex/official_models")
        if os.path.isdir(cache_dir):
            entries = [
                e for e in os.listdir(cache_dir)
                if os.path.isdir(os.path.join(cache_dir, e))
            ]
            if len(entries) >= 5:
                self.status_updated.emit("正在加载 OCR 模型...")
                return
        self.status_updated.emit("首次运行，正在下载 OCR 识别模型（约 50 MB）...")

    def _create_ocr(self):
        from paddleocr import PaddleOCR
        return PaddleOCR(lang=config.get("ocr_lang"), use_angle_cls=True)


def is_ocr_ready() -> bool:
    return _ocr_instance is not None


def _get_ocr():
    global _ocr_instance
    if _ocr_instance is None:
        if _init_error:
            raise RuntimeError(f"OCR 引擎初始化失败: {_init_error}")
        raise RuntimeError("OCR 引擎尚未初始化完成")
    return _ocr_instance


def _save_temp_png(pixmap: QPixmap) -> str:
    image = pixmap.toImage()
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        path = f.name
    image.save(path, "PNG")
    return path


def ocr_image(pixmap: QPixmap) -> str:
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
