import sys
import os
import openpyxl
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTabWidget, QFormLayout, QScrollArea, QComboBox,
                             QLineEdit, QPushButton, QLabel, QGroupBox, QMessageBox,
                             QTextEdit, QCheckBox, QFileDialog, QTreeWidget, QTreeWidgetItem, QHeaderView)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QIntValidator, QColor, QBrush, QFont

from config_manager import config_manager
from 产品自动刊登.debug_tool import ListingWorker


class ListingToolUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ERP 全站结构校验工具 v3.1 (层级视图版)")
        self.setGeometry(200, 100, 1200, 850)  # 窗口加宽，适应树形列表
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

        # --- 1. 账号管理区 ---
        layout.addRow(QLabel("<b>[1] 账号选择</b>"))

        acc_scroll = QScrollArea()
        acc_box = QWidget()
        self.acc_layout = QHBoxLayout(acc_box)
        self.acc_layout.setAlignment(Qt.AlignLeft)
        acc_scroll.setWidget(acc_box)
        acc_scroll.setWidgetResizable(True)
        acc_scroll.setFixedHeight(60)
        layout.addRow(acc_scroll)

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

        btn_save_acc = QPushButton("保存/更新账号")
        btn_save_acc.clicked.connect(self.save_account)
        btn_del_acc = QPushButton("删除账号")
        btn_del_acc.clicked.connect(self.del_account)
        sub_layout.addWidget(btn_save_acc)
        sub_layout.addWidget(btn_del_acc)
        layout.addRow(sub_layout)

        layout.addRow(QLabel("<hr>"))

        # --- 2. 参数设置区 ---
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

        # --- 3. 核心控制区 ---
        ctl_box = QHBoxLayout()

        self.btn_run = QPushButton("🚀 启动全站校验")
        self.btn_run.setFixedHeight(45)
        self.btn_run.setStyleSheet("font-size: 14px; font-weight: bold; background-color: #0078d7; color: white;")
        self.btn_run.clicked.connect(self.toggle_run)

        self.btn_pause = QPushButton("⏸ 暂停")
        self.btn_pause.setFixedHeight(45)
        self.btn_pause.setStyleSheet("font-size: 14px; font-weight: bold; background-color: #fbbc05; color: black;")
        self.btn_pause.setEnabled(False)
        self.btn_pause.clicked.connect(self.manual_pause)

        self.btn_stop = QPushButton("🛑 停止")
        self.btn_stop.setFixedHeight(45)
        self.btn_stop.setStyleSheet("font-size: 14px; font-weight: bold; background-color: #d93025; color: white;")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_task)

        ctl_box.addWidget(self.btn_run)
        ctl_box.addWidget(self.btn_pause)
        ctl_box.addWidget(self.btn_stop)
        layout.addRow(ctl_box)

        # --- 日志 ---
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("background-color: #f8f9fa; border: 1px solid #ccc; font-family: Consolas;")
        layout.addRow(self.log_view)

        self.refresh_acc_ui()

    # ========================================================
    # 🌟 [重构] 元素配置页 - 使用 QTreeWidget 实现层级嵌套
    # ========================================================
    def create_cfg_page(self):
        page = QWidget()
        self.tabs.addTab(page, "⚙️ 元素配置 (层级视图)")
        main = QVBoxLayout(page)

        # 顶部提示
        tip_label = QLabel("<b>提示：元素按模块层级显示。父级元素通常在上层。修改后点击底部【保存配置】。</b>")
        tip_label.setStyleSheet("color: #666; margin-bottom: 5px;")
        main.addWidget(tip_label)

        # --- 创建树形控件 ---
        self.tree = QTreeWidget()
        self.tree.setColumnCount(5)
        self.tree.setHeaderLabels(["模块/元素名称", "定位符 (XPath / CSS)", "Index", "超时(s)", "缓冲(s)"])

        # 设置列宽比例
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 名称列自适应
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Locator列拉伸
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        self.tree.setAlternatingRowColors(True)  # 交替行颜色
        self.tree.setStyleSheet("""
            QTreeWidget { font-size: 13px; }
            QTreeWidget::item { height: 32px; padding: 2px; }
            QLineEdit { border: 1px solid #ccc; border-radius: 2px; padding: 2px; background: white; }
            QLineEdit:focus { border: 1px solid #0078d7; }
        """)

        self.element_widgets = {}

        # --- 填充数据 ---
        for mod in self.element_config:
            # 1. 创建一级节点 (模块)
            module_item = QTreeWidgetItem([mod.get("module", "未命名模块")])
            # 设置模块样式 (加粗, 灰色背景)
            font = QFont()
            font.setBold(True)
            module_item.setFont(0, font)
            module_item.setBackground(0, QBrush(QColor("#e0e0e0")))
            module_item.setBackground(1, QBrush(QColor("#e0e0e0")))
            module_item.setBackground(2, QBrush(QColor("#e0e0e0")))
            module_item.setBackground(3, QBrush(QColor("#e0e0e0")))
            module_item.setBackground(4, QBrush(QColor("#e0e0e0")))

            self.tree.addTopLevelItem(module_item)
            module_item.setExpanded(True)  # 默认展开

            # 2. 创建二级节点 (元素)
            for ele in mod.get("elements", []):
                name = ele["name"]
                child_item = QTreeWidgetItem([name])
                module_item.addChild(child_item)

                # 创建嵌入的输入框控件
                # Locator
                loc_edit = QLineEdit(ele["locator"])
                loc_edit.setPlaceholderText("//xpath 或 .class")

                # Index
                idx_edit = QLineEdit(str(ele.get("index", "1")))
                idx_edit.setFixedWidth(40)
                idx_edit.setAlignment(Qt.AlignCenter)

                # Timeout
                to_edit = QLineEdit(str(ele.get("timeout", "10")))
                to_edit.setFixedWidth(50)
                to_edit.setAlignment(Qt.AlignCenter)
                to_edit.setValidator(QIntValidator(1, 300))

                # Rest
                rst_edit = QLineEdit(str(ele.get("rest", "2")))
                rst_edit.setFixedWidth(50)
                rst_edit.setAlignment(Qt.AlignCenter)
                rst_edit.setValidator(QIntValidator(0, 60))

                # 将控件放入树的列中
                self.tree.setItemWidget(child_item, 1, loc_edit)
                self.tree.setItemWidget(child_item, 2, idx_edit)
                self.tree.setItemWidget(child_item, 3, to_edit)
                self.tree.setItemWidget(child_item, 4, rst_edit)

                # 保存引用以便保存时获取值
                self.element_widgets[name] = {
                    "locator": loc_edit,
                    "index": idx_edit,
                    "timeout": to_edit,
                    "rest": rst_edit
                }

        main.addWidget(self.tree)

        # 保存按钮
        btn_save = QPushButton("💾 保存当前配置")
        btn_save.setFixedHeight(40)
        btn_save.setStyleSheet("font-weight: bold; font-size: 14px;")
        btn_save.clicked.connect(self.save_global_config)
        main.addWidget(btn_save)

    # --- 逻辑处理 ---

    def toggle_run(self):
        # --- 1. 恢复逻辑 (Resume) ---
        if self.is_paused_state:
            self.log("🔄 正在应用新配置并恢复...", "blue")
            self.save_global_config(silent=True)
            cfg = config_manager.config_data
            cfg.update(self._get_runtime_params())

            if self.worker:
                # [兼容性修改] 尝试调用 resume_work，如果新 worker 没实现该方法则不报错
                try:
                    if hasattr(self.worker, 'resume_work'):
                        self.worker.resume_work(cfg)
                    else:
                        self.log("⚠️ 当前核心模块暂不支持热更新配置，将继续运行...", "orange")
                except Exception as e:
                    self.log(f"恢复失败: {e}", "red")

            self.btn_run.setText("⏳ 运行中...")
            self.btn_run.setEnabled(False)
            self.btn_pause.setEnabled(True)
            self.btn_stop.setEnabled(True)
            self.is_paused_state = False
            return

        # --- 2. 启动逻辑 (Start) ---
        if not self.acc_user.text():
            return QMessageBox.warning(self, "提示", "请选择或输入一个账号！")

        excel_path = self.file_input.text()
        skus = self.read_skus(excel_path)
        if not skus:
            return QMessageBox.warning(self, "提示", "SKU 列表为空或文件无法读取")

        self.save_global_config(silent=True)
        cfg = config_manager.config_data
        cfg.update(self._get_runtime_params())

        # [关键修改] 在创建新线程前，必须彻底清理旧线程！
        # 这一步是解决 0xC0000409 闪退的核心
        if self.worker is not None:
            try:
                if self.worker.isRunning():
                    self.worker.stop()
                    self.worker.wait()  # 等待线程完全退出
                self.worker.deleteLater()  # 标记对象待删除
            except Exception as e:
                print(f"清理旧线程出错: {e}")
            self.worker = None

        # 创建新 Worker (注意: 这里的 ListingWorker 必须来自 main_worker.py)
        self.worker = ListingWorker(cfg, self.headless_chk.isChecked(), skus, excel_path=excel_path)

        # 连接信号
        self.worker.log_signal.connect(self.log)
        self.worker.finished_signal.connect(self.on_worker_finished)
        self.worker.error_signal.connect(self.on_worker_error)

        # [兼容性修改] 新版 main_worker 可能还没定义 pause_required_signal
        # 先尝试连接，如果报错则忽略，防止因信号缺失导致闪退
        if hasattr(self.worker, 'pause_required_signal'):
            self.worker.pause_required_signal.connect(self.on_pause_required)

        # 启动线程
        self.worker.start()

        # 更新 UI 状态
        self.btn_run.setText("⏳ 运行中...")
        self.btn_run.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_stop.setEnabled(True)

    def manual_pause(self):
        if self.worker and self.worker.isRunning():
            self.worker.request_manual_pause()
            self.btn_pause.setEnabled(False)
            self.btn_run.setText("⏸ 暂停中...")
            self.log("⏸️ 发送暂停请求...", "orange")

    def on_pause_required(self, reason):
        self.is_paused_state = True
        self.btn_run.setText("▶️ 保存配置并重试当前SKU")
        self.btn_run.setEnabled(True)
        self.btn_run.setStyleSheet("font-size: 14px; font-weight: bold; background-color: #34a853; color: white;")
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(True)

        self.log(f"⚠️ 暂停: {reason}", "red")
        self.log("👉 请去【元素配置】页修正Locator或时间，保存后点击绿色按钮继续。", "black")

    def stop_task(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.btn_stop.setEnabled(False)
            self.log("🛑 正在停止任务，请稍候...", "orange")

    def on_worker_finished(self):
        self.btn_run.setText("🚀 启动全站校验")
        self.btn_run.setEnabled(True)
        self.btn_run.setStyleSheet("font-size: 14px; font-weight: bold; background-color: #0078d7; color: white;")
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.is_paused_state = False
        self.log("🛑 任务已完全停止", "red")

    def on_worker_error(self, msg):
        self.log(f"❌ 错误: {msg}", "red")
        self.on_worker_finished()

    def _get_runtime_params(self):
        return {
            'USERNAME': self.acc_user.text(),
            'PASSWORD': self.acc_pass.text(),
            'ACCOUNT_NAME': self.acc_name.text(),
            'TEXT_SOURCE': self.text_source_combo.currentText(),
            'LOGIN_URL': self.url_input.text(),
            'ORG_CODE': self.org_input.text()
        }

    def refresh_acc_ui(self):
        while self.acc_layout.count():
            item = self.acc_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        for acc in self.all_accounts:
            btn = QPushButton(acc["name"])
            btn.setStyleSheet("background-color: #e1f5fe; border: 1px solid #81d4fa; border-radius: 4px; padding: 4px;")
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
        new_acc = {"name": name, "username": self.acc_user.text(), "password": self.acc_pass.text()}
        found = False
        for i, acc in enumerate(self.all_accounts):
            if acc["name"] == name:
                self.all_accounts[i] = new_acc;
                found = True;
                break
        if not found: self.all_accounts.append(new_acc)
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

    def select_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Excel", "", "Excel (*.xlsx)")
        if path: self.file_input.setText(path)

    def read_skus(self, path):
        if not path or not os.path.exists(path): return []
        try:
            wb = openpyxl.load_workbook(path)
            return [str(r[0]).strip() for r in wb.active.iter_rows(min_row=2, values_only=True) if r[0]]
        except Exception as e:
            self.log(f"Excel读取错误: {e}", "red")
            return []

    def save_global_config(self, silent=False):
        new_ele_config = []
        for mod in self.element_config:
            new_mod = {"module": mod["module"], "elements": []}
            for ele in mod["elements"]:
                w = self.element_widgets.get(ele["name"])
                if w:
                    ele["locator"] = w["locator"].text()
                    ele["index"] = w["index"].text()
                    ele["timeout"] = int(w["timeout"].text() or 10)
                    ele["rest"] = int(w["rest"].text() or 2)
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
        vb = self.log_view.verticalScrollBar()
        vb.setValue(vb.maximum())

    def closeEvent(self, e):
        if self.worker: self.worker.stop(); self.worker.wait()
        e.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ListingToolUI()
    window.show()
    sys.exit(app.exec_())