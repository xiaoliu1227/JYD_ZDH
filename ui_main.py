from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTableWidget, QPushButton, QLineEdit, QLabel, QTextEdit,
    QHeaderView, QComboBox, QListWidget, QAbstractItemView, QGroupBox, QGridLayout
)
from PyQt5.QtCore import Qt


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setWindowTitle("自动化任务执行器 (单选模式)")
        MainWindow.setGeometry(100, 100, 950, 750)

        self.centralWidget = QWidget(MainWindow)
        MainWindow.setCentralWidget(self.centralWidget)

        self.mainLayout = QVBoxLayout(self.centralWidget)
        self.tabs = QTabWidget(self.centralWidget)
        self.mainLayout.addWidget(self.tabs)

        # --- Tab 1: 自动化运行 ---
        self.run_tab = QWidget()
        self.tabs.addTab(self.run_tab, "运行任务")
        self.run_layout = QVBoxLayout(self.run_tab)

        # 1. 当前运行账号显示区域 (Active Selection Display)
        self.active_group = QGroupBox("当前运行账号 (点击列表选择)")
        self.active_layout = QGridLayout(self.active_group)

        self.active_layout.addWidget(QLabel("账号:"), 0, 0)
        self.active_user_display = QLineEdit();
        self.active_user_display.setReadOnly(True)
        self.active_layout.addWidget(self.active_user_display, 0, 1)

        self.active_layout.addWidget(QLabel("密码:"), 0, 2)
        self.active_pwd_display = QLineEdit();
        self.active_pwd_display.setReadOnly(True)
        self.active_pwd_display.setEchoMode(QLineEdit.Password)
        self.active_layout.addWidget(self.active_pwd_display, 0, 3)

        self.active_layout.addWidget(QLabel("流程:"), 1, 0)
        self.workflow_combo = QComboBox()
        self.active_layout.addWidget(self.workflow_combo, 1, 1, 1, 3)  # 跨越三列

        self.run_button = QPushButton("开始执行选中账号")
        self.active_layout.addWidget(self.run_button, 2, 0, 1, 4)
        self.run_layout.addWidget(self.active_group)

        # 2. 账号池列表 (Selection List)
        self.pool_group = QGroupBox("历史账号池 (点击选择)")
        self.pool_layout = QHBoxLayout(self.pool_group)

        self.account_pool_list = QListWidget()
        self.account_pool_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.pool_layout.addWidget(self.account_pool_list)

        # 3. 新增/删除管理区域
        self.mgmt_group = QGroupBox("新增/删除管理")
        self.mgmt_layout = QVBoxLayout(self.mgmt_group)

        self.mgmt_layout.addWidget(QLabel("新/目标账号备注:"))
        self.acc_alias = QLineEdit();
        self.acc_alias.setPlaceholderText("账号备注 (必填)")
        self.mgmt_layout.addWidget(self.acc_alias)

        self.mgmt_layout.addWidget(QLabel("账号:"))
        self.acc_user = QLineEdit();
        self.acc_user.setPlaceholderText("User")
        self.mgmt_layout.addWidget(self.acc_user)

        self.mgmt_layout.addWidget(QLabel("密码:"))
        self.acc_pwd = QLineEdit();
        self.acc_pwd.setEchoMode(QLineEdit.Password)
        self.mgmt_layout.addWidget(self.acc_pwd)

        self.btn_add_acc = QPushButton("保存/更新账号")
        self.mgmt_layout.addWidget(self.btn_add_acc)

        self.btn_del_acc = QPushButton("删除选中账号")
        self.mgmt_layout.addWidget(self.btn_del_acc)

        self.pool_layout.addWidget(self.mgmt_group)
        self.run_layout.addWidget(self.pool_group)

        # 4. 日志
        self.run_layout.addWidget(QLabel("执行日志:"))
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.run_layout.addWidget(self.log_output)

        # --- Tab 2: 元素配置 (保持不变) ---
        self.config_tab = QWidget()
        self.tabs.addTab(self.config_tab, "元素定位配置")
        self.config_tab_layout = QVBoxLayout(self.config_tab)

        self.instructions = QTextEdit()
        self.instructions.setReadOnly(True)
        self.instructions.setFixedHeight(80)
        self.instructions.setHtml(
            "<b>智能定位指南:</b><br>"
            "1. <code>placeholder=\"请输入\"</code> (自动识别属性)<br>"
            "2. <code>&lt;span&gt;登录</code> (标签+文本)<br>"
            "3. <code>登录</code> (纯文本)"
        )
        self.config_tab_layout.addWidget(self.instructions)

        self.elements_table = QTableWidget()
        self.elements_table.setColumnCount(3)
        self.elements_table.setHorizontalHeaderLabels(["Key", "描述", "智能定位值 (Value)"])
        self.elements_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.elements_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.config_tab_layout.addWidget(self.elements_table)

        self.save_button = QPushButton("保存元素配置")
        self.config_tab_layout.addWidget(self.save_button)