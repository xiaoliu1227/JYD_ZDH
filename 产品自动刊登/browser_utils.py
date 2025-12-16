import time
import re
import datetime
from selenium import webdriver
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException


class LocatorParser:
    @staticmethod
    def parse(locator_str: str) -> tuple:
        locator_str = locator_str.strip()
        if not locator_str: return None, None
        if locator_str.startswith('./'): return (By.XPATH, locator_str)
        if locator_str.startswith('//') or locator_str.startswith('(') or locator_str.startswith('.//'):
            return (By.XPATH, locator_str)
        if locator_str.startswith('#') or locator_str.startswith('.'): return (By.CSS_SELECTOR, locator_str)
        attr_match = re.match(r'^([\w-]+)=\"(.*?)\"$', locator_str) or re.match(r"^([\w-]+)='(.*?)'$", locator_str)
        if attr_match: return (By.CSS_SELECTOR, f"[{attr_match.group(1)}='{attr_match.group(2)}']")
        if locator_str.startswith("<span>"):
            text = locator_str.replace("<span>", "").strip()
            return (By.XPATH, f".//span[normalize-space(text())='{text}']")
        return (By.XPATH, f".//*[normalize-space(text())='{locator_str}']")


class BrowserBase:
    def __init__(self, driver, config_data, logger_func):
        self.driver = driver
        self.config_data = config_data
        self.log = logger_func  # 传入回调函数用于打印日志

    def _parse_config(self):
        # 简化版配置解析，建议在 Init 时缓存，这里仅做演示
        parsed = {}
        for mod in self.config_data.get('ELEMENT_CONFIG', []):
            for ele in mod['elements']:
                by, val = LocatorParser.parse(ele['locator'])
                if by:
                    parsed[ele['name']] = {
                        'locator': (by, val),
                        'timeout': ele.get('timeout', 10),
                        'rest': ele.get('rest', 1)
                    }
        return parsed

    def find(self, name, root=None, optional=False):
        cfg = self._parse_config().get(name)
        if not cfg:
            if not optional: self.log(f"❌ 配置缺失: {name}", "red")
            return None

        ctx = root if root else self.driver
        try:
            el = WebDriverWait(ctx, cfg['timeout']).until(EC.visibility_of_element_located(cfg['locator']))
            self._highlight(el)
            if not optional: self.log(f"   ✅ 锁定: [{name}]", "gray")
            if cfg['rest'] > 0: time.sleep(cfg['rest'])
            return el
        except:
            if not optional: self.log(f"❌ 未找到元素: {name}", "red")
            return None

    def safe_click(self, element, name=""):
        if not element: return False
        try:
            element.click()
            return True
        except:
            try:
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except Exception as e:
                self.log(f"❌ 点击失败 [{name}]: {e}", "red")
                return False

    def _highlight(self, element, color="green"):
        try:
            self.driver.execute_script(f"arguments[0].style.border='2px solid {color}'", element)
        except:
            pass

    def wait_loading_mask(self, timeout=15):
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, ".el-loading-mask")))
        except:
            pass