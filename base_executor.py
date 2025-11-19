import time
import re
import traceback
import importlib.util  # 用于在 BaseExecutor 内部动态加载流程文件
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


# 导入 PROCESS_MODULES (假设它在 main_app.py 中是全局可访问的，但为了模块化，我们把它放在此处)
# 在实际运行中，PROCESS_MODULES 应该被正确地传递或导入。这里我们假设可以获取到。
from config_manager import PROCESS_MODULES

class BaseExecutor(QThread):
    """
    序列执行器：负责启动单次会话，并按顺序调用流程文件中的 execute_workflow 方法。
    """

    def __init__(self, config, credentials_list, sequence_data):  # 【修改】直接接收序列数据
        super().__init__()
        self.config = config
        self.credentials_list = credentials_list
        self.sequence_data = sequence_data  # 整个流程序列 (e.g., ['login', 'query', 'logout'])
        self.signals = WorkerSignals()

        self.driver = None
        self.wait = None
        self.current_creds = {}

        self.WORKFLOW_MAX_RETRIES = 2
        self.INPUT_MAX_RETRIES = 3

    # ... (log, get_locator, substitute_value, safe_type 等核心方法保持不变) ...

    def log(self, message):
        self.signals.log.emit(message)

    def get_locator(self, key):
        # (此处省略 get_locator 内部代码，假设其逻辑和功能是完整的)
        try:
            elements = self.config.get('elements', {})
            if key not in elements: return None
            element_info = elements[key]
            value_str = element_info.get('value', '').strip()
            if not value_str: return None

            if value_str.startswith(('//', '/', '(')): return (By.XPATH, value_str)
            if value_str.startswith(('.', '#')): return (By.CSS_SELECTOR, value_str)
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

    def substitute_value(self, value_str):
        if not value_str: return ""
        val = str(value_str)
        val = val.replace("{username}", self.current_creds.get('username', ''))
        val = val.replace("{password}", self.current_creds.get('password', ''))
        val = val.replace("{sku}", self.current_creds.get('sku', ''))
        return val

    def safe_type(self, locator, text):
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

    # ... (其他基础方法 click, hover, get_table_data 等代码块省略，但它们应该在 base_executor.py 中) ...

    # --- 核心调度方法 ---

    def _initialize_driver(self):
        """仅在程序启动时调用一次"""
        self.log("启动 Edge 浏览器...")
        options = EdgeOptions()
        options.add_argument("--start-maximized")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        service = EdgeService()
        self.driver = webdriver.Edge(service=service, options=options)

    def _run_single_process(self, flow_key):
        """执行序列中的一个流程步骤"""

        # 1. 获取流程信息
        process_info = PROCESS_MODULES.get(flow_key)
        if not process_info:
            raise Exception(f"流程 Key '{flow_key}' 未在 PROCESS_MODULES 中定义。")

        # 2. 动态加载类 (此步骤在线程内是安全的)
        spec = importlib.util.spec_from_file_location(process_info['module'], f"{process_info['module']}.py")
        if spec is None:
            raise FileNotFoundError(f"未找到流程文件: {process_info['module']}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        ProcessClass = getattr(module, process_info['class'])

        # 3. 实例化流程 (将 self 传递给流程实例)
        process_instance = ProcessClass(self)

        # 4. 执行流程
        process_instance.execute_workflow()

    def run(self):
        try:
            self._initialize_driver()  # 1. 启动浏览器 (只执行一次)

            # --- 外层：账号循环 ---
            total = len(self.credentials_list)
            for index, creds in enumerate(self.credentials_list):
                self.current_creds = creds
                alias = creds.get('alias', '未知')
                self.log(f"\n========== 正在处理账号 [{index + 1}/{total}]: {alias} ==========")

                try:
                    # 【核心】运行整个序列 (支持流程级重试)
                    self._run_sequence_with_retry()
                    self.log(f"账号 {alias} 序列执行成功！")
                except Exception as e:
                    self.log(f"!!! 账号 {alias} 序列执行失败: {e}")

                # 清理 Cookie，准备下一个账号 (如果不是最后一个)
                if index < total - 1:
                    self.log("清理 Cookie，准备切换下一个账号...")
                    try:
                        self.driver.delete_all_cookies()
                        self.driver.get("about:blank")
                        time.sleep(1)
                    except:
                        pass

            self.signals.success.emit("所有任务执行完毕。")

        except Exception as e:
            self.signals.error.emit(f"浏览器/驱动层级错误: {e}")
            full_trace = traceback.format_exc()
            print("\n========== 自动化错误追踪 (控制台输出) ==========")
            print(full_trace)
            print("====================================================\n")
        finally:
            if self.driver:
                self.log("序列执行完毕，正在关闭浏览器...")
                time.sleep(3)
                self.driver.quit()  # 2. 关闭浏览器 (只执行一次)
            self.signals.finished.emit()

    def _run_sequence_with_retry(self):
        """执行整个序列的流程 (支持全局重试)"""
        for attempt in range(self.WORKFLOW_MAX_RETRIES + 1):
            try:
                if attempt > 0:
                    self.log(f"序列执行失败，正在进行第 {attempt} 次全局重试...")
                    self.driver.refresh()
                    time.sleep(3)

                # --- 顺序执行流程中的每一步骤 ---
                for step_index, flow_key in enumerate(self.sequence_data):
                    self.log(f"\n--- 步骤 {step_index + 1}/{len(self.sequence_data)}: 运行流程 '{flow_key}' ---")
                    self._run_single_process(flow_key)  # 执行单个流程

                return  # 序列执行成功，跳出重试循环

            except Exception as e:
                if attempt == self.WORKFLOW_MAX_RETRIES:
                    raise e  # 达到最大重试次数，抛出异常到上层处理
                time.sleep(2)