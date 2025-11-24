import sys
import os
import openpyxl
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTabWidget, QFormLayout, QScrollArea, QComboBox,
                             QLineEdit, QPushButton, QLabel, QGroupBox, QMessageBox,
                             QTextEdit, QCheckBox, QFileDialog)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QIntValidator

from config_manager import config_manager
from edge_listing_tool import ListingWorker


class ListingToolUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ERP 全站结构校验工具 v2.2 (UI修复版)")
        self.setGeometry(200, 100, 1000, 800)
        self.config_settings = QSettings('MyCompany', 'ListingTool')

        self.all_accounts = []
        self.element_config = []
        self.worker = None
        self.is_paused_state = False

        self.element_widgets = {}

        self.load_config_data()
        self.init_ui()

    def load_config_data(self):
        config = config_manager.load_config()
        self.all_accounts = config.get("ACCOUNTS", [])
        self.element_config = config.get("ELEMENT_CONFIG", [])

        self.saved_url = self.config_settings.value('url', config.get("LOGIN_URL"))
        self.saved_org = self.config_settings.value('org_code', config.get("ORG_CODE"))
        self.saved_sku_path = self.config_settings.value('sku_path', '')
        self.saved_last_acc = self.config_settings.value('last_acc', '')

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout(self.central_widget)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.create_op_page()
        self.create_cfg_page()

    def create_op_page(self):
        page = QWidget()
        self.tabs.addTab(page, "🏠 运行控制")
        layout = QFormLayout(page)

        # --- 5. 账号管理区 (恢复) ---
        layout.addRow(QLabel("<b>[1] 账号选择</b>"))

        # 账号列表 (滚动区)
        acc_scroll = QScrollArea()
        acc_box = QWidget()
        self.acc_layout = QHBoxLayout(acc_box)
        self.acc_layout.setAlignment(Qt.AlignLeft)
        acc_scroll.setWidget(acc_box)
        acc_scroll.setWidgetResizable(True)
        acc_scroll.setFixedHeight(60)
        layout.addRow(acc_scroll)

        # 账号编辑输入框
        self.acc_name = QLineEdit()
        self.acc_name.setPlaceholderText("备注名 (如: 店铺A)")
        self.acc_user = QLineEdit()
        self.acc_user.setPlaceholderText("登录账号")
        self.acc_pass = QLineEdit()
        self.acc_pass.setEchoMode(QLineEdit.Password)
        self.acc_pass.setPlaceholderText("登录密码")

        sub_layout = QHBoxLayout()
        sub_layout.addWidget(QLabel("备注:"))
        sub_layout.addWidget(self.acc_name)
        sub_layout.addWidget(QLabel("账号:"))
        sub_layout.addWidget(self.acc_user)
        sub_layout.addWidget(QLabel("密码:"))
        sub_layout.addWidget(self.acc_pass)

        # 增删按钮
        btn_save_acc = QPushButton("保存/更新账号")
        btn_save_acc.clicked.connect(self.save_account)
        btn_del_acc = QPushButton("删除账号")
        btn_del_acc.clicked.connect(self.del_account)
        sub_layout.addWidget(btn_save_acc)
        sub_layout.addWidget(btn_del_acc)
        layout.addRow(sub_layout)

        layout.addRow(QLabel("<hr>"))

        # --- 参数设置区 ---
        layout.addRow(QLabel("<b>[2] 运行参数</b>"))

        file_box = QHBoxLayout()
        self.file_input = QLineEdit(self.saved_sku_path)
        btn_file = QPushButton("📂 选择 SKU Excel")
        btn_file.clicked.connect(self.select_file)
        file_box.addWidget(self.file_input)
        file_box.addWidget(btn_file)
        layout.addRow("SKU 列表:", file_box)

        self.text_source_combo = QComboBox()
        self.text_source_combo.addItems(["网页AI生成", "跳过文案"])
        layout.addRow("文案来源:", self.text_source_combo)

        self.url_input = QLineEdit(self.saved_url)
        self.org_input = QLineEdit(self.saved_org)
        self.headless_chk = QCheckBox("后台静默运行")
        layout.addRow("URL:", self.url_input)
        layout.addRow("组织:", self.org_input)
        layout.addRow("", self.headless_chk)

        layout.addRow(QLabel("<hr>"))

        # --- 核心控制区 (恢复停止按钮) ---
        ctl_box = QHBoxLayout()

        self.btn_run = QPushButton("🚀 启动全站校验")
        self.btn_run.setFixedHeight(45)
        self.btn_run.setStyleSheet("font-size: 15px; font-weight: bold; background-color: #0078d7; color: white;")
        self.btn_run.clicked.connect(self.toggle_run)

        self.btn_stop = QPushButton("🛑 停止")
        self.btn_stop.setFixedHeight(45)
        self.btn_stop.setStyleSheet("font-size: 15px; font-weight: bold; background-color: #d93025; color: white;")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_task)

        ctl_box.addWidget(self.btn_run)
        ctl_box.addWidget(self.btn_stop)
        layout.addRow(ctl_box)

        # --- 日志 ---
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("background-color: #f8f9fa; border: 1px solid #ccc;")
        layout.addRow(self.log_view)

        # 初始化显示账号列表
        self.refresh_acc_ui()

    def create_cfg_page(self):
        page = QWidget()
        self.tabs.addTab(page, "⚙️ 元素配置 (内部元素)")
        main = QVBoxLayout(page)
        main.addWidget(QLabel("提示：这里只显示模块内部的元素。模块容器本身的定位逻辑已在代码中硬编码。"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        cont = QWidget()
        form_layout = QVBoxLayout(cont)
        self.element_widgets = {}

        for mod in self.element_config:
            box = QGroupBox(mod.get("module", "模块"))
            fl = QFormLayout(box)
            for ele in mod.get("elements", []):
                name = ele["name"]
                row = QHBoxLayout()
                loc = QLineEdit(ele["locator"])
                idx = QLineEdit(str(ele.get("index", "1")))
                idx.setFixedWidth(30)
                row.addWidget(loc)
                row.addWidget(QLabel("#"))
                row.addWidget(idx)
                fl.addRow(name, row)
                self.element_widgets[name] = {"locator": loc, "index": idx}
            form_layout.addWidget(box)

        form_layout.addStretch()
        scroll.setWidget(cont)
        main.addWidget(scroll)

        btn_save = QPushButton("💾 保存内部元素配置")
        btn_save.clicked.connect(self.save_global_config)
        main.addWidget(btn_save)

    # --- 逻辑处理 ---

    def toggle_run(self):
        if self.is_paused_state:
            # 恢复逻辑
            self.save_global_config(silent=True)
            cfg = config_manager.config_data
            cfg.update(self._get_runtime_params())

            self.worker.resume_work(cfg)

            self.btn_run.setText("运行中...")
            self.btn_run.setEnabled(False)
            self.btn_stop.setEnabled(True)
            self.is_paused_state = False
            return

        # 启动逻辑
        if not self.acc_user.text():
            return QMessageBox.warning(self, "提示", "请选择或输入一个账号！")

        skus = self.read_skus(self.file_input.text())
        if not skus:
            return QMessageBox.warning(self, "提示", "SKU 列表为空或文件无法读取")

        self.save_global_config(silent=True)
        cfg = config_manager.config_data
        cfg.update(self._get_runtime_params())

        self.worker = ListingWorker(cfg, self.headless_chk.isChecked(), skus)
        self.worker.log_signal.connect(self.log)
        self.worker.finished_signal.connect(self.on_worker_finished)
        self.worker.error_signal.connect(self.on_worker_error)
        self.worker.pause_required_signal.connect(self.on_pause)
        self.worker.start()

        self.btn_run.setText("⏳ 运行中...")
        self.btn_run.setEnabled(False)
        self.btn_stop.setEnabled(True)

    def stop_task(self):
        if self.worker:
            self.worker.stop()
            self.worker.wait()
        self.on_worker_finished()
        self.log("🛑 任务已手动停止", "red")

    def on_pause(self, reason):
        self.is_paused_state = True
        self.btn_run.setEnabled(True)
        self.btn_run.setText("▶️ 保存配置并继续")
        self.btn_stop.setEnabled(True)
        QMessageBox.warning(self, "暂停", f"需要人工介入：{reason}")

    def on_worker_finished(self):
        self.btn_run.setText("🚀 启动全站校验")
        self.btn_run.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.is_paused_state = False

    def on_worker_error(self, msg):
        self.on_worker_finished()
        # QMessageBox.critical(self, "错误", msg) # 可选：弹窗提示错误

    def _get_runtime_params(self):
        return {
            'USERNAME': self.acc_user.text(),
            'PASSWORD': self.acc_pass.text(),
            'ACCOUNT_NAME': self.acc_name.text(),
            'TEXT_SOURCE': self.text_source_combo.currentText(),
            'LOGIN_URL': self.url_input.text(),
            'ORG_CODE': self.org_input.text()
        }

    # --- 账号管理逻辑 (恢复) ---

    def refresh_acc_ui(self):
        # 清除旧按钮
        while self.acc_layout.count():
            item = self.acc_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        for acc in self.all_accounts:
            btn = QPushButton(acc["name"])
            btn.setFlat(False)
            btn.setStyleSheet("""
                QPushButton { background-color: #e1f5fe; border: 1px solid #81d4fa; padding: 4px; border-radius: 4px; }
                QPushButton:hover { background-color: #b3e5fc; }
            """)
            btn.clicked.connect(lambda _, a=acc: self.load_account_to_ui(a))
            self.acc_layout.addWidget(btn)

    def load_account_to_ui(self, acc):
        self.acc_name.setText(acc["name"])
        self.acc_user.setText(acc["username"])
        self.acc_pass.setText(acc["password"])
        self.config_settings.setValue('last_acc', acc["name"])

    def save_account(self):
        name = self.acc_name.text()
        if not name: return
        new_acc = {
            "name": name,
            "username": self.acc_user.text(),
            "password": self.acc_pass.text()
        }

        found = False
        for i, acc in enumerate(self.all_accounts):
            if acc["name"] == name:
                self.all_accounts[i] = new_acc
                found = True
                break
        if not found:
            self.all_accounts.append(new_acc)

        self.save_global_config(silent=True)
        self.refresh_acc_ui()
        self.log(f"✅ 账号 [{name}] 已保存", "green")

    def del_account(self):
        name = self.acc_name.text()
        self.all_accounts = [a for a in self.all_accounts if a["name"] != name]
        self.save_global_config(silent=True)
        self.refresh_acc_ui()
        self.acc_name.clear();
        self.acc_user.clear();
        self.acc_pass.clear()

    # --- 文件与保存 ---

    def select_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Excel", "", "Excel (*.xlsx)")
        if path: self.file_input.setText(path)

    def read_skus(self, path):
        if not path or not os.path.exists(path): return []
        try:
            wb = openpyxl.load_workbook(path)
            return [str(r[0]).strip() for r in wb.active.iter_rows(min_row=2, values_only=True) if r[0]]
        except Exception as e:
            self.log(f"读取 Excel 失败: {e}", "red")
            return []

    def save_global_config(self, silent=False):
        # 收集元素配置
        new_ele_config = []
        for mod in self.element_config:
            new_mod = {"module": mod["module"], "elements": []}
            for ele in mod["elements"]:
                w = self.element_widgets.get(ele["name"])
                if w:
                    ele["locator"] = w["locator"].text()
                    ele["index"] = w["index"].text()
                new_mod["elements"].append(ele)
            new_ele_config.append(new_mod)

        data = {
            "LOGIN_URL": self.url_input.text(),
            "ORG_CODE": self.org_input.text(),
            "ACCOUNTS": self.all_accounts,
            "ELEMENT_CONFIG": new_ele_config
        }

        if config_manager.save_config(data):
            self.config_settings.setValue('url', self.url_input.text())
            self.config_settings.setValue('org_code', self.org_input.text())
            if not silent: QMessageBox.information(self, "成功", "配置已保存！")
        else:
            if not silent: QMessageBox.warning(self, "错误", "配置文件保存失败！")

    def log(self, msg, color="black"):
        self.log_view.append(f"<font color='{color}'>{msg}</font>")
        # 自动滚动
        vb = self.log_view.verticalScrollBar()
        vb.setValue(vb.maximum())

    def closeEvent(self, e):
        if self.worker: self.worker.stop()
        e.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ListingToolUI()
    window.show()
    sys.exit(app.exec_())