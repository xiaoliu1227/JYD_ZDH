import time
import re
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException


class LocatorParser:
    @staticmethod
    def parse(locator_str: str) -> tuple:
        if not locator_str: return None, None
        locator_str = str(locator_str).strip()

        # 1. 优先识别 ./ 开头的相对路径 (XPath)
        if locator_str.startswith('./'):
            return (By.XPATH, locator_str)

        # 2. 常规 XPath
        if locator_str.startswith('//') or locator_str.startswith('(') or locator_str.startswith('.//'):
            return (By.XPATH, locator_str)

        # 3. CSS ID/Class
        if locator_str.startswith('#') or locator_str.startswith('.'):
            return (By.CSS_SELECTOR, locator_str)

        # 4. 属性匹配 (支持 key="value" 或 key='value')
        attr_match = re.match(r'^([\w-]+)=\"(.*?)\"$', locator_str) or re.match(r"^([\w-]+)='(.*?)'$", locator_str)
        if attr_match:
            return (By.CSS_SELECTOR, f"[{attr_match.group(1)}='{attr_match.group(2)}']")

        # 5. 属性选择器 [type='text']
        if locator_str.startswith('['):
            return (By.CSS_SELECTOR, locator_str)

        # 6. Span 文本简写 (你的配置中大量使用)
        if locator_str.startswith("<span>"):
            text = locator_str.replace("<span>", "").strip()
            return (By.XPATH, f".//span[normalize-space(text())='{text}']")

        # 7. 纯文本智能定位 (兜底)
        return (By.XPATH, f".//*[normalize-space(text())='{locator_str}']")


class BrowserBase:
    def __init__(self, driver, config_data, logger_func):
        self.driver = driver
        self.config_data = config_data
        self.log = logger_func
        self._cached_config = None  # 缓存解析结果

    def _parse_config(self):
        # 简单的缓存机制，防止每次 find 都重新解析一遍正则
        if self._cached_config: return self._cached_config

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
        self._cached_config = parsed
        return parsed

    # [关键修复] 增加了 timeout 参数，解决报错问题
    def find(self, name, root=None, optional=False, timeout=None):
        cfg = self._parse_config().get(name)
        if not cfg:
            if not optional: self.log(f"❌ 配置缺失: {name}", "red")
            return None

        ctx = root if root else self.driver

        # [逻辑核心] 如果传入了 timeout，就用传入的；否则用配置文件的
        use_timeout = timeout if timeout is not None else cfg['timeout']

        try:
            el = WebDriverWait(ctx, use_timeout).until(EC.visibility_of_element_located(cfg['locator']))
            self._highlight(el)
            # if not optional: self.log(f"   ✅ 锁定: [{name}]", "gray") # 减少日志刷屏
            if cfg['rest'] > 0: time.sleep(cfg['rest'])
            return el
        except:
            # 只有非 optional 且超时时间较长时才报红，避免高频检测时刷屏
            if not optional and use_timeout > 3:
                self.log(f"❌ 未找到元素: {name} (超时 {use_timeout}s)", "red")
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