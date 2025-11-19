import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableWidgetItem,
                             QMessageBox, QListWidgetItem)
from PyQt5.QtCore import Qt

from ui_main import Ui_MainWindow
from config_manager import load_config, save_config
from selenium_worker import SeleniumWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.config = load_config()
        if self.config is None: sys.exit(1)

        self.worker = None
        # [新增] 存储当前选中的凭证 (单套)
        self.active_credentials = {}

        # 初始化界面数据
        self.load_elements_to_table()
        self.load_workflows_to_combo()
        self.load_account_pool()

        # 绑定事件
        self.ui.save_button.clicked.connect(self.save_elements)
        self.ui.btn_add_acc.clicked.connect(self.add_or_update_account)  # 绑定新增/更新
        self.ui.btn_del_acc.clicked.connect(self.del_account)
        self.ui.run_button.clicked.connect(self.run_single_account)  # 绑定单次运行

        # [新增] 列表点击事件：点击列表项，自动加载账号到运行区域
        self.ui.account_pool_list.itemClicked.connect(self.load_selected_credentials)

    # --- 账号管理逻辑 ---

    def load_account_pool(self):
        """加载所有账号到列表"""
        self.ui.account_pool_list.clear()
        accounts = self.config.get("accounts", {})
        # 清空 Active Display
        self.ui.active_user_display.clear()
        self.ui.active_pwd_display.clear()
        self.active_credentials = {}

        for alias, creds in accounts.items():
            # 显示格式: 备注 (账号)
            item = QListWidgetItem(f"{alias} ({creds.get('username')})")
            item.setData(Qt.UserRole, alias)  # 存储 Key (alias)
            self.ui.account_pool_list.addItem(item)

    def load_selected_credentials(self, item):
        """点击列表项时触发：将选中的账号加载到 Active Display"""
        alias = item.data(Qt.UserRole)
        creds = self.config["accounts"].get(alias)

        if creds:
            # 1. 更新内部变量 (本次运行的凭证)
            self.active_credentials = creds.copy()
            self.active_credentials['alias'] = alias

            # 2. 更新 UI
            self.ui.active_user_display.setText(creds.get('username'))
            self.ui.active_pwd_display.setText(creds.get('password'))  # 密码是明文，安全问题交给 Worker 处理
            self.ui.log_output.append(f"已选择账号: {alias}。")

    def add_or_update_account(self):
        """将新增区的账号保存/更新到账号池"""
        alias = self.ui.acc_alias.text().strip()
        user = self.ui.acc_user.text().strip()
        pwd = self.ui.acc_pwd.text().strip()

        if not alias or not user or not pwd:
            QMessageBox.warning(self, "提示", "备注、账号、密码都不能为空！")
            return

        if "accounts" not in self.config: self.config["accounts"] = {}
        self.config["accounts"][alias] = {"username": user, "password": pwd}

        if save_config(self.config):
            self.load_account_pool()  # 刷新列表
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

    # --- 运行逻辑 ---

    def run_single_account(self):
        """
        运行当前选中的一个账号的流程。
        未来循环时，只需将多套凭证放入列表即可。
        """
        if not self.active_credentials:
            QMessageBox.warning(self, "提示", "请先在列表中点击选择一个账号！")
            return

        if self.worker is not None and self.worker.isRunning():
            QMessageBox.warning(self, "警告", "任务正在运行中...")
            return

        workflow_key = self.ui.workflow_combo.currentData()
        alias = self.active_credentials.get('alias', '未知')

        self.ui.log_output.clear()
        self.ui.log_output.append(f"准备执行工作流: {workflow_key}，账号: {alias}")
        self.ui.run_button.setDisabled(True)

        # 将单个凭证包装成一个列表，传入 Worker (Worker 内部是循环结构，兼容未来)
        credentials_list = [self.active_credentials]

        self.worker = SeleniumWorker(self.config, workflow_key, credentials_list)
        self.worker.signals.log.connect(self.ui.log_output.append)
        self.worker.signals.finished.connect(self.on_finished)
        self.worker.start()

    # --- 以下函数保持不变 ---

    def on_finished(self):
        self.ui.log_output.append("任务已结束。")
        self.ui.run_button.setDisabled(False)

    def load_elements_to_table(self):
        # ... (代码保持不变) ...
        self.ui.elements_table.setRowCount(0)
        elements = self.config.get('elements', {})
        self.ui.elements_table.setRowCount(len(elements))
        for row, (key, info) in enumerate(elements.items()):
            item_key = QTableWidgetItem(key);
            item_key.setFlags(Qt.ItemIsEnabled)
            item_desc = QTableWidgetItem(info.get('description', ''));
            item_desc.setFlags(Qt.ItemIsEnabled)
            item_val = QTableWidgetItem(info.get('value', ''))
            self.ui.elements_table.setItem(row, 0, item_key)
            self.ui.elements_table.setItem(row, 1, item_desc)
            self.ui.elements_table.setItem(row, 2, item_val)

    def load_workflows_to_combo(self):
        self.ui.workflow_combo.clear()
        for key, info in self.config.get('workflows', {}).items():
            self.ui.workflow_combo.addItem(f"{info.get('description')} ({key})", key)

    def save_elements(self):
        new_elements = {}
        for row in range(self.ui.elements_table.rowCount()):
            key = self.ui.elements_table.item(row, 0).text()
            desc = self.ui.elements_table.item(row, 1).text()
            val = self.ui.elements_table.item(row, 2).text()
            new_elements[key] = {"description": desc, "by": "auto", "value": val}
        self.config["elements"] = new_elements
        if save_config(self.config):
            QMessageBox.information(self, "成功", "元素配置已保存")


# --- 程序入口 ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())