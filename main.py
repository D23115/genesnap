"""GeneSnap — 基因截图管理工具 程序入口"""

import sys
import os
import traceback

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction
from PySide6.QtCore import Qt, QTimer

import config
from screenshot_overlay import ScreenshotOverlay
from ocr_engine import ocr_image, start_init, get_init_status, is_ocr_ready
from info_extractor import extract_order_info
from excel_manager import find_gene_row, get_row_data, write_order_to_cell
from folder_manager import build_folder_path, get_subfolder
from image_saver import save_screenshot
from dialogs import (
    ConfirmDialog, ManualInputDialog, SaveConfirmDialog,
    LoadingDialog, show_error, show_gene_not_found,
)


def _make_tray_icon():
    pix = QPixmap(32, 32)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setBrush(QColor(46, 139, 87))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(4, 4, 24, 24)
    p.setBrush(QColor(255, 255, 255))
    p.drawRect(8, 10, 16, 12)
    p.setBrush(QColor(46, 139, 87))
    p.drawEllipse(12, 13, 8, 6)
    p.end()
    return QIcon(pix)


class GeneSnapApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.tray = None
        self.overlay = None
        self._poll_timer = None
        self._loading_dlg = None

        # 直接显示托盘（让用户知道程序已启动）
        self._setup_tray()

        # 后台初始化 OCR，显示加载进度
        self._init_ocr()

    def _setup_tray(self):
        self.tray = QSystemTrayIcon()
        self.tray.setIcon(_make_tray_icon())
        self.tray.setToolTip("GeneSnap - 基因截图管理工具")

        menu = QMenu()
        capture_action = QAction("立即截图")
        capture_action.triggered.connect(self.start_screenshot)
        menu.addAction(capture_action)
        menu.addSeparator()
        quit_action = QAction("退出")
        quit_action.triggered.connect(self.quit)
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.show()
        self._register_hotkey()

    def _init_ocr(self):
        """启动后台 OCR 初始化，显示加载进度对话框"""
        self._loading_dlg = LoadingDialog()
        self._loading_dlg.setWindowTitle("GeneSnap - 正在初始化 OCR 引擎")
        self._loading_dlg.set_progress(-1, "正在启动 OCR 引擎...")
        self._loading_dlg.show()

        # 启动后台线程
        start_init()

        # 定时轮询状态（每 200ms）
        self._poll_timer = QTimer()
        self._poll_timer.timeout.connect(self._poll_ocr_status)
        self._poll_timer.start(200)

    def _poll_ocr_status(self):
        done, ok, status, progress = get_init_status()

        if self._loading_dlg and self._loading_dlg.isVisible():
            self._loading_dlg.set_progress(progress, status)

        if done:
            self._poll_timer.stop()
            self._poll_timer = None

            if self._loading_dlg:
                self._loading_dlg.close()
                self._loading_dlg = None

            if not ok:
                QMessageBox.critical(
                    None, "启动失败",
                    f"OCR 引擎初始化失败:\n{status}\n\n"
                    "程序将以手动输入模式运行。\n"
                    "请检查网络连接后重新启动。"
                )
                # 不退出，允许手动输入模式
            else:
                self.tray.showMessage(
                    "GeneSnap",
                    "OCR 引擎就绪，按 Ctrl+Shift+X 开始截图",
                    QSystemTrayIcon.MessageIcon.Information,
                    2000,
                )

    def _register_hotkey(self):
        try:
            import keyboard
            hotkey = config.get("hotkey")
            keyboard.add_hotkey(hotkey, self.start_screenshot)
            print(f"[GeneSnap] 全局快捷键已注册: {hotkey}")
        except Exception as e:
            print(f"[GeneSnap] 全局快捷键注册失败: {e}")
            print("[GeneSnap] 可通过托盘菜单手动触发截图")

    # ── 截图流程 ──────────────────────────────────────────────

    def start_screenshot(self):
        if not is_ocr_ready():
            self.tray.showMessage(
                "GeneSnap",
                "OCR 引擎尚未就绪，请稍候...",
                QSystemTrayIcon.MessageIcon.Warning,
                2000,
            )
            return

        self.overlay = ScreenshotOverlay()
        self.overlay.screenshot_taken.connect(self._on_screenshot)
        self.overlay.cancelled.connect(self._on_cancel)
        self.overlay.start()

    def _on_cancel(self):
        print("[GeneSnap] 截图已取消")
        self._cleanup_overlay()

    def _cleanup_overlay(self):
        if self.overlay:
            self.overlay.deleteLater()
            self.overlay = None

    # ── OCR + 信息提取 ────────────────────────────────────────

    def _on_screenshot(self, pixmap: QPixmap):
        self._cleanup_overlay()
        print(f"[GeneSnap] 截图完成: {pixmap.width()}x{pixmap.height()}")

        try:
            raw_text = ocr_image(pixmap)
        except Exception as e:
            traceback.print_exc()
            self._handle_ocr_error(str(e), pixmap)
            return

        if not raw_text.strip():
            self._handle_ocr_empty(pixmap)
            return

        print(f"[GeneSnap] OCR 文本:\n{raw_text}")

        info = extract_order_info(raw_text)

        if info is None:
            self._handle_extract_failure(raw_text, pixmap)
            return

        print(f"[GeneSnap] 提取结果: {info}")
        self._show_confirm_dialog(info, pixmap)

    # ── 弹窗①：确认/修改 ──────────────────────────────────────

    def _show_confirm_dialog(self, info: dict, pixmap: QPixmap):
        dlg = ConfirmDialog(
            order_id=info["order_id"],
            gene_name=info["gene_name"],
            order_type=info["order_type"],
        )
        dlg.exec()

        action = dlg.result_action
        if action == "retry":
            self.start_screenshot()
        elif action == "manual":
            self._show_manual_input(pixmap)
        elif action == "confirm":
            self._process_save(dlg.order_id, dlg.gene_name, dlg.order_type, pixmap)

    def _show_manual_input(self, pixmap: QPixmap):
        dlg = ManualInputDialog()
        if dlg.exec():
            self._process_save(dlg.order_id, dlg.gene_name, dlg.order_type, pixmap)

    # ── Excel 查找 + 保存 ─────────────────────────────────────

    def _process_save(self, order_id: str, gene_name: str, order_type: str, pixmap: QPixmap):
        try:
            row = find_gene_row(gene_name)
        except Exception:
            show_error(f"打开项目进度表失败，请确认文件未被其他程序占用。\n\n{traceback.format_exc()}")
            return

        if row is None:
            new_gene = show_gene_not_found(gene_name)
            if new_gene:
                self._process_save(order_id, new_gene, order_type, pixmap)
            return

        try:
            row_data = get_row_data(row)
        except Exception:
            show_error("读取项目进度表失败。")
            return

        try:
            write_order_to_cell(row, order_type, order_id)
            print(f"[GeneSnap] 已写入 {order_id} → 第{row}行 {order_type}")
        except Exception:
            show_error("写入订单号失败，请确认项目进度表未被其他程序占用。")
            return

        base_path = build_folder_path(
            serial=str(row_data["serial"] or ""),
            bom=str(row_data["bom"] or ""),
            gene=str(row_data["gene"] or gene_name),
        )

        dlg = SaveConfirmDialog(base_path, order_type)
        if not dlg.exec():
            return

        save_path = get_subfolder(base_path, dlg.subfolder)
        try:
            saved = save_screenshot(pixmap, save_path, order_id, gene_name)
            print(f"[GeneSnap] 截图已保存: {saved}")
            self.tray.showMessage(
                "GeneSnap",
                f"已保存: {os.path.basename(saved)}",
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )
        except Exception as e:
            show_error(f"保存截图失败: {e}")

    # ── 错误处理 ──────────────────────────────────────────────

    def _handle_ocr_error(self, error_msg: str, pixmap: QPixmap):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("OCR 识别失败")
        msg.setText(f"OCR 识别出错：{error_msg}")
        msg.setInformativeText("请选择重试截图或手动输入。")
        btn_retry = msg.addButton("重试截图", QMessageBox.ButtonRole.AcceptRole)
        btn_manual = msg.addButton("手动输入", QMessageBox.ButtonRole.ActionRole)
        btn_cancel = msg.addButton("取消", QMessageBox.ButtonRole.RejectRole)
        msg.exec()

        clicked = msg.clickedButton()
        if clicked == btn_retry:
            self.start_screenshot()
        elif clicked == btn_manual:
            self._show_manual_input(pixmap)

    def _handle_ocr_empty(self, pixmap: QPixmap):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("未识别到文字")
        msg.setText("OCR 未识别到任何文字内容。")
        msg.setInformativeText("请确保截图包含订单表格信息，或手动输入。")
        btn_retry = msg.addButton("重试截图", QMessageBox.ButtonRole.AcceptRole)
        btn_manual = msg.addButton("手动输入", QMessageBox.ButtonRole.ActionRole)
        btn_cancel = msg.addButton("取消", QMessageBox.ButtonRole.RejectRole)
        msg.exec()

        clicked = msg.clickedButton()
        if clicked == btn_retry:
            self.start_screenshot()
        elif clicked == btn_manual:
            self._show_manual_input(pixmap)

    def _handle_extract_failure(self, raw_text: str, pixmap: QPixmap):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("信息提取失败")
        msg.setText("未能从截图中提取到订单号和基因名。")
        msg.setInformativeText(f"识别文本:\n{raw_text[:300]}\n\n请手动输入或重试。")
        btn_retry = msg.addButton("重试截图", QMessageBox.ButtonRole.AcceptRole)
        btn_manual = msg.addButton("手动输入", QMessageBox.ButtonRole.ActionRole)
        btn_cancel = msg.addButton("取消", QMessageBox.ButtonRole.RejectRole)
        msg.exec()

        clicked = msg.clickedButton()
        if clicked == btn_retry:
            self.start_screenshot()
        elif clicked == btn_manual:
            self._show_manual_input(pixmap)

    # ── 生命周期 ──────────────────────────────────────────────

    def run(self):
        self.app.exec()

    def quit(self):
        try:
            import keyboard
            keyboard.unhook_all()
        except Exception:
            pass
        self._cleanup_overlay()
        self.app.quit()


def main():
    app = GeneSnapApp()
    app.run()


if __name__ == "__main__":
    main()
