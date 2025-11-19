import sys
import json
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTabWidget, QFormLayout,
                             QLineEdit, QPushButton, QLabel, QTableWidget,
                             QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox, QTextEdit)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QFont, QTextCharFormat, QTextCursor

# 导入上面定义的智能定位解析器
from edge_automation_tool import LocatorParser

# 假设的自动化核心函数 (需要在实际环境中运行)
try:
    from selenium import webdriver
    from selenium.webdriver.edge.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("Selenium 库未找到。自动化功能将无法执行。请使用 pip install selenium 安装。")

# 默认配置路径
CONFIG_FILE = 'element_config.json'
DEFAULT_CONFIG = {
    "LOGIN_URL": "https://saaserp-pos.yibainetwork.com/#/login_page",
    "ELEMENT_CONFIG": [
        {"name": "账号输入框", "locator": "placeholder=\"请输入账号\""},
        {"name": "密码输入框", "locator": "placeholder=\"请输入密码\""},
        {"name": "登录按钮", "locator": "登录"},
    ]
}


class AutomationToolUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Edge 自动化配置工具")
        self.setGeometry(100, 100, 800, 600)

        self.config_settings = QSettings('MyCompany', 'EdgeAutoTool')
        self.element_config = DEFAULT_CONFIG["ELEMENT_CONFIG"]
        self.load_config()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QVBoxLayout(self.central_widget)
        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)

        self.create_operation_page()
        self.create_config_page()

    # --- 1. 配置加载与保存 ---
    def load_config(self):
        """从配置文件加载配置，或使用默认配置"""
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.element_config = config.get("ELEMENT_CONFIG", DEFAULT_CONFIG["ELEMENT_CONFIG"])
                self.config_settings.setValue('url', config.get("LOGIN_URL", DEFAULT_CONFIG["LOGIN_URL"]))
        except (FileNotFoundError, json.JSONDecodeError):
            print(f"配置文件 {CONFIG_FILE} 不存在或格式错误，使用默认配置。")

        # 加载账号/密码/URL的运行时值
        self.runtime_url = self.config_settings.value('url', DEFAULT_CONFIG["LOGIN_URL"])
        self.runtime_username = self.config_settings.value('username', '')
        self.runtime_password = self.config_settings.value('password', '')

    def save_config(self):
        """将当前的元素配置和URL保存到文件和QSettings"""
        data = {
            "LOGIN_URL": self.url_input.text(),
            "ELEMENT_CONFIG": self.get_table_data()
        }

        # 保存到文件
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"配置已保存到 {CONFIG_FILE}")
        except Exception as e:
            QMessageBox.critical(self, "保存错误", f"保存配置文件时出错: {e}")

        # 保存运行时参数到 QSettings
        self.config_settings.setValue('url', self.url_input.text())
        self.config_settings.setValue('username', self.username_input.text())
        self.config_settings.setValue('password', self.password_input.text())

    # --- 2. 操作页面 (Operation Panel) ---
    def create_operation_page(self):
        op_page = QWidget()
        self.tab_widget.addTab(op_page, "操作执行")

        layout = QFormLayout(op_page)
        layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        # URL 输入
        self.url_input = QLineEdit(self.runtime_url)
        layout.addRow("目标 URL:", self.url_input)

        # 账号输入
        self.username_input = QLineEdit(self.runtime_username)
        layout.addRow("账号:", self.username_input)

        # 密码输入
        self.password_input = QLineEdit(self.runtime_password)
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addRow("密码:", self.password_input)

        # 开始执行按钮
        self.execute_button = QPushButton("开始执行 Edge 自动化")
        self.execute_button.setFont(QFont('Arial', 12, QFont.Bold))
        self.execute_button.clicked.connect(self.start_automation)

        # 保存配置按钮
        self.save_button = QPushButton("保存当前配置")
        self.save_button.clicked.connect(self.save_config)

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.execute_button)
        layout.addRow(button_layout)

        # 日志输出区域
        log_label = QLabel("执行日志:")
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addRow(log_label)
        layout.addRow(self.log_output)

    def log(self, message, color="black"):
        """向日志区域输出消息"""
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

    # --- 3. 配置页面 (Configuration Panel) ---
    def create_config_page(self):
        config_page = QWidget()
        self.tab_widget.addTab(config_page, "元素配置")

        layout = QVBoxLayout(config_page)

        # 帮助信息
        guide_label = QLabel("<b>智能定位指南:</b><br>"
                             "1. <code>//div[@id='root']</code> 或 <code>.my-class</code> (直接 XPath/CSS)<br>"
                             "2. <code>placeholder=\"请输入\"</code> (自动识别属性: key=\"value\")<br>"
                             "3. <code>&lt;span&gt;登录</code> (标签+文本: &lt;tag&gt;text)<br>"
                             "4. <code>登录</code> (纯文本: Text)")
        guide_label.setTextFormat(Qt.RichText)
        guide_label.setWordWrap(True)
        layout.addWidget(guide_label)

        # 元素配置表格
        self.element_table = QTableWidget()
        self.element_table.setColumnCount(2)
        self.element_table.setHorizontalHeaderLabels(['元素名称 (变量名)', '定位字符串 (定位值)'])
        self.element_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.element_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

        self.load_table_data()

        layout.addWidget(self.element_table)

        # 按钮
        add_button = QPushButton("添加新元素")
        add_button.clicked.connect(self.add_row)
        layout.addWidget(add_button)

    def load_table_data(self):
        """将配置字典加载到表格"""
        self.element_table.setRowCount(len(self.element_config))
        for i, item in enumerate(self.element_config):
            name_item = QTableWidgetItem(item.get("name", f"Element_{i + 1}"))
            locator_item = QTableWidgetItem(item.get("locator", ""))
            self.element_table.setItem(i, 0, name_item)
            self.element_table.setItem(i, 1, locator_item)

    def get_table_data(self):
        """从表格获取当前的配置数据"""
        data = []
        for row in range(self.element_table.rowCount()):
            name_item = self.element_table.item(row, 0)
            locator_item = self.element_table.item(row, 1)
            if name_item and locator_item and name_item.text().strip():
                data.append({
                    "name": name_item.text().strip(),
                    "locator": locator_item.text().strip()
                })
        return data

    def add_row(self):
        """向表格添加一行"""
        row_count = self.element_table.rowCount()
        self.element_table.insertRow(row_count)
        self.element_table.setItem(row_count, 0, QTableWidgetItem(f"New_Element_{row_count + 1}"))

    # --- 4. 自动化执行核心 ---
    def start_automation(self):
        """开始 Edge 浏览器自动化流程"""
        if not SELENIUM_AVAILABLE:
            self.log("ERROR: Selenium 库未安装。请先安装。", "red")
            return

        self.log("--- 自动化执行开始 ---", "blue")
        self.save_config()  # 确保使用最新的配置和运行时值

        url = self.url_input.text()
        username = self.username_input.text()
        password = self.password_input.text()
        config_data = self.get_table_data()

        # 将配置数据转换为 (name: (By, value)) 字典
        parsed_config = {}
        for item in config_data:
            by, value = LocatorParser.parse(item["locator"])
            if by and value:
                parsed_config[item["name"]] = (by, value)
            else:
                self.log(f"警告: 元素 '{item['name']}' 的定位字符串无效或为空，跳过。", "red")

        # 检查关键元素是否配置
        try:
            user_locator = parsed_config['账号输入框']
            pass_locator = parsed_config['密码输入框']
            login_locator = parsed_config['登录按钮']
        except KeyError as e:
            self.log(f"FATAL ERROR: 关键元素 {e} 未配置或名称错误。请检查配置。", "red")
            return

        # 检查 Edge 驱动程序
        try:
            # 假设 msedgedriver 已经添加到 PATH 或位于已知位置
            service = Service()  # 使用默认路径查找 msedgedriver
            driver = webdriver.Edge(service=service)
            self.log("Edge 浏览器启动成功。", "green")
        except Exception as e:
            self.log(f"FATAL ERROR: Edge 浏览器启动失败。请确保安装了 Edge 浏览器并配置了 msedgedriver: {e}", "red")
            return

        # 自动化步骤
        try:
            # 1. 访问 URL
            self.log(f"访问 URL: {url}...")
            driver.get(url)

            # 等待页面加载（最多 10 秒）
            wait = WebDriverWait(driver, 10)

            # 2. 查找并输入账号
            self.log(f"输入账号: {username}")
            user_element = wait.until(EC.presence_of_element_located(user_locator))
            user_element.clear()
            user_element.send_keys(username)

            # 3. 查找并输入密码
            self.log(f"输入密码: *********")
            pass_element = wait.until(EC.presence_of_element_located(pass_locator))
            pass_element.clear()
            pass_element.send_keys(password)

            # 4. 点击登录
            self.log("点击登录按钮...")
            login_element = wait.until(EC.element_to_be_clickable(login_locator))
            login_element.click()

            # 5. 初始流程完成，等待后续操作
            self.log("登录操作完成，脚本暂停等待后续流程指令...", "green")
            # 实际应用中，你可以在这里添加一个循环或事件监听，等待用户在UI中触发下一步操作

        except Exception as e:
            self.log(f"自动化执行中发生错误: {e}", "red")
        finally:
            # 暂时不关闭浏览器，以便观察登录结果
            # driver.quit()
            self.log("请手动关闭 Edge 浏览器。", "blue")

        self.log("--- 自动化执行结束 ---", "blue")


if __name__ == '__main__':
    # 将 LocatorParser 的代码放在 AutomationToolUI 类的定义之前，或者确保它在一个单独的文件中。
    # 为了方便运行，我们假设它们在同一个文件中，将 LocatorParser 代码块放在文件开头。
    app = QApplication(sys.argv)
    window = AutomationToolUI()
    window.show()
    sys.exit(app.exec_())