import time
import re
import traceback
from PyQt5.QtCore import QThread, pyqtSignal, QObject

from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException


class WorkerSignals(QObject):
    log = pyqtSignal(str)
    error = pyqtSignal(str)
    success = pyqtSignal(str)
    finished = pyqtSignal()


class BaseExecutor(QThread):
    """
    基础执行器：提供底层WebDriver控制、智能定位、动作方法和重试机制。
    所有的流程文件（如 process_login.py）都将继承此类。
    """

    def __init__(self, config, credentials_list, process_class):
        super().__init__()
        self.config = config
        self.credentials_list = credentials_list
        self.signals = WorkerSignals()
        self.process_instance = process_class(self)  # 实例化具体的流程类

        self.driver = None
        self.wait = None
        self.current_creds = {}

        # --- 配置参数 ---
        self.WORKFLOW_MAX_RETRIES = 2
        self.INPUT_MAX_RETRIES = 3

    def log(self, message):
        self.signals.log.emit(message)

    # --- 核心方法 1: 智能定位 ---
    def get_locator(self, key):
        """智能解析定位器 (从 config.json 的 elements 中读取)"""
        try:
            elements = self.config.get('elements', {})
            if key not in elements: return None

            element_info = elements[key]
            value_str = element_info.get('value', '').strip()
            if not value_str: return None

            # 规则 1-5: XPath, CSS, 属性, 标签+文本
            if value_str.startswith(('//', '/', '(')): return (By.XPATH, value_str)
            if value_str.startswith(('.', '#')) or re.match(r'^\w*\[.+\]', value_str): return (By.CSS_SELECTOR,
                                                                                               value_str)
            match_attr = re.match(r'^([\w.-]+)\s*=\s*["\'](.+)["\']$', value_str)
            if match_attr:
                attr, val = match_attr.group(1).lower(), match_attr.group(2)
                if attr == 'id': return (By.ID, val)
                if attr == 'name': return (By.NAME, val)
                if attr == 'class': return (By.CLASS_NAME, val)
                return (By.XPATH, f"//*[@{attr}='{val}']")
            match_html = re.match(r'^<(\w+)>(.+)$', value_str)
            if match_html:
                return (By.XPATH, f"//{match_html.group(1).lower()}[normalize-space()='{match_html.group(2).strip()}']")
            return (By.XPATH, f"//*[normalize-space()='{value_str}']")
        except Exception as e:
            raise ValueError(f"解析定位器 '{key}' 失败: {e}")

    # --- 核心方法 2: 变量替换 ---
    def substitute_value(self, value_str):
        if not value_str: return ""
        val = str(value_str)
        val = val.replace("{username}", self.current_creds.get('username', ''))
        val = val.replace("{password}", self.current_creds.get('password', ''))
        val = val.replace("{sku}", self.current_creds.get('sku', ''))  # 兼容产品流程
        return val

    # --- 核心方法 3: 安全输入 (供流程文件调用) ---
    def safe_type(self, target_key, text):
        locator = self.get_locator(target_key)
        if not locator: raise ValueError(f"找不到 {target_key} 的定位配置")

        for attempt in range(self.INPUT_MAX_RETRIES):
            try:
                element = self.wait.until(EC.element_to_be_clickable(locator))
                element.click()
                element.clear()
                element.send_keys(text)
                if element.get_attribute('value') == text: return True
                self.log(f"输入校验失败 (尝试 {attempt + 1}/{self.INPUT_MAX_RETRIES})")
                time.sleep(0.5)
            except Exception as e:
                self.log(f"输入出错 (尝试 {attempt + 1}): {e}")
                time.sleep(1)
        raise Exception(f"经过 {self.INPUT_MAX_RETRIES} 次尝试，仍无法正确输入内容。")

    # --- 核心方法 4: 基础动作 (供流程文件调用) ---
    def click(self, target_key, timeout=10):
        locator = self.get_locator(target_key)
        if not locator: raise ValueError(f"找不到 {target_key} 的定位配置")
        self.wait = WebDriverWait(self.driver, timeout)

        for _ in range(3):
            try:
                el = self.wait.until(EC.element_to_be_clickable(locator))
                el.click()
                return
            except Exception:
                time.sleep(1)
        raise Exception(f"无法点击元素 {target_key}")

    def hover(self, target_key, timeout=10):
        locator = self.get_locator(target_key)
        if not locator: raise ValueError(f"找不到 {target_key} 的定位配置")
        self.wait = WebDriverWait(self.driver, timeout)
        element = self.wait.until(EC.presence_of_element_located(locator))
        ActionChains(self.driver).move_to_element(element).perform()
        self.log("执行鼠标悬停操作。")
        time.sleep(1)

    # --- 核心方法 5: 验证/跳转 ---
    def ensure_on_page(self, url, timeout=10):
        if self.driver.current_url != url:
            self.driver.get(url)
        self.wait_url_contains(url.split('#/')[-1], timeout=timeout)  # 假设锚点是页面的核心标识

    def wait_url_contains(self, fragment, timeout=10):
        self.wait = WebDriverWait(self.driver, timeout)
        self.wait.until(EC.url_contains(fragment))

    def wait_visible(self, target_key, timeout=10):
        locator = self.get_locator(target_key)
        self.wait = WebDriverWait(self.driver, timeout)
        self.wait.until(EC.visibility_of_element_located(locator))

    def check_and_close_popup(self, check_key, close_key):
        """检查弹窗并关闭"""
        try:
            check_locator = self.get_locator(check_key)
            if check_locator:
                WebDriverWait(self.driver, 3).until(EC.visibility_of_element_located(check_locator))
                self.log("检测到弹窗，尝试点击关闭...")
                self.click(close_key, timeout=3)
        except TimeoutException:
            pass
        except Exception as e:
            self.log(f"可选点击执行时忽略错误: {e}")

    # --- 核心方法 6: 数据提取 ---
    def get_table_data(self, target_key, timeout=10):
        locator = self.get_locator(target_key)
        if not locator:
            self.log(f"无法提取表格：未配置定位器 {target_key}")
            return []

        self.wait = WebDriverWait(self.driver, timeout)
        table_element = self.wait.until(EC.presence_of_element_located(locator))

        table_data = []
        rows = table_element.find_elements(By.TAG_NAME, "tr")

        self.log(f"--- 提取表格数据 ({target_key}) ---")

        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if not cols: cols = row.find_elements(By.TAG_NAME, "th")

            row_data = [col.text.strip() for col in cols if col.text.strip()]
            if row_data:
                self.log(f"| {' | '.join(row_data)} |")
                table_data.append(row_data)

        self.log("--- 表格数据提取完毕 ---")
        return table_data

    # --- 运行调度 (QThread 入口) ---
    def run(self):
        # ... (账号循环逻辑) ...
        try:
            self.log("启动浏览器...")
            options = EdgeOptions()
            options.add_argument("--start-maximized")
            options.add_experimental_option("excludeSwitches", ["enable-logging"])
            service = EdgeService()
            self.driver = webdriver.Edge(service=service, options=options)

            total = len(self.credentials_list)
            for index, creds in enumerate(self.credentials_list):
                self.current_creds = creds
                alias = creds.get('alias', '未知')
                self.log(f"\n========== 正在处理账号 [{index + 1}/{total}]: {alias} ==========")

                try:
                    self.run_process_with_retry()  # 运行具体的流程
                    self.log(f"账号 {alias} 执行成功！")
                except Exception as e:
                    self.log(f"!!! 账号 {alias} 执行失败: {e}")

                if index < total - 1:
                    self.log("清理 Cookie，准备切换下一个账号...")
                    try:
                        self.driver.delete_all_cookies(); self.driver.get("about:blank"); time.sleep(1)
                    except:
                        pass

            self.log("\n所有选定账号处理完毕。")

        except Exception as e:
            self.log(f"浏览器/驱动层级错误: {e}")
        finally:
            if self.driver: time.sleep(3); self.driver.quit()
            self.signals.finished.emit()

    def run_process_with_retry(self):
        """执行单次工作流的逻辑 (支持流程级重试)"""
        for attempt in range(self.WORKFLOW_MAX_RETRIES + 1):
            try:
                if attempt > 0:
                    self.log(f"流程重试 ({attempt}/{self.WORKFLOW_MAX_RETRIES})...")
                    self.driver.refresh();
                    time.sleep(3)

                # 【关键】调用流程文件中的 execute_workflow 方法
                self.process_instance.execute_workflow()

                return  # 成功执行则返回

            except Exception as e:
                err_msg = f"流程执行出错: {str(e)}"
                self.log(err_msg)

                if attempt == self.WORKFLOW_MAX_RETRIES:
                    full_trace = traceback.format_exc()
                    print("\n========== 自动化错误追踪 (控制台输出) ==========")
                    print(full_trace)
                    print("====================================================\n")
                    raise Exception(f"最终失败。\n错误详情:\n{full_trace}")
                time.sleep(2)