import sys
import importlib.util
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableWidgetItem,
                             QMessageBox, QListWidgetItem)
from PyQt5.QtCore import Qt

from ui_main import Ui_MainWindow
from config_manager import load_config, save_config
from base_executor import BaseExecutor # 导入 BaseExecutor


# 定义流程模块的映射关系，新增了 "elements" 字段来指定该流程所需的元素 Key
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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # 检查 BaseExecutor 文件，防止程序启动失败
        if not os.path.exists("base_executor.py"):
            QMessageBox.critical(self, "致命错误", "缺少 base_executor.py 文件，请确保文件已重命名或存在。")
            sys.exit(1)

        self.config = load_config()
        if self.config is None: sys.exit(1)

        self.worker = None
        self.active_credentials = {}

        self.load_workflows_to_combo()
        self.active_workflow_key = self.ui.workflow_combo.currentData() if self.ui.workflow_combo.count() > 0 else None

        # 初始化界面数据
        self.load_elements_to_table()
        self.load_account_pool()

        # 绑定事件
        self.ui.save_button.clicked.connect(self.save_elements)
        self.ui.btn_add_acc.clicked.connect(self.add_or_update_account)
        self.ui.btn_del_acc.clicked.connect(self.del_account)
        self.ui.run_button.clicked.connect(self.run_single_account)
        self.ui.account_pool_list.itemClicked.connect(self.load_selected_credentials)

        self.ui.tabs.currentChanged.connect(self.on_tab_changed)
        self.ui.workflow_combo.currentIndexChanged.connect(self.on_workflow_change)

    # --- 流程/配置 动态切换逻辑 ---
    def on_tab_changed(self, index):
        if self.ui.tabs.tabText(index) == "元素定位配置":
            self.load_elements_to_table(filter_by_workflow=True)

    def on_workflow_change(self, index):
        self.active_workflow_key = self.ui.workflow_combo.currentData()
        if self.ui.tabs.currentIndex() == 1:
             self.load_elements_to_table(filter_by_workflow=True)
        self.ui.log_output.append(f"当前任务流程已切换为: {self.active_workflow_key}")

    def load_elements_to_table(self, filter_by_workflow=False):
        self.ui.elements_table.setRowCount(0)
        elements_pool = self.config.get('elements', {})

        filter_keys = None
        if filter_by_workflow and self.active_workflow_key and self.active_workflow_key in PROCESS_MODULES:
            filter_keys = PROCESS_MODULES[self.active_workflow_key].get("elements", [])

        filtered_elements = {}
        if filter_keys:
            for key in filter_keys:
                if key in elements_pool:
                    filtered_elements[key] = elements_pool[key]
        else:
            filtered_elements = elements_pool

        self.ui.elements_table.setRowCount(len(filtered_elements))
        for row, (key, info) in enumerate(filtered_elements.items()):
            item_key = QTableWidgetItem(key); item_key.setFlags(Qt.ItemIsEnabled)
            item_desc = QTableWidgetItem(info.get('description', '')); item_desc.setFlags(Qt.ItemIsEnabled)
            item_val = QTableWidgetItem(info.get('value', ''))
            self.ui.elements_table.setItem(row, 0, item_key)
            self.ui.elements_table.setItem(row, 1, item_desc)
            self.ui.elements_table.setItem(row, 2, item_val)

    def load_workflows_to_combo(self):
        self.ui.workflow_combo.clear()
        for key, info in PROCESS_MODULES.items():
            self.ui.workflow_combo.addItem(f"{key}", key)

        if self.ui.workflow_combo.count() > 0:
            self.active_workflow_key = self.ui.workflow_combo.currentData()

    # --- 账号管理逻辑 ---
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
            self.ui.acc_alias.clear(); self.ui.acc_user.clear(); self.ui.acc_pwd.clear()
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

    # --- 运行逻辑 ---
    def run_single_account(self):
        if not self.active_credentials:
            QMessageBox.warning(self, "提示", "请先在列表中点击选择一个账号！")
            return
        if self.worker is not None and self.worker.isRunning():
            QMessageBox.warning(self, "警告", "任务正在运行中...")
            return

        workflow_key = self.ui.workflow_combo.currentData()
        alias = self.active_credentials.get('alias', '未知')
        sku_to_run = self.ui.sku_input.text().strip()

        process_info = PROCESS_MODULES.get(workflow_key)
        if not process_info: return

        ProcessClass = load_process_class(process_info['module'], process_info['class'])
        if not ProcessClass: return

        self.ui.log_output.clear()
        self.ui.log_output.append(f"准备执行工作流: {workflow_key}，账号: {alias}")
        self.ui.run_button.setDisabled(True)

        credentials_list = [self.active_credentials]
        credentials_list[0]['sku'] = sku_to_run

        self.worker = BaseExecutor(self.config, credentials_list, ProcessClass)
        self.worker.signals.log.connect(self.ui.log_output.append)
        self.worker.signals.finished.connect(self.on_finished)
        self.worker.start()

    def on_finished(self):
        self.ui.log_output.append("任务已结束。")
        self.ui.run_button.setDisabled(False)

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

# --- 【修复的入口代码块】 ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())