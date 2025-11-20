import sys
import os
import openpyxl
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTabWidget, QFormLayout, QScrollArea, QComboBox,
                             QLineEdit, QPushButton, QLabel, QDialog, QGroupBox,
                             QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QTextEdit, QFileDialog)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QFont, QTextCharFormat, QTextCursor

# 导入配置管理器和定位解析器
from config_manager import config_manager
from edge_automation_tool import LocatorParser

# 假设的自动化核心函数 (需要在实际环境中运行)
try:
    from selenium import webdriver
    from selenium.webdriver.edge.service import Service
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    from selenium.webdriver.common.keys import Keys

    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


# 【ResultsTableDialog 类】 (与之前一致，用于结果展示)
class ResultsTableDialog(QDialog):
    def __init__(self, data, headers, parent=None):
        super().__init__(parent)
        self.setWindowTitle("自动化抓取结果预览")
        self.setGeometry(200, 200, 800, 600)
        self.layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

        self.table.setRowCount(len(data))
        for row_idx, row_data in enumerate(data):
            for col_idx, cell_data in enumerate(row_data):
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(cell_data)))

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layout.addWidget(self.table)

        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)
        self.layout.addWidget(close_button)


class AutomationToolUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Edge 自动化配置工具")
        self.setGeometry(100, 100, 850, 750)

        self.config_settings = QSettings('MyCompany', 'EdgeAutoTool')

        self.all_accounts = []
        self.element_config = []  # 存储模块化结构
        self.element_fields = {}  # 存储 QLineEdit 控件引用 (用于 get/set 数据)
        self.runtime_selected_account_name = ''
        self.sku_file_path = ''

        self.load_config()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QVBoxLayout(self.central_widget)
        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)

        self.create_operation_page()
        self.create_config_page()

    # 【新增方法：数据结构统一（代码结构优先）】
    def _unify_element_config(self, code_structure, json_data):
        """
        将 JSON 文件中的定位值合并到 Python 代码定义的模块化结构中 (Python 结构优先)。
        """

        # 1. 扁平化 JSON 数据，方便查找 {"name": "locator"}
        json_locators = {}
        if json_data:
            for module_item in json_data:
                for element in module_item.get("elements", []):
                    json_locators[element["name"]] = element.get("locator", "")

        # 2. 从 Python 代码结构开始，用 JSON 值填充
        unified_config = code_structure.copy()

        for module_item in unified_config:
            for element in module_item["elements"]:
                name = element["name"]
                # 如果 JSON 中有该元素的定位值，则使用 JSON 的值
                if name in json_locators:
                    element["locator"] = json_locators[name]

        return unified_config

    # --- 1. 配置加载与保存 ---
    def load_config(self):
        """从 ConfigManager 加载配置，并初始化运行时值"""

        config = config_manager.load_config()
        default_config = config_manager.default_config

        self.all_accounts = config.get("ACCOUNTS", [])

        # 使用统一方法加载配置
        self.element_config = self._unify_element_config(
            default_config.get("ELEMENT_CONFIG", []),
            config.get("ELEMENT_CONFIG_FROM_FILE", [])  # 从临时存储中获取 JSON 文件数据
        )

        # 加载运行时值
        self.runtime_url = self.config_settings.value('url', config.get("LOGIN_URL"))
        self.runtime_org_code = self.config_settings.value('org_code', config.get("ORG_CODE"))
        self.sku_file_path = self.config_settings.value('sku_file_path', config.get("SKU_FILE_PATH"))
        self.runtime_start_point = self.config_settings.value('start_point', '完整流程 (从登录开始)')

        # 加载上一次选择的账号名称
        first_account_name = self.all_accounts[0]['name'] if self.all_accounts else ''
        self.runtime_selected_account_name = self.config_settings.value('last_selected_account', first_account_name)

    def save_config(self):
        """将当前的配置状态保存到 ConfigManager 和 QSettings"""

        if self.element_fields:
            element_config_data = self.get_table_data()
        else:
            element_config_data = self.element_config

        data = {
            "LOGIN_URL": self.url_input.text(),
            "ORG_CODE": self.org_code_input.text(),
            "SKU_FILE_PATH": self.file_path_input.text(),
            "ACCOUNTS": self.all_accounts,
            "ELEMENT_CONFIG": element_config_data
        }

        if config_manager.save_config(data):
            self.log("配置已保存。", "green")
        else:
            QMessageBox.critical(self, "保存错误", "保存配置文件时出错。请查看日志。")

        # 保存运行时参数到 QSettings
        if self.runtime_selected_account_name:
            self.config_settings.setValue('last_selected_account', self.runtime_selected_account_name)

        self.config_settings.setValue('url', self.url_input.text())
        self.config_settings.setValue('org_code', self.org_code_input.text())
        self.config_settings.setValue('sku_file_path', self.file_path_input.text())
        self.config_settings.setValue('start_point', self.start_point_combo.currentText())

    # --- 2. 账号档案管理逻辑 (省略) ---
    def load_account_profiles_to_ui(self):
        # ... (与之前一致) ...
        for i in reversed(range(self.account_list_layout.count())):
            widget_to_remove = self.account_list_layout.itemAt(i).widget()
            if widget_to_remove:
                widget_to_remove.setParent(None)

        if self.all_accounts:
            for account in self.all_accounts:
                btn = QPushButton(account["name"])
                btn.setProperty("account_name", account["name"])
                btn.clicked.connect(lambda checked, name=account["name"]: self.select_account_profile_by_name(name))
                self.account_list_layout.addWidget(btn)

            self.select_account_profile_by_name(self.runtime_selected_account_name, initial_load=True)
            self.delete_account_button.setEnabled(True)
        else:
            no_account_label = QLabel("无可用账号档案。请在下方输入并保存新档案。")
            self.account_list_layout.addWidget(no_account_label)
            self.account_name_input.clear()
            self.username_input.clear()
            self.password_input.clear()
            self.delete_account_button.setEnabled(False)
            self.runtime_selected_account_name = ''

    def select_account_profile_by_name(self, name, initial_load=False):
        # ... (与之前一致) ...
        selected_account = None
        for account in self.all_accounts:
            if account["name"] == name:
                selected_account = account
                break

        for i in range(self.account_list_layout.count()):
            widget = self.account_list_layout.itemAt(i).widget()
            if isinstance(widget, QPushButton):
                if widget.property("account_name") == name:
                    widget.setStyleSheet("background-color: #AECBFA; font-weight: bold;")
                else:
                    widget.setStyleSheet("")

        if selected_account:
            self.account_name_input.setText(selected_account.get("name", ""))
            self.username_input.setText(selected_account.get("username", ""))
            self.password_input.setText(selected_account.get("password", ""))
            self.delete_account_button.setEnabled(True)
            self.runtime_selected_account_name = name

            if not initial_load:
                self.save_config()
        else:
            self.account_name_input.clear()
            self.username_input.clear()
            self.password_input.clear()
            self.delete_account_button.setEnabled(False)
            self.runtime_selected_account_name = ''

    def save_current_account(self):
        # ... (与之前一致) ...
        name = self.account_name_input.text().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not name or not username or not password:
            QMessageBox.warning(self, "保存失败", "档案名称、账号和密码都不能为空。")
            return

        existing_index = -1
        for i, account in enumerate(self.all_accounts):
            if account["name"] == name:
                existing_index = i
                break

        new_account = {
            "name": name,
            "username": username,
            "password": password
        }

        if existing_index != -1:
            self.all_accounts[existing_index] = new_account
            self.log(f"账号档案 '{name}' 已更新。", "blue")
        else:
            self.all_accounts.append(new_account)
            self.log(f"账号档案 '{name}' 已新增。", "blue")

        self.save_config()
        self.load_account_profiles_to_ui()
        self.select_account_profile_by_name(name)

    def delete_current_account(self):
        # ... (与之前一致) ...
        current_name = self.account_name_input.text().strip()
        if not current_name or not self.runtime_selected_account_name:
            QMessageBox.warning(self, "删除失败", "请选择一个有效的账号档案。")
            return

        reply = QMessageBox.question(self, '确认删除',
                                     f"确定要删除账号档案 '{current_name}' 吗?", QMessageBox.Yes |
                                     QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.all_accounts = [acc for acc in self.all_accounts if acc["name"] != current_name]

            self.log(f"账号档案 '{current_name}' 已删除。", "blue")
            self.runtime_selected_account_name = ''
            self.save_config()

            self.load_account_profiles_to_ui()
            if self.all_accounts:
                self.select_account_profile_by_name(self.all_accounts[0]['name'])
            else:
                self.select_account_profile_by_name('')

    def open_file_dialog(self):
        # ... (与之前一致) ...
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 SKU 列表文件",
            "",
            "Excel/CSV 文件 (*.xlsx *.csv);;所有文件 (*)"
        )
        if file_path:
            self.file_path_input.setText(file_path)
            self.save_config()

    # --- 3. 操作页面 (Operation Panel) ---
    def create_operation_page(self):
        op_page = QWidget()
        self.tab_widget.addTab(op_page, "操作执行")

        layout = QFormLayout(op_page)
        layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        # 账号管理 UI 布局 (与之前一致)
        layout.addRow(QLabel("--- 账号档案配置 ---"))
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        account_list_widget = QWidget()
        self.account_list_layout = QVBoxLayout(account_list_widget)
        self.account_list_layout.setAlignment(Qt.AlignTop)
        scroll_area.setWidget(account_list_widget)
        scroll_area.setMaximumHeight(150)
        layout.addRow("所有账号档案:", scroll_area)

        self.account_name_input = QLineEdit()
        layout.addRow("档案名称:", self.account_name_input)
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addRow("账号 (Username):", self.username_input)
        layout.addRow("密码 (Password):", self.password_input)

        account_button_layout = QHBoxLayout()
        self.save_account_button = QPushButton("保存/更新当前档案")
        self.save_account_button.clicked.connect(self.save_current_account)
        self.delete_account_button = QPushButton("删除当前档案")
        self.delete_account_button.clicked.connect(self.delete_current_account)

        account_button_layout.addWidget(self.save_account_button)
        account_button_layout.addWidget(self.delete_account_button)
        layout.addRow(account_button_layout)

        # 运行参数 (与之前一致)
        layout.addRow(QLabel("--- 运行参数 ---"))

        self.url_input = QLineEdit(self.runtime_url)
        layout.addRow("目标 URL:", self.url_input)

        self.org_code_input = QLineEdit(self.runtime_org_code)
        layout.addRow("组织代码 (如: 156):", self.org_code_input)

        sku_path_layout = QHBoxLayout()
        self.file_path_input = QLineEdit(self.sku_file_path)
        self.file_path_input.setReadOnly(True)
        select_file_button = QPushButton("选择文件...")
        select_file_button.clicked.connect(self.open_file_dialog)

        sku_path_layout.addWidget(self.file_path_input)
        sku_path_layout.addWidget(select_file_button)
        layout.addRow("SKU 列表文件路径:", sku_path_layout)

        self.start_point_combo = QComboBox()
        self.start_point_combo.addItem("完整流程 (从登录开始)")
        self.start_point_combo.addItem("跳过登录/组织选择 (从导航开始)")

        index = self.start_point_combo.findText(self.runtime_start_point)
        if index != -1:
            self.start_point_combo.setCurrentIndex(index)

        layout.addRow("自动化起始点:", self.start_point_combo)

        # 执行按钮和日志区域 (与之前一致)
        self.execute_button = QPushButton("开始执行 Edge 自动化")
        self.execute_button.setFont(QFont('Arial', 12, QFont.Bold))
        self.execute_button.clicked.connect(self.start_automation)

        self.save_button = QPushButton("保存所有配置")
        self.save_button.clicked.connect(self.save_config)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.execute_button)
        layout.addRow(button_layout)

        log_label = QLabel("执行日志:")
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addRow(log_label)
        layout.addRow(self.log_output)

        self.load_account_profiles_to_ui()

    def log(self, message, color="black"):
        """实时日志输出"""
        fmt = QTextCharFormat()
        if color == "red":
            fmt.setForeground(Qt.red)
        elif color == "green":
            fmt.setForeground(Qt.green)
        elif color == "blue":
            fmt.setForeground(Qt.blue)
        else:
            fmt.setForeground(Qt.black)

        cursor = self.log_output.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(f"{message}\n", fmt)
        self.log_output.ensureCursorVisible()

        QApplication.processEvents()

    # 【新增方法：读取 SKU 文件】 (与之前一致)
    def _read_skus_from_file(self, file_path):
        """从用户指定的表格文件读取 SKU 列表。只读取第一列，跳过第一行（标题）"""

        if not os.path.exists(file_path):
            self.log(f"ERROR: SKU 文件未找到: {file_path}", "red")
            return []

        try:
            if file_path.endswith('.xlsx'):
                workbook = openpyxl.load_workbook(file_path)
                sheet = workbook.active
                skus = []
                for row_idx, row in enumerate(sheet.iter_rows(min_col=1, max_col=1, values_only=True)):
                    if row_idx == 0:
                        continue
                    if row[0] is not None:
                        skus.append(str(row[0]).strip())
                return [sku for sku in skus if sku]
            else:
                self.log("ERROR: 暂不支持该文件类型。请选择 .xlsx 文件。", "red")
                return []

        except Exception as e:
            self.log(f"ERROR: 读取 SKU 文件失败: {e}", "red")
            return []

    # --- 4. 自动化执行核心 ---
    def _get_locator(self, parsed_config, element_name):
        """安全地从配置中获取定位器"""
        if element_name not in parsed_config:
            raise KeyError(f"元素 '{element_name}' 未在配置页面中定义。请检查 config_manager.py 和元素配置。")
        return parsed_config[element_name]

    def _execute_login_flow(self, driver, wait, parsed_config, url, username, password, org_code):
        # ... (登录流程) ...
        self.log(f"1. 访问 URL: {url}...")
        driver.get(url)

        self.log(f"2. 输入账号和密码...")
        wait.until(EC.presence_of_element_located(self._get_locator(parsed_config, '账号输入框'))).send_keys(username)
        wait.until(EC.presence_of_element_located(self._get_locator(parsed_config, '密码输入框'))).send_keys(password)

        self.log("3. 点击登录按钮...")
        wait.until(EC.element_to_be_clickable(self._get_locator(parsed_config, '登录按钮'))).click()

        self.log("4. 等待组织选择弹窗...")
        wait.until(EC.presence_of_element_located(self._get_locator(parsed_config, '组织选择弹窗')))
        self.log("组织选择弹窗已出现。", "green")

        self.log(f"5. 输入组织代码: {org_code}")
        org_input = wait.until(EC.presence_of_element_located(self._get_locator(parsed_config, '组织输入框')))
        org_input.send_keys(org_code)

        list_item_by, list_item_value = self._get_locator(parsed_config, '组织列表项')
        dynamic_list_item_value = list_item_value.replace('156', org_code)
        dynamic_list_item_locator = (list_item_by, dynamic_list_item_value)

        self.log(f"6. 等待并点击组织列表项 (定位: {dynamic_list_item_locator[1]})")
        wait.until(EC.element_to_be_clickable(dynamic_list_item_locator)).click()

        self.log("7. 点击确认登录按钮...")
        wait.until(EC.element_to_be_clickable(self._get_locator(parsed_config, '确认登录按钮'))).click()

        self.log("8. 等待跳转到首页...")
        wait.until(EC.url_contains("home_page"))

        self.log("完整登录和组织选择流程成功完成！", "green")

    def _execute_navigation_to_product_list(self, driver, wait, parsed_config):
        # ... (导航流程) ...
        self.log("9. 执行导航流程: 鼠标悬停...")

        nav_icon_locator = self._get_locator(parsed_config, '导航_商品主图标')
        list_link_locator = self._get_locator(parsed_config, '导航_分销商品列表')

        # 【关键修复：使用 visibility_of_element_located】
        nav_icon_element = wait.until(EC.visibility_of_element_located(nav_icon_locator))
        ActionChains(driver).move_to_element(nav_icon_element).perform()

        self.log("悬停成功，等待子菜单出现...")

        self.log("10. 点击 '分销商品列表'...")
        wait.until(EC.element_to_be_clickable(list_link_locator)).click()

        self.log("11. 导航完成，等待页面加载...")
        self.log("导航到 '分销商品列表' 成功。", "green")

    def _capture_detail_info(self, driver, wait, parsed_config):
        # ... (数据抓取流程) ...
        self.log("15. 抓取数据流程开始...")

        view_detail_locator = self._get_locator(parsed_config, 'product_list_view_detail_button')
        detail_dialog_locator = self._get_locator(parsed_config, 'detail_popup_dialog')
        detail_table_locator = self._get_locator(parsed_config, 'detail_info_table')

        self.log("16. 点击 '查看详情' 按钮...")
        wait.until(EC.element_to_be_clickable(view_detail_locator)).click()

        self.log("17. 等待详情弹窗出现...")
        wait.until(EC.visibility_of_element_located(detail_dialog_locator))

        self.log("18. 抓取详情表格内容...")
        detail_table_element = wait.until(EC.presence_of_element_located(detail_table_locator))

        captured_data = detail_table_element.text

        # 关闭弹窗（模拟点击 ESC 键）
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)

        # 显式等待弹窗消失
        wait.until(EC.invisibility_of_element_located(detail_dialog_locator))

        self.log("详情信息抓取完成，并关闭弹窗。", "green")

        return captured_data

    def _execute_product_search(self, driver, wait, parsed_config, sku_value):
        # ... (查询流程) ...
        self.log("12. 执行商品查询流程...")

        sku_input_locator = self._get_locator(parsed_config, 'product_list_sku_input')
        search_button_locator = self._get_locator(parsed_config, 'product_list_search_button')

        self.log(f"13. 输入 SKU: {sku_value}")
        sku_element = wait.until(EC.visibility_of_element_located(sku_input_locator))
        sku_element.clear()
        sku_element.send_keys(sku_value)

        self.log("14. 点击 '查询' 按钮...")
        wait.until(EC.element_to_be_clickable(search_button_locator)).click()

        self.log("查询指令已发送，等待结果加载...")

        self.log("商品查询流程成功完成。", "green")

    def start_automation(self):
        # ... (主流程) ...
        if not SELENIUM_AVAILABLE:
            self.log("ERROR: Selenium 库未安装。请先安装。", "red")
            return

        self.log("--- 自动化执行开始 ---", "blue")
        self.save_config()

        url = self.url_input.text()
        username = self.username_input.text()
        password = self.password_input.text()
        org_code = self.org_code_input.text()
        sku_file_path = self.file_path_input.text()
        start_point = self.start_point_combo.currentText()

        if start_point == "完整流程 (从登录开始)" and (not username or not password):
            self.log(f"FATAL ERROR: 选择完整流程时，账号和密码不能为空。", "red")
            return

        config_data = self.get_table_data()

        # 扁平化配置数据，方便查找 {"name": (By, value)}
        parsed_config = {}
        for module_item in config_data:
            for element in module_item.get("elements", []):
                by, value = LocatorParser.parse(element["locator"])
                if by and value:
                    parsed_config[element["name"]] = (by, value)

        # 读取 SKU 列表
        sku_list = self._read_skus_from_file(sku_file_path)
        if not sku_list:
            self.log("FATAL ERROR: 未能从文件中读取到 SKU 列表，请检查文件路径和内容。", "red")
            return

        self.log(f"成功读取 {len(sku_list)} 个 SKU。", "blue")

        try:
            service = Service()
            driver = webdriver.Edge(service=service)
            self.log("Edge 浏览器启动成功。", "green")
        except Exception as e:
            self.log(f"FATAL ERROR: Edge 浏览器启动失败。请确保安装了 Edge 浏览器并配置了 msedgedriver: {e}", "red")
            return

        all_results = []
        try:
            wait = WebDriverWait(driver, 15)

            # 流程控制
            if start_point == "完整流程 (从登录开始)":
                self._execute_login_flow(driver, wait, parsed_config, url, username, password, org_code)

            elif start_point == "跳过登录/组织选择 (从导航开始)":
                self.log("跳过登录/组织选择流程，直接从导航开始...", "blue")
                driver.get(url.split('#')[0] + '#/product/distribution_list')

                # 导航到商品列表页
            self._execute_navigation_to_product_list(driver, wait, parsed_config)

            # 【核心逻辑：循环查询】
            for sku_idx, current_sku in enumerate(sku_list):
                # 首次运行只测试第一个 SKU
                if sku_idx > 0:
                    break

                self.log(f"\n--- 开始处理 SKU: {current_sku} ---", "blue")

                self._execute_product_search(driver, wait, parsed_config, current_sku)
                captured_text = self._capture_detail_info(driver, wait, parsed_config)

                all_results.append({
                    "SKU": current_sku,
                    "Captured_Text": captured_text
                })

                self.log(f"SKU {current_sku} 处理完成。", "green")

            self.log("自动化测试运行成功。", "green")

            # 结果展示
            if all_results:
                headers = ["SKU", "抓取到的详情文本"]
                data = [[res["SKU"], res["Captured_Text"].replace('\n', ' | ')] for res in all_results]
                dialog = ResultsTableDialog(data, headers, self)
                dialog.exec_()


        except KeyError as e:
            self.log(f"FATAL ERROR: 自动化流程失败，因为配置中缺少 {e} 元素。请检查 config_manager.py 或配置页面。", "red")
        except Exception as e:
            self.log(f"自动化执行中发生错误: {e}", "red")
        finally:
            self.log("请手动关闭 Edge 浏览器以结束。", "blue")

        self.log("--- 自动化执行结束 ---", "blue")

    # --- 5. 配置页面 (Configuration Panel) 【已模块化】---
    def create_config_page(self):
        config_page = QWidget()
        self.tab_widget.addTab(config_page, "元素配置")

        layout = QVBoxLayout(config_page)

        guide_label = QLabel("<b>智能定位指南:</b><br>"
                             "1. <code>//div[@id='root']</code> 或 <code>.my-class</code> (直接 XPath/CSS)<br>"
                             "2. <code>placeholder=\"请输入\"</code> (自动识别属性: key=\"value\")<br>"
                             "3. <code>&lt;tag&gt;文本</code> (标签+文本: 精确匹配，忽略子标签)<br>"
                             "4. <code>纯文本</code> (模糊匹配: 查找包含该文本的任何元素)")
        guide_label.setTextFormat(Qt.RichText)
        guide_label.setWordWrap(True)
        layout.addWidget(guide_label)

        # 模块化 UI 渲染
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        config_container = QWidget()
        container_layout = QVBoxLayout(config_container)

        self.element_fields = {}  # 存储 QLineEdit 控件引用

        for module_item in self.element_config:
            module_name = module_item["module"]
            group_box = QGroupBox(module_name)
            group_layout = QFormLayout(group_box)

            for element in module_item["elements"]:
                name = element["name"]
                locator_input = QLineEdit(element["locator"])
                self.element_fields[name] = locator_input
                group_layout.addRow(name, locator_input)

            container_layout.addWidget(group_box)

        scroll_area.setWidget(config_container)
        layout.addWidget(scroll_area)

        # 配置保存按钮
        save_config_button = QPushButton("保存元素配置")
        save_config_button.clicked.connect(self.save_config)
        layout.addWidget(save_config_button)

    def get_table_data(self):
        """从 UI 元素中获取当前数据，并返回模块化结构"""
        updated_config = []

        for module_item in self.element_config:
            new_module = {"module": module_item["module"], "elements": []}
            for element in module_item["elements"]:
                name = element["name"]
                if name in self.element_fields:
                    locator = self.element_fields[name].text()
                    new_module["elements"].append({"name": name, "locator": locator})
                else:
                    new_module["elements"].append(element)
            updated_config.append(new_module)

        return updated_config


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AutomationToolUI()
    window.show()
    sys.exit(app.exec_())