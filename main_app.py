import sys
import importlib.util
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableWidgetItem,
                             QMessageBox, QListWidgetItem, QListWidget, QAbstractItemView)
from PyQt5.QtCore import Qt, QMimeData, QByteArray, QDataStream, QIODevice
from PyQt5.QtGui import QDrag

from ui_main import Ui_MainWindow
from config_manager import load_config, save_config
from base_executor import BaseExecutor
from config_manager import PROCESS_MODULES

# 定义流程模块的映射关系。
PROCESS_MODULES = {
    "workflow_full_login": {
        "module": "process_login",
        "class": "LoginProcess",
        "elements": [
            "login_page_username_input", "login_page_password_input", "login_page_login_button",
            "org_popup_dialog", "org_popup_input", "org_popup_list_item", "org_popup_confirm_button",
            "home_page_notification_popup", "home_page_notification_close_button"
        ]
    },
    "workflow_view_product_info": {
        "module": "process_view_product",
        "class": "ViewProductProcess",
        "elements": [
            "nav_product_icon", "nav_product_distribution_list", "product_list_sku_input",
            "product_list_search_button", "product_list_view_detail_button", "detail_popup_dialog",
            "detail_info_table"
        ]
    },
    "workflow_logout": {
        "module": "process_logout",
        "class": "LogoutProcess",
        "elements": ["home_page_logout_button"]
    }
}


# --- 动态导入函数 ---
def load_process_class(module_name, class_name):
    """动态加载流程模块文件，并返回指定的流程类"""
    file_path = f"{module_name}.py"
    if not os.path.exists(file_path):
        QMessageBox.critical(None, "加载流程错误", f"未找到流程文件: {file_path}")
        return None

    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return getattr(module, class_name)
    except Exception as e:
        QMessageBox.critical(None, "加载流程错误", f"无法加载 {module_name}.py 中的 {class_name} 类: {e}")
        return None


# --- QListWidget 扩展 (处理拖拽) ---
# 定义一个全局实例变量，以便在 dropEvent 中访问 MainWindow
class MainWindow(QMainWindow):
    instance = None
    # ... (其余代码) ...


class FlowPoolListWidget(QListWidget):
    """用于流程库，支持拖拽"""

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            item = self.currentItem()
            if item:
                # 使用 item data 存储流程 Key
                flow_key = item.data(Qt.UserRole)

                # 准备 MIME data
                mimeData = QMimeData()
                mimeData.setText(flow_key)

                # 开始拖拽
                drag = QDrag(self)
                drag.setMimeData(mimeData)
                drag.exec_(Qt.CopyAction)
        super().mouseMoveEvent(event)


class FlowQueueListWidget(QListWidget):
    """用于执行队列，支持外部拖入和内部重排"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)  # 允许内部重排

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        # 外部拖入
        flow_key = event.mimeData().text()
        if flow_key and MainWindow.instance:
            # 调用主窗口方法来创建并添加列表项
            text = MainWindow.instance.create_flow_item_text(flow_key)
            if text:
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, flow_key)
                self.addItem(item)
                event.accept()
                return

        # 内部重排
        super().dropEvent(event)


class MainWindow(QMainWindow):
    instance = None  # 静态变量，用于 ListWidget 访问

    def __init__(self):
        super().__init__()
        MainWindow.instance = self

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # 致命错误检查
        if not os.path.exists("base_executor.py"):
            QMessageBox.critical(self, "致命错误", "缺少 base_executor.py 文件，请确保文件已重命名或存在。")
            sys.exit(1)

        self.config = load_config()
        if self.config is None: sys.exit(1)

        self.worker = None
        self.active_credentials = {}

        # 替换默认的 QListWidget 为可拖拽的
        self.replace_flow_list_widgets()

        self.load_workflows_to_pool()  # 加载流程到左侧库
        self.load_account_pool()

        self.active_workflow_key = list(PROCESS_MODULES.keys())[0] if PROCESS_MODULES else None

        # 绑定事件
        self.ui.save_button.clicked.connect(self.save_elements)
        self.ui.btn_add_acc.clicked.connect(self.add_or_update_account)
        self.ui.btn_del_acc.clicked.connect(self.del_account)

        self.ui.run_button.clicked.connect(self.run_sequence_batch)
        self.ui.btn_clear_queue.clicked.connect(self.ui.flow_queue_list.clear)  # 清空队列

        self.ui.account_pool_list.itemClicked.connect(self.load_selected_credentials)

        self.ui.tabs.currentChanged.connect(self.on_tab_changed)
        # 注意：这里我们不再需要 workflow_combo 的绑定，因为序列编排是主要的启动方式
        self.ui.tabs.currentChanged.connect(lambda: self.load_elements_to_table(filter_by_workflow=True))

        # 初始加载元素配置
        self.load_elements_to_table(filter_by_workflow=True)

    # --- 流程/配置 动态切换逻辑 ---
    def replace_flow_list_widgets(self):
        """用可拖拽的定制 ListWidget 替换默认的 QListWidget"""
        self.ui.flow_pool_list.deleteLater()
        self.ui.flow_queue_list.deleteLater()

        self.ui.flow_pool_list = FlowPoolListWidget()
        self.ui.flow_queue_list = FlowQueueListWidget(parent=self)

        self.ui.pool_layout.addWidget(self.ui.flow_pool_list)
        self.ui.queue_layout.insertWidget(0, self.ui.flow_queue_list)

    def load_flow_item(self, key):
        """弃用：由 create_flow_item_text 代替"""
        return self.create_flow_item_text(key)

    def create_flow_item_text(self, key):
        """根据 Key 生成可读的流程文本"""
        info = PROCESS_MODULES.get(key)
        if info:
            return f"{info.get('class')} ({key})"
        return None

    def load_workflows_to_pool(self):
        """加载所有可用的流程到左侧流程库"""
        self.ui.flow_pool_list.clear()
        for key, info in PROCESS_MODULES.items():
            text = self.create_flow_item_text(key)
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, key)  # 存储 key (例如 workflow_full_login)
            self.ui.flow_pool_list.addItem(item)

    def on_tab_changed(self, index):
        """切换 Tab 时，如果进入配置 Tab，则刷新表格"""
        if self.ui.tabs.tabText(index) == "元素定位配置":
            self.load_elements_to_table(filter_by_workflow=True)

    def load_elements_to_table(self, filter_by_workflow=False):
        """加载元素到表格，如果 filter_by_workflow=True，则显示所有元素"""
        self.ui.elements_table.setRowCount(0)
        elements_pool = self.config.get('elements', {})

        # 1. 在序列编排模式下，必须显示所有元素，因为所有流程都可能用到
        if filter_by_workflow:
            filter_keys = set()
            for key in PROCESS_MODULES:
                filter_keys.update(PROCESS_MODULES[key].get("elements", []))

            filtered_elements = {}
            for key in sorted(list(filter_keys)):  # 按字母排序显示
                if key in elements_pool:
                    filtered_elements[key] = elements_pool[key]
        else:
            filtered_elements = elements_pool

        # 2. 填充表格
        self.ui.elements_table.setRowCount(len(filtered_elements))
        for row, (key, info) in enumerate(filtered_elements.items()):
            item_key = QTableWidgetItem(key);
            item_key.setFlags(Qt.ItemIsEnabled)
            item_desc = QTableWidgetItem(info.get('description', ''));
            item_desc.setFlags(Qt.ItemIsEnabled)
            item_val = QTableWidgetItem(info.get('value', ''))
            self.ui.elements_table.setItem(row, 0, item_key)
            self.ui.elements_table.setItem(row, 1, item_desc)
            self.ui.elements_table.setItem(row, 2, item_val)

    # --- 运行逻辑 (已修改为序列模式) ---
    def run_sequence_batch(self):
        """读取队列，并按顺序启动 Worker"""
        if not self.active_credentials:
            QMessageBox.warning(self, "提示", "请先在列表中点击选择一个账号！")
            return

        if self.ui.flow_queue_list.count() == 0:
            QMessageBox.warning(self, "提示", "执行队列为空，请拖拽流程到右侧。")
            return

        if self.worker is not None and self.worker.isRunning():
            QMessageBox.warning(self, "警告", "任务正在运行中...")
            return

        # 1. 提取序列
        sequence_data = []
        for i in range(self.ui.flow_queue_list.count()):
            item = self.ui.flow_queue_list.item(i)
            flow_key = item.data(Qt.UserRole)
            sequence_data.append(flow_key)

        # 2. 准备运行参数
        sku_to_run = self.ui.sku_input.text().strip()
        alias = self.active_credentials.get('alias', '未知')

        self.ui.log_output.clear()
        self.ui.log_output.append(f"准备执行序列 ({len(sequence_data)} 步)，账号: {alias}")
        self.ui.run_button.setDisabled(True)

        # 3. 动态加载第一个流程类，并启动执行器
        first_flow_key = sequence_data[0]
        process_info = PROCESS_MODULES.get(first_flow_key)

        if not process_info:
            QMessageBox.critical(self, "错误", f"序列首个流程 {first_flow_key} 配置信息缺失。")
            self.ui.run_button.setDisabled(False)
            return

        ProcessClass = load_process_class(process_info['module'], process_info['class'])
        if not ProcessClass:
            self.ui.run_button.setDisabled(False)
            return

        # 4. 准备 credentials 列表
        credentials_list = [self.active_credentials.copy()]
        credentials_list[0]['sku'] = sku_to_run

        # 5. 启动 Worker，并将【整个序列】传递给 BaseExecutor
        self.worker = BaseExecutor(self.config, credentials_list, ProcessClass)
        self.worker.sequence = sequence_data  # 序列数据传递给 BaseExecutor

        self.worker.signals.log.connect(self.ui.log_output.append)
        self.worker.signals.finished.connect(self.on_finished)
        self.worker.start()

    # --- 账号管理逻辑 (保持不变) ---
    def load_account_pool(self):
        self.ui.account_pool_list.clear()
        accounts = self.config.get("accounts", {})
        self.ui.active_user_display.clear()
        self.ui.active_pwd_display.clear()
        self.active_credentials = {}
        for alias, creds in accounts.items():
            item = QListWidgetItem(f"{alias} ({creds.get('username')})")
            item.setData(Qt.UserRole, alias)
            self.ui.account_pool_list.addItem(item)

    def load_selected_credentials(self, item):
        alias = item.data(Qt.UserRole)
        creds = self.config["accounts"].get(alias)
        if creds:
            self.active_credentials = creds.copy()
            self.active_credentials['alias'] = alias
            self.ui.active_user_display.setText(creds.get('username'))
            self.ui.active_pwd_display.setText(creds.get('password'))
            self.ui.log_output.append(f"已选择账号: {alias}。")

    def add_or_update_account(self):
        alias = self.ui.acc_alias.text().strip()
        user = self.ui.acc_user.text().strip()
        pwd = self.ui.acc_pwd.text().strip()
        if not alias or not user or not pwd:
            QMessageBox.warning(self, "提示", "备注、账号、密码都不能为空！")
            return
        if "accounts" not in self.config: self.config["accounts"] = {}
        self.config["accounts"][alias] = {"username": user, "password": pwd}
        if save_config(self.config):
            self.load_account_pool()
            self.ui.acc_alias.clear();
            self.ui.acc_user.clear();
            self.ui.acc_pwd.clear()
            QMessageBox.information(self, "成功", f"账号 '{alias}' 已保存/更新。")

    def del_account(self):
        current_item = self.ui.account_pool_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先在列表中选中要删除的账号。")
            return
        alias = current_item.data(Qt.UserRole)
        del self.config["accounts"][alias]
        if save_config(self.config):
            self.load_account_pool()
            QMessageBox.information(self, "成功", f"账号 '{alias}' 已删除。")

    def save_elements(self):
        all_elements = self.config.get("elements", {})
        for row in range(self.ui.elements_table.rowCount()):
            key = self.ui.elements_table.item(row, 0).text()
            val = self.ui.elements_table.item(row, 2).text()

            if key in all_elements:
                all_elements[key]["value"] = val

        self.config["elements"] = all_elements

        if save_config(self.config):
            QMessageBox.information(self, "成功", "元素配置已保存")
            self.load_elements_to_table(filter_by_workflow=True)

    def on_finished(self):
        self.ui.log_output.append("任务已结束。")
        self.ui.run_button.setDisabled(False)


# --- 程序入口 ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())