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
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException


class WorkerSignals(QObject):
    log = pyqtSignal(str)
    error = pyqtSignal(str)
    success = pyqtSignal(str)
    finished = pyqtSignal()


class SeleniumWorker(QThread):
    def __init__(self, config, workflow_name, credentials):
        super().__init__()
        self.config = config
        self.workflow_name = workflow_name
        self.workflow = config.get('workflows', {}).get(workflow_name)
        self.credentials = credentials
        self.signals = WorkerSignals()
        self.driver = None
        self.wait = None

        # --- 配置参数 ---
        # 整个流程失败后的重试次数
        self.WORKFLOW_MAX_RETRIES = 2
        # 单个输入步骤校验失败后的重试次数
        self.INPUT_MAX_RETRIES = 3

    def log(self, message):
        self.signals.log.emit(message)

    def get_locator(self, key):
        """智能解析定位器 (包含对 span 标签等的支持)"""
        try:
            elements = self.config.get('elements', {})
            if key not in elements:
                # 允许 key 为空的情况(针对非强制步骤)
                return None

            element_info = elements[key]
            value_str = element_info.get('value', '').strip()

            if not value_str:
                return None

            # 规则 1: XPath
            if value_str.startswith(('//', '/', '(')):
                return (By.XPATH, value_str)
            # 规则 2: CSS
            if value_str.startswith(('.', '#')) or re.match(r'^\w*\[.+\]', value_str):
                return (By.CSS_SELECTOR, value_str)
            # 规则 3: 属性
            match_attr = re.match(r'^([\w.-]+)\s*=\s*["\'](.+)["\']$', value_str)
            if match_attr:
                attr = match_attr.group(1).lower()
                val = match_attr.group(2)
                if attr == 'id': return (By.ID, val)
                if attr == 'name': return (By.NAME, val)
                if attr == 'class': return (By.CLASS_NAME, val)
                return (By.XPATH, f"//*[@{attr}='{val}']")
            # 规则 4: <tag>text
            match_html = re.match(r'^<(\w+)>(.+)$', value_str)
            if match_html:
                return (By.XPATH, f"//{match_html.group(1).lower()}[normalize-space()='{match_html.group(2).strip()}']")
            # 规则 5: 默认纯文本
            return (By.XPATH, f"//*[normalize-space()='{value_str}']")
        except Exception as e:
            raise ValueError(f"解析定位器 '{key}' 失败: {e}")

    def substitute_value(self, value_str):
        if not value_str: return ""
        val = str(value_str)
        val = val.replace("{username}", self.credentials.get('username', ''))
        val = val.replace("{password}", self.credentials.get('password', ''))
        return val

    # --- 核心功能：安全输入 (带校验和重试) ---
    def safe_type(self, locator, text):
        """
        输入文字，并检查是否输入成功。
        如果失败，清空重试。
        """
        for attempt in range(self.INPUT_MAX_RETRIES):
            try:
                element = self.wait.until(EC.element_to_be_clickable(locator))

                # 1. 尝试点击激活
                element.click()
                # 2. 清空
                element.clear()
                # 3. 输入
                element.send_keys(text)

                # 4. 【关键步骤】校验输入结果
                # 获取输入框当前的值
                current_val = element.get_attribute('value')

                if current_val == text:
                    return True  # 成功！

                self.log(
                    f"输入校验失败 (尝试 {attempt + 1}/{self.INPUT_MAX_RETRIES}): 期望 '{text}', 实际 '{current_val}'")
                time.sleep(0.5)  # 稍等再试

            except Exception as e:
                self.log(f"输入出错 (尝试 {attempt + 1}): {e}")
                time.sleep(1)

        raise Exception(f"经过 {self.INPUT_MAX_RETRIES} 次尝试，仍无法正确输入内容。")

    def run(self):
        if not self.workflow:
            self.signals.error.emit("未找到工作流配置。")
            self.signals.finished.emit()
            return

        # --- 宏观容错：流程级重试循环 ---
        for workflow_attempt in range(self.WORKFLOW_MAX_RETRIES + 1):
            try:
                if workflow_attempt > 0:
                    self.log(f"\n>>> 流程执行失败，正在进行第 {workflow_attempt} 次全局重试... <<<")
                    if self.driver:
                        self.log("刷新页面...")
                        self.driver.refresh()
                        time.sleep(3)
                else:
                    self.log("正在启动 Edge 浏览器...")
                    options = EdgeOptions()
                    options.add_argument("--start-maximized")
                    options.add_experimental_option("excludeSwitches", ["enable-logging"])
                    service = EdgeService()
                    self.driver = webdriver.Edge(service=service, options=options)

                # 开始执行步骤
                steps = self.workflow.get('steps', [])
                for i, step in enumerate(steps):
                    action = step.get('action')
                    target = step.get('target')
                    raw_value = step.get('value')
                    timeout = step.get('timeout', 10)

                    self.wait = WebDriverWait(self.driver, timeout)
                    value = self.substitute_value(raw_value)

                    self.log(f"步骤 {i + 1}: {action} {target or ''}")

                    # 1. 跳转
                    if action == "ensure_on_page":
                        if self.driver.current_url != value:
                            self.driver.get(value)

                    # 2. 输入 (使用新的 safe_type)
                    elif action == "type":
                        locator = self.get_locator(target)
                        if not locator: raise ValueError(f"找不到 {target} 的定位配置")
                        self.safe_type(locator, value)

                    # 3. 点击
                    elif action == "click":
                        locator = self.get_locator(target)
                        if not locator: raise ValueError(f"找不到 {target} 的定位配置")
                        # 循环点击直到不报错 (应对短暂遮挡)
                        clicked = False
                        for _ in range(3):
                            try:
                                el = self.wait.until(EC.element_to_be_clickable(locator))
                                el.click()
                                clicked = True
                                break
                            except Exception:
                                time.sleep(1)
                        if not clicked:
                            raise Exception(f"无法点击元素 {target}")

                    # 4. 等待出现
                    elif action == "wait_visible":
                        locator = self.get_locator(target)
                        self.wait.until(EC.visibility_of_element_located(locator))

                    # 5. 等待URL (通常用于判断登录成功)
                    elif action == "wait_url_contains":
                        self.wait.until(EC.url_contains(value))

                    # 6. 可选点击 (不报错)
                    elif action == "if_visible_click":
                        try:
                            check_locator = self.get_locator(step.get('check_target'))
                            if not check_locator:
                                self.log("跳过可选点击: 未配置检测目标")
                                continue

                            WebDriverWait(self.driver, 3).until(EC.visibility_of_element_located(check_locator))
                            self.log("检测到可选目标，尝试点击...")

                            click_locator = self.get_locator(target)
                            if click_locator:
                                self.driver.find_element(*click_locator).click()
                        except TimeoutException:
                            pass  # 正常跳过
                        except Exception as e:
                            self.log(f"可选点击执行时忽略错误: {e}")

                # 如果所有步骤都走完了，没有抛出异常，说明成功了
                self.signals.success.emit("工作流执行成功！")
                break  # 跳出重试循环

            except Exception as e:
                # 捕获这一轮的错误
                err_msg = f"流程执行出错: {str(e)}"
                self.log(err_msg)

                # 如果这是最后一次尝试，依然失败，那就真的失败了
                if workflow_attempt == self.WORKFLOW_MAX_RETRIES:
                    self.signals.error.emit(
                        f"已重试 {self.WORKFLOW_MAX_RETRIES} 次，最终失败。\n错误详情: {traceback.format_exc()}")
                else:
                    # 准备下一次重试
                    time.sleep(2)

        self.signals.finished.emit()
        if self.driver:
            # 等待一会儿再关闭，方便查看
            time.sleep(5)
            self.driver.quit()