"""弹窗 UI：确认/修改识别结果、选择保存位置、手动输入、错误提示"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QRadioButton, QButtonGroup, QPushButton, QMessageBox,
    QGroupBox, QFormLayout,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class ConfirmDialog(QDialog):
    """弹窗①：确认/修改 OCR 识别结果"""

    def __init__(self, order_id: str, gene_name: str, order_type: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("截图识别结果确认")
        self.setMinimumWidth(420)
        self.setModal(True)

        self._result = None  # None=未确认, "retry", "manual", "confirm", "cancel"

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 标题
        title = QLabel("📸 截图识别结果确认")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(13)
        title.setFont(title_font)
        layout.addWidget(title)

        # 表单
        form = QFormLayout()
        form.setSpacing(8)

        self.order_id_edit = QLineEdit(order_id)
        self.order_id_edit.setMinimumHeight(28)
        form.addRow("订单号:", self.order_id_edit)

        self.gene_edit = QLineEdit(gene_name)
        self.gene_edit.setMinimumHeight(28)
        form.addRow("基因名:", self.gene_edit)

        layout.addLayout(form)

        # 类型选择
        type_group = QGroupBox("类型")
        type_layout = QHBoxLayout(type_group)
        self.type_group = QButtonGroup(self)
        self.primer_radio = QRadioButton("引物到货确认 (TSP...)")
        self.seq_radio = QRadioButton("测序确认 (TSS...)")
        self.type_group.addButton(self.primer_radio, 0)
        self.type_group.addButton(self.seq_radio, 1)
        type_layout.addWidget(self.primer_radio)
        type_layout.addWidget(self.seq_radio)

        if order_type == "primer":
            self.primer_radio.setChecked(True)
        else:
            self.seq_radio.setChecked(True)
        layout.addWidget(type_group)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        btn_retry = QPushButton("🔄 重试截图")
        btn_retry.clicked.connect(self._on_retry)
        btn_layout.addWidget(btn_retry)

        btn_manual = QPushButton("✏️ 手动输入")
        btn_manual.clicked.connect(self._on_manual)
        btn_layout.addWidget(btn_manual)

        btn_layout.addStretch()

        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_confirm = QPushButton("确认 ✓")
        btn_confirm.setDefault(True)
        btn_confirm.clicked.connect(self._on_confirm)
        btn_layout.addWidget(btn_confirm)

        layout.addLayout(btn_layout)

    def _on_retry(self):
        self._result = "retry"
        self.accept()

    def _on_manual(self):
        self._result = "manual"
        self.accept()

    def _on_confirm(self):
        oid = self.order_id_edit.text().strip()
        gene = self.gene_edit.text().strip()
        if not oid or not gene:
            QMessageBox.warning(self, "不完整", "订单号和基因名不能为空。")
            return
        self._result = "confirm"
        self.accept()

    @property
    def result_action(self):
        return self._result

    @property
    def order_id(self):
        return self.order_id_edit.text().strip()

    @property
    def gene_name(self):
        return self.gene_edit.text().strip()

    @property
    def order_type(self):
        return "primer" if self.primer_radio.isChecked() else "sequencing"


class ManualInputDialog(QDialog):
    """手动输入弹窗"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("手动输入订单信息")
        self.setMinimumWidth(380)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("✏️ 手动输入订单信息")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(8)
        self.order_id_edit = QLineEdit()
        self.order_id_edit.setPlaceholderText("如 TSP20260421-021-00312")
        form.addRow("订单号:", self.order_id_edit)

        self.gene_edit = QLineEdit()
        self.gene_edit.setPlaceholderText("如 POLR2H")
        form.addRow("基因名:", self.gene_edit)
        layout.addLayout(form)

        type_group = QGroupBox("类型")
        type_layout = QHBoxLayout(type_group)
        self.type_group = QButtonGroup(self)
        self.primer_radio = QRadioButton("引物到货确认")
        self.seq_radio = QRadioButton("测序确认")
        self.type_group.addButton(self.primer_radio, 0)
        self.type_group.addButton(self.seq_radio, 1)
        type_layout.addWidget(self.primer_radio)
        type_layout.addWidget(self.seq_radio)
        self.primer_radio.setChecked(True)
        layout.addWidget(type_group)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        btn_ok = QPushButton("确认")
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self._on_ok)
        btn_layout.addWidget(btn_ok)
        layout.addLayout(btn_layout)

    def _on_ok(self):
        if not self.order_id_edit.text().strip() or not self.gene_edit.text().strip():
            QMessageBox.warning(self, "不完整", "订单号和基因名不能为空。")
            return
        self.accept()

    @property
    def order_id(self):
        return self.order_id_edit.text().strip()

    @property
    def gene_name(self):
        return self.gene_edit.text().strip()

    @property
    def order_type(self):
        return "primer" if self.primer_radio.isChecked() else "sequencing"


class SaveConfirmDialog(QDialog):
    """弹窗②：确认保存位置"""

    def __init__(self, folder_path: str, order_type: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("保存截图")
        self.setMinimumWidth(440)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("💾 保存到哪个文件夹？")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(13)
        title.setFont(title_font)
        layout.addWidget(title)

        # 显示路径
        path_label = QLabel(f"将保存到：\n{folder_path}")
        path_label.setWordWrap(True)
        path_label.setStyleSheet("background: #f0f0f0; padding: 8px; border-radius: 4px;")
        layout.addWidget(path_label)

        # 子文件夹选择
        type_group = QGroupBox("子文件夹")
        type_layout = QHBoxLayout(type_group)
        self.type_group = QButtonGroup(self)
        self.primer_radio = QRadioButton("引物到货确认")
        self.seq_radio = QRadioButton("测序确认")
        self.type_group.addButton(self.primer_radio, 0)
        self.type_group.addButton(self.seq_radio, 1)
        type_layout.addWidget(self.primer_radio)
        type_layout.addWidget(self.seq_radio)

        if order_type == "primer":
            self.primer_radio.setChecked(True)
        else:
            self.seq_radio.setChecked(True)
        layout.addWidget(type_group)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        btn_save = QPushButton("确认保存 💾")
        btn_save.setDefault(True)
        btn_save.clicked.connect(self.accept)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    @property
    def subfolder(self):
        return "引物到货确认" if self.primer_radio.isChecked() else "测序确认"


def show_error(msg: str, parent=None):
    QMessageBox.critical(parent, "错误", msg)


def show_gene_not_found(gene_name: str, parent=None):
    """基因名找不到弹窗，返回用户输入的新基因名或None"""
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Icon.Warning)
    msg.setWindowTitle("基因名未找到")
    msg.setText(f"在项目进度表中未找到基因名「{gene_name}」。")
    msg.setInformativeText("请手动输入正确的基因名，或点取消退出。")

    from PySide6.QtWidgets import QInputDialog
    new_gene, ok = QInputDialog.getText(
        msg, "输入基因名", "正确的基因名:"
    )
    if ok and new_gene.strip():
        return new_gene.strip()
    return None
