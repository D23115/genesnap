"""PaddleOCR 封装 + 后台初始化"""

import os
import sys
import re
import threading
import tempfile
import traceback
from io import StringIO

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QPixmap

import config

_ocr_instance = None
_init_result = None  # (ok, error_msg) 或 None=进行中
_init_lock = threading.Lock()

# 模型下载状态（供外部轮询）
init_status = "等待启动..."
init_progress = 0  # 0-100, -1 表示不确定
download_log = []


class _ProgressCapture:
    """捕获 tqdm 输出并解析进度"""

    def __init__(self):
        self.percentage = 0
        self.current_file = ""
        self._buffer = ""

    def write(self, s: str):
        self._buffer += s
        # tqdm 格式: "Fetching 6 files:  83%|████████  | 5/6 [00:25<00:05]"
        m = re.search(r"Fetching \d+ files?:\s+(\d+)%", self._buffer)
        if m:
            self.percentage = int(m.group(1))
        # 检测每个文件的下载
        m2 = re.search(r"Downloading.*?:\s+(\d+)%", self._buffer)
        if m2:
            self.percentage = int(m2.group(1))
        # 超过一屏就截断
        if len(self._buffer) > 8192:
            self._buffer = self._buffer[-4096:]

    def flush(self):
        pass


def _init_ocr_background():
    """后台线程：初始化 PaddleOCR，捕获下载进度"""
    global _ocr_instance, _init_result, init_status, init_progress, download_log

    # 跳过网络连通性检查，加速启动
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

    with _init_lock:
        init_status = "正在检查模型缓存..."
        init_progress = -1
        download_log = []

    try:
        # 检查是否已缓存模型
        cache_dir = os.path.expanduser("~/.paddlex/official_models")
        if os.path.isdir(cache_dir):
            cached = [
                d for d in os.listdir(cache_dir)
                if os.path.isdir(os.path.join(cache_dir, d))
            ]
            if len(cached) >= 5:
                init_status = "模型已缓存，正在加载..."
                init_progress = -1
            else:
                init_status = "正在下载 OCR 识别模型...（首次约 50 MB，请耐心等待）"
                init_progress = -1
        else:
            init_status = "正在下载 OCR 识别模型...（首次约 50 MB，请耐心等待）"
            init_progress = -1

        # 重定向 stdout 捕获 tqdm 进度
        capture = _ProgressCapture()
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = capture
        sys.stderr = capture

        try:
            from paddleocr import PaddleOCR
            _ocr_instance = PaddleOCR(lang=config.get("ocr_lang"))
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        # 检查最终进度
        if capture.percentage > 0:
            init_progress = capture.percentage

        init_status = "OCR 引擎就绪"
        init_progress = 100

        with _init_lock:
            _init_result = (True, "")

    except Exception as e:
        tb = traceback.format_exc()
        init_status = f"初始化失败: {e}\n{tb[-300:]}"
        init_progress = 0
        with _init_lock:
            _init_result = (False, f"{e}\n{tb}")


def start_init():
    """启动后台 OCR 初始化线程"""
    global _init_result, init_status, init_progress
    with _init_lock:
        if _init_result is not None:
            return  # 已初始化
        _init_result = None  # 标记为进行中

    init_status = "正在启动..."
    init_progress = -1
    t = threading.Thread(target=_init_ocr_background, daemon=True)
    t.start()


def get_init_status():
    """轮询：返回 (done: bool, ok: bool, status: str, progress: int)"""
    with _init_lock:
        if _init_result is None:
            return (False, False, init_status, init_progress)
        ok, msg = _init_result
        return (True, ok, init_status, init_progress)


def is_ocr_ready() -> bool:
    return _ocr_instance is not None


def _get_ocr():
    global _ocr_instance
    if _ocr_instance is None:
        with _init_lock:
            if _init_result and not _init_result[0]:
                raise RuntimeError(f"OCR 引擎初始化失败: {_init_result[1]}")
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
        if not results:
            return ""

        lines = []
        for item in results:
            # PaddleOCR 3.x: OCRResult (UserDict-like), use .get()
            if hasattr(item, "get"):
                texts = item.get("rec_texts", []) or []
                if texts:
                    lines.extend(texts)
                    continue
            # PaddleOCR 2.x: [[bbox, (text, confidence)], ...]
            if isinstance(item, (list, tuple)):
                for line_info in item:
                    if isinstance(line_info, (list, tuple)) and len(line_info) >= 2:
                        text = line_info[1]
                        if isinstance(text, (list, tuple)) and len(text) >= 1:
                            lines.append(str(text[0]))
                        else:
                            lines.append(str(text))
        return "\n".join(lines)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
