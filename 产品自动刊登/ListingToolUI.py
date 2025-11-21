import sys
import os
import openpyxl
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTabWidget, QFormLayout, QScrollArea, QComboBox,
                             QLineEdit, QPushButton, QLabel, QGroupBox, QMessageBox,
                             QTextEdit, QCheckBox, QFileDialog)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QTextCharFormat, QIntValidator, QTextCursor

# 导入配置管理
from config_manager import config_manager
# 导入核心工具 (包含 ListingWorker)
from edge_listing_tool import ListingWorker


class ListingToolUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("产品自动刊登工具 v2.0 (交互调试版)")
        self.setGeometry(200, 100, 950, 850)
        self.config_settings = QSettings('MyCompany', 'ListingTool')

        self.all_accounts = []
        self.element_config = []
        self.element_widgets = {}
        self.worker = None
        self.sku_list = []

        # 【状态标记】是否处于暂停等待修复状态
        self.is_paused_state = False

        # 初始化运行时变量，防止 AttributeError
        self.runtime_url = ""
        self.runtime_org = ""
        self.runtime_headless = False
        self.runtime_sku_path = ""
        self.runtime_text_source = "网页AI生成"
        self.runtime_selected_acc = ""

        self.load_config()
        self.init_ui()

    def load_config(self):
        # 从 ConfigManager 加载 (它负责合并逻辑)
        config = config_manager.load_config()
        self.all_accounts = config.get("ACCOUNTS", [])
        self.element_config = config.get("ELEMENT_CONFIG", [])

        # 读取注册表中的 UI 偏好
        self.runtime_url = self.config_settings.value('url', config.get("LOGIN_URL"))
        self.runtime_org = self.config_settings.value('org_code', config.get("ORG_CODE"))
        self.runtime_headless = self.config_settings.value('headless', 'false') == 'true'
        self.runtime_sku_path = self.config_settings.value('sku_path', '')
        self.runtime_text_source = self.config_settings.value('text_source', '网页AI生成')
        self.runtime_selected_acc = self.config_settings.value('last_acc', '')

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
        self.tabs.addTab(page, "操作执行")
        layout = QFormLayout(page)

        # 1. 账号配置
        layout.addRow(QLabel("<b>--- 账号配置 ---</b>"))
        acc_box = QWidget()
        self.acc_layout = QVBoxLayout(acc_box)
        self.acc_layout.setAlignment(Qt.AlignTop)
        scroll = QScrollArea()
        scroll.setWidget(acc_box)
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(100)
        layout.addRow(scroll)

        self.acc_name = QLineEdit()
        self.acc_name.setPlaceholderText("档案名称")
        self.acc_user = QLineEdit()
        self.acc_pass = QLineEdit()
        self.acc_pass.setEchoMode(QLineEdit.Password)
        layout.addRow("名称:", self.acc_name)
        layout.addRow("账号:", self.acc_user)
        layout.addRow("密码:", self.acc_pass)

        btn_box = QHBoxLayout()
        btn_save = QPushButton("保存档案")
        btn_save.clicked.connect(self.save_acc)
        btn_del = QPushButton("删除档案")
        btn_del.clicked.connect(self.del_acc)
        btn_box.addWidget(btn_save)
        btn_box.addWidget(btn_del)
        layout.addRow(btn_box)

        # 2. 任务参数
        layout.addRow(QLabel("<b>--- 任务参数 ---</b>"))
        file_box = QHBoxLayout()
        self.file_input = QLineEdit(self.runtime_sku_path)
        btn_file = QPushButton("选择 SKU 表")
        btn_file.clicked.connect(self.select_file)
        file_box.addWidget(self.file_input)
        file_box.addWidget(btn_file)
        layout.addRow("SKU 文件:", file_box)

        self.text_source_combo = QComboBox()
        self.text_source_combo.addItems(["网页AI生成", "表格获取(暂未开发)"])
        self.text_source_combo.setCurrentText(self.runtime_text_source)
        layout.addRow("文案来源:", self.text_source_combo)

        self.url_input = QLineEdit(self.runtime_url)
        self.org_input = QLineEdit(self.runtime_org)
        self.headless_chk = QCheckBox("后台静默运行")
        self.headless_chk.setChecked(self.runtime_headless)
        layout.addRow("URL:", self.url_input)
        layout.addRow("组织:", self.org_input)
        layout.addRow("", self.headless_chk)

        # 3. 启动控制
        self.btn_run = QPushButton("启动循环刊登")
        self.btn_run.clicked.connect(self.start)
        self.btn_run.setStyleSheet("background-color: #0078D7; color: white; font-weight: bold; height: 45px;")

        self.save_global_btn = QPushButton("保存全局配置")
        self.save_global_btn.clicked.connect(self.save_all)

        ctl_box = QHBoxLayout()
        ctl_box.addWidget(self.save_global_btn)
        ctl_box.addWidget(self.btn_run)
        layout.addRow(ctl_box)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        layout.addRow("日志:", self.log_view)

        self.refresh_acc_list()

    def create_cfg_page(self):
        page = QWidget()
        self.tabs.addTab(page, "元素配置")
        main = QVBoxLayout(page)
        main.addWidget(QLabel("在此处配置 Selenium 元素。<b>遇到抓取失败暂停时，请修改此处并点击【保存配置并继续】。</b>"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        cont = QWidget()
        c_layout = QVBoxLayout(cont)
        self.element_widgets = {}

        # 根据 config_manager 中的结构动态生成配置表单
        for mod in self.element_config:
            box = QGroupBox(mod.get("module", "模块"))
            form = QFormLayout(box)
            for ele in mod.get("elements", []):
                name = ele["name"]
                row_w = QWidget()
                row_l = QHBoxLayout(row_w)
                row_l.setContentsMargins(0, 0, 0, 0)

                loc = QLineEdit(ele["locator"])
                loc.setPlaceholderText("XPath / CSS / ID")

                pos = QComboBox()
                pos.addItems(["当前元素", "父元素", "子元素", "上一个", "下一个"])
                pos.setCurrentText(ele.get("position", "当前元素"))
                pos.setFixedWidth(85)

                idx = QLineEdit(str(ele.get("index", "1")))
                idx.setFixedWidth(30)
                idx.setValidator(QIntValidator(1, 99))

                row_l.addWidget(loc, 3)
                row_l.addWidget(pos, 1)
                row_l.addWidget(idx, 0)

                form.addRow(name, row_w)
                # 保存控件引用，用于 save_all 时读取
                self.element_widgets[name] = {"locator": loc, "position": pos, "index": idx}
            c_layout.addWidget(box)

        c_layout.addStretch()
        scroll.setWidget(cont)
        main.addWidget(scroll)

        btn = QPushButton("保存元素配置")
        btn.clicked.connect(self.save_all)
        main.addWidget(btn)

    def select_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 Excel", "", "Excel Files (*.xlsx)")
        if path: self.file_input.setText(path)

    def read_skus(self, path):
        if not path or not os.path.exists(path): return []
        try:
            wb = openpyxl.load_workbook(path)
            ws = wb.active
            skus = []
            for row in ws.iter_rows(min_row=2, max_col=1, values_only=True):
                if row[0]: skus.append(str(row[0]).strip())
            return skus
        except Exception as e:
            self.log(f"读取 Excel 失败: {e}", "red")
            return []

    def save_all(self):
        """保存所有配置到文件"""
        new_cfg = []
        for mod in self.element_config:
            new_mod = {"module": mod["module"], "elements": []}
            for ele in mod["elements"]:
                name = ele["name"]
                w = self.element_widgets.get(name)
                if w:
                    new_mod["elements"].append({
                        "name": name,
                        "locator": w["locator"].text(),
                        "position": w["position"].currentText(),
                        "index": w["index"].text()
                    })
                else:
                    new_mod["elements"].append(ele)
            new_cfg.append(new_mod)

        data = {
            "LOGIN_URL": self.url_input.text(),
            "ORG_CODE": self.org_input.text(),
            "ACCOUNTS": self.all_accounts,
            "ELEMENT_CONFIG": new_cfg
        }

        if config_manager.save_config(data):
            # 同步更新 UI 缓存
            self.config_settings.setValue('url', self.url_input.text())
            self.config_settings.setValue('org_code', self.org_input.text())
            self.config_settings.setValue('sku_path', self.file_input.text())
            self.config_settings.setValue('text_source', self.text_source_combo.currentText())
            self.config_settings.setValue('headless', str(self.headless_chk.isChecked()).lower())
            return True
        return False

    def start(self):
        """启动或恢复任务"""

        # --- 情况 1: 处于暂停状态 (用户修改配置后点击继续) ---
        if self.is_paused_state:
            self.log("🔄 正在应用新配置并恢复运行...", "blue")

            # 1. 保存当前 UI 上的新 XPath
            if not self.save_all():
                QMessageBox.warning(self, "错误", "保存配置失败，无法继续。")
                return

            # 2. 从 ConfigManager 获取最新完整配置
            latest_config = config_manager.config_data
            # 补全运行时参数 (这些没保存在 json 里)
            latest_config['USERNAME'] = self.acc_user.text()
            latest_config['PASSWORD'] = self.acc_pass.text()
            latest_config['ACCOUNT_NAME'] = self.acc_name.text()
            latest_config['TEXT_SOURCE'] = self.text_source_combo.currentText()

            # 3. 唤醒后台线程
            if self.worker:
                self.worker.resume_work(latest_config)

            # 4. 恢复按钮 UI
            self.btn_run.setText("运行中...")
            self.btn_run.setStyleSheet("background-color: #808080; color: white;")  # 灰色表示运行中
            self.btn_run.setEnabled(False)
            self.is_paused_state = False
            return

        # --- 情况 2: 初始启动 ---
        if not self.save_all(): return

        user = self.acc_user.text()
        pwd = self.acc_pass.text()
        account_name = self.acc_name.text()

        if not user or not pwd: QMessageBox.warning(self, "提示", "请选择账号"); return
        if not account_name: QMessageBox.warning(self, "提示", "档案名称不能为空(用于店铺匹配)"); return

        skus = self.read_skus(self.file_input.text())
        if not skus:
            QMessageBox.warning(self, "提示", "未找到有效 SKU")
            return

        # 准备配置
        conf = config_manager.config_data
        conf['USERNAME'] = user
        conf['PASSWORD'] = pwd
        conf['ACCOUNT_NAME'] = account_name
        conf['TEXT_SOURCE'] = self.text_source_combo.currentText()

        self.btn_run.setEnabled(False)
        self.btn_run.setText("运行中...")
        self.btn_run.setStyleSheet("background-color: #808080; color: white;")
        self.log(f"启动任务，店铺: {account_name}, SKU数: {len(skus)}")

        self.worker = ListingWorker(conf, self.headless_chk.isChecked(), sku_list=skus)

        # 连接信号
        self.worker.log_signal.connect(self.log)
        self.worker.finished_signal.connect(self.on_fin)
        self.worker.error_signal.connect(self.on_error)
        # 【关键】连接暂停请求信号
        self.worker.pause_required_signal.connect(self.on_pause_required)

        self.worker.start()

    # --- 信号槽 ---

    def on_pause_required(self, reason):
        """当后台线程找不到元素时触发"""
        self.is_paused_state = True
        self.btn_run.setEnabled(True)
        self.btn_run.setText("保存配置并继续")
        # 变成醒目的橙色
        self.btn_run.setStyleSheet(
            "background-color: #FF5722; color: white; font-weight: bold; height: 45px; font-size: 14px;")

        self.log(f"⚠️ 任务已暂停！", "red")
        self.log(f"原因: {reason}", "black")
        self.log("👉 请切换到【元素配置】页，修改错误的定位符，然后点击上方【保存配置并继续】。", "blue")

        # 自动跳转到配置页
        self.tabs.setCurrentIndex(1)
        QMessageBox.warning(self, "任务暂停",
                            f"抓取元素失败，程序已暂停等待。\n\n原因：{reason}\n\n请修改配置后点击“保存配置并继续”。")

    def on_fin(self):
        self.btn_run.setEnabled(True)
        self.btn_run.setText("启动循环刊登")
        self.btn_run.setStyleSheet("background-color: #0078D7; color: white; font-weight: bold; height: 45px;")
        self.is_paused_state = False
        self.log("✅ 任务流程全部结束", "blue")

    def on_error(self, msg):
        # 只有致命错误（如浏览器关闭）才会走到这里
        self.btn_run.setEnabled(True)
        self.btn_run.setText("启动循环刊登")
        self.btn_run.setStyleSheet("background-color: #0078D7; color: white; font-weight: bold; height: 45px;")
        self.is_paused_state = False
        self.log(msg, "red")

    # --- 账号管理 ---

    def refresh_acc_list(self):
        for i in reversed(range(self.acc_layout.count())): self.acc_layout.itemAt(i).widget().setParent(None)
        for acc in self.all_accounts:
            btn = QPushButton(acc["name"]);
            btn.clicked.connect(lambda c, a=acc: self.load_acc(a))
            self.acc_layout.addWidget(btn)
        if self.runtime_selected_acc:
            t = next((a for a in self.all_accounts if a["name"] == self.runtime_selected_acc), None)
            if t: self.load_acc(t)

    def load_acc(self, a):
        self.acc_name.setText(a["name"]);
        self.acc_user.setText(a["username"]);
        self.acc_pass.setText(a["password"])
        self.runtime_selected_acc = a["name"];
        self.config_settings.setValue('last_acc', a["name"])

    def save_acc(self):
        n = self.acc_name.text()
        if not n: return
        new = {"name": n, "username": self.acc_user.text(), "password": self.acc_pass.text()}
        f = False
        for i, a in enumerate(self.all_accounts):
            if a["name"] == n: self.all_accounts[i] = new; f = True; break
        if not f: self.all_accounts.append(new)
        self.save_all();
        self.refresh_acc_list();
        self.log(f"档案 {n} 保存")

    def del_acc(self):
        n = self.acc_name.text();
        self.all_accounts = [a for a in self.all_accounts if a["name"] != n]
        self.save_all();
        self.refresh_acc_list();
        self.log(f"档案 {n} 删除")

    def log(self, m, c="black"):
        f = QTextCharFormat();
        f.setForeground(Qt.red if c == "red" else Qt.green if c == "green" else Qt.blue if c == "blue" else Qt.black)
        cur = self.log_view.textCursor();
        cur.movePosition(QTextCursor.End);
        cur.insertText(f"{m}\n", f);
        self.log_view.ensureCursorVisible()


if __name__ == '__main__':
    app = QApplication(sys.argv);
    window = ListingToolUI();
    window.show();
    sys.exit(app.exec_())