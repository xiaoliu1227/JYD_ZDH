from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTableWidget, QPushButton, QLineEdit, QLabel, QTextEdit,
    QHeaderView, QComboBox, QListWidget, QAbstractItemView, QGroupBox, QGridLayout, QSplitter
)
from PyQt5.QtCore import Qt


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setWindowTitle("自动化任务执行器 (流程序列编排版)")
        MainWindow.setGeometry(100, 100, 1100, 800)  # 增大窗口

        self.centralWidget = QWidget(MainWindow)
        MainWindow.setCentralWidget(self.centralWidget)

        self.mainLayout = QVBoxLayout(self.centralWidget)
        self.tabs = QTabWidget(self.centralWidget)
        self.mainLayout.addWidget(self.tabs)

        # --- Tab 1: 自动化运行 (序列编排模式) ---
        self.run_tab = QWidget()
        self.tabs.addTab(self.run_tab, "运行任务")
        self.run_layout = QVBoxLayout(self.run_tab)

        # 1. 当前运行账号/SKU区域 (保持不变)
        self.active_group = QGroupBox("激活的账号/参数")
        self.active_layout = QGridLayout(self.active_group)

        # Row 0: 账号/密码显示
        self.active_layout.addWidget(QLabel("账号:"), 0, 0)
        self.active_user_display = QLineEdit();
        self.active_user_display.setReadOnly(True)
        self.active_layout.addWidget(self.active_user_display, 0, 1)

        self.active_layout.addWidget(QLabel("密码:"), 0, 2)
        self.active_pwd_display = QLineEdit();
        self.active_pwd_display.setReadOnly(True)
        self.active_pwd_display.setEchoMode(QLineEdit.Password)
        self.active_layout.addWidget(self.active_pwd_display, 0, 3)

        # Row 1: SKU 输入框
        self.active_layout.addWidget(QLabel("SKU值:"), 1, 0)
        self.sku_input = QLineEdit()
        self.sku_input.setPlaceholderText("用于 {sku} 变量 (查询流程需要)")
        self.active_layout.addWidget(self.sku_input, 1, 1, 1, 3)  # 跨越三列

        self.run_layout.addWidget(self.active_group)

        # 2. 流程序列编排区域 (核心修改)
        self.sequencer_group = QGroupBox("第二步：流程序列编排")
        self.sequencer_layout = QHBoxLayout(self.sequencer_group)
        self.splitter = QSplitter(Qt.Horizontal)

        # A. 流程池 (左侧)
        self.pool_frame = QGroupBox("流程库 (拖拽源)")
        self.pool_layout = QVBoxLayout(self.pool_frame)
        self.flow_pool_list = QListWidget()  # 所有可用的流程
        self.flow_pool_list.setDragEnabled(True)  # 允许拖拽
        self.flow_pool_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.pool_layout.addWidget(self.flow_pool_list)
        self.splitter.addWidget(self.pool_frame)

        # B. 任务队列 (右侧)
        self.queue_frame = QGroupBox("任务执行队列 (拖拽到此，可重排)")
        self.queue_layout = QVBoxLayout(self.queue_frame)
        self.flow_queue_list = QListWidget()  # 序列列表
        self.flow_queue_list.setAcceptDrops(True)  # 允许拖入
        self.flow_queue_list.setDragDropMode(QAbstractItemView.InternalMove)  # 允许内部重排
        self.queue_layout.addWidget(self.flow_queue_list)

        self.btn_clear_queue = QPushButton("清空队列")
        self.queue_layout.addWidget(self.btn_clear_queue)

        self.splitter.addWidget(self.queue_frame)
        self.sequencer_layout.addWidget(self.splitter)
        self.run_layout.addWidget(self.sequencer_group)

        # 3. 运行按钮 (新的位置)
        self.run_button = QPushButton("开始执行序列任务")
        self.run_button.setFixedHeight(40)
        self.run_layout.addWidget(self.run_button)

        # 4. 账号池管理和日志区域
        self.bottom_splitter = QSplitter(Qt.Horizontal)

        # A. 账号池列表
        self.pool_group = QGroupBox("历史账号池 (点击选择)")
        self.pool_layout_h = QHBoxLayout(self.pool_group)
        self.account_pool_list = QListWidget()
        self.account_pool_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.pool_layout_h.addWidget(self.account_pool_list)

        # B. 新增/删除管理区域 (和之前一样)
        self.mgmt_group = QGroupBox("新增/删除管理")
        self.mgmt_layout = QVBoxLayout(self.mgmt_group)
        self.mgmt_layout.addWidget(QLabel("新/目标账号备注:"));
        self.acc_alias = QLineEdit();
        self.acc_alias.setPlaceholderText("账号备注 (必填)");
        self.mgmt_layout.addWidget(self.acc_alias)
        self.mgmt_layout.addWidget(QLabel("账号:"));
        self.acc_user = QLineEdit();
        self.acc_user.setPlaceholderText("User");
        self.mgmt_layout.addWidget(self.acc_user)
        self.mgmt_layout.addWidget(QLabel("密码:"));
        self.acc_pwd = QLineEdit();
        self.acc_pwd.setEchoMode(QLineEdit.Password);
        self.mgmt_layout.addWidget(self.acc_pwd)
        self.btn_add_acc = QPushButton("保存/更新账号");
        self.mgmt_layout.addWidget(self.btn_add_acc)
        self.btn_del_acc = QPushButton("删除选中账号");
        self.mgmt_layout.addWidget(self.btn_del_acc)

        self.pool_layout_h.addWidget(self.mgmt_group)
        self.bottom_splitter.addWidget(self.pool_group)

        # C. 日志区域
        self.log_group = QGroupBox("执行日志")
        self.log_layout = QVBoxLayout(self.log_group)
        self.log_output = QTextEdit();
        self.log_output.setReadOnly(True)
        self.log_layout.addWidget(self.log_output)
        self.bottom_splitter.addWidget(self.log_group)

        self.run_layout.addWidget(self.bottom_splitter)

        # --- Tab 2: 元素配置 (保持不变) ---
        self.config_tab = QWidget()
        self.tabs.addTab(self.config_tab, "元素定位配置")
        self.config_tab_layout = QVBoxLayout(self.config_tab)

        self.instructions = QTextEdit()
        self.instructions.setReadOnly(True)
        self.instructions.setFixedHeight(80)
        self.instructions.setHtml(
            "<b>智能定位指南:</b><br>"
            "1. <code>//div[@id='root']</code> 或 <code>.my-class</code> (直接 XPath/CSS)<br>"
            "2. <code>placeholder=\"请输入\"</code> (自动识别属性)<br>"
            "3. <code>&lt;span&gt;登录</code> (标签+文本)<br>"
            "4. <code>登录</code> (纯文本)"
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