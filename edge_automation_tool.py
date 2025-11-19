from selenium.webdriver.common.by import By
import re


class LocatorParser:
    """
    智能定位解析器：根据用户输入的字符串自动判断最佳的 Selenium 定位策略。

    定位指南：
    1. //div[@id='root'] 或 .my-class (XPath/CSS) -> By.XPATH 或 By.CSS_SELECTOR
    2. 属性=\"值\" (属性定位) -> By.CSS_SELECTOR
    3. <tag>文本 (标签+文本) -> By.XPATH (查找特定标签，使用 normalize-space(.) 忽略子标签，精确匹配文本)
    4. 纯文本 (Text) -> By.XPATH (查找任何标签内含特定文本，模糊匹配)
    """

    @staticmethod
    def parse(locator_str: str) -> tuple:
        """解析定位字符串，返回 (By, 定位值)"""
        locator_str = locator_str.strip()

        if not locator_str:
            return None, None

        # --- 1. XPath / CSS Selector (以 // 或 . 或 # 开头) ---
        if locator_str.startswith('//') or locator_str.startswith('.') or locator_str.startswith('#'):
            if locator_str.startswith('//'):
                print(f"解析定位器: '{locator_str}' -> By.XPATH")
                return (By.XPATH, locator_str)
            else:
                print(f"解析定位器: '{locator_str}' -> By.CSS_SELECTOR")
                return (By.CSS_SELECTOR, locator_str)

        # --- 2. 属性=\"值\" 定位 (包含 = 和引号) ---
        # 匹配 key="value" 或 key='value' 格式
        attr_match = re.match(r'^(\w+)=\"(.*?)\"$', locator_str) or re.match(r"^(\w+)='(.*?)'$", locator_str)
        if attr_match:
            attr_key = attr_match.group(1)
            attr_value = attr_match.group(2)
            css_selector = f"[{attr_key}='{attr_value}']"
            print(f"解析定位器: '{locator_str}' -> By.CSS_SELECTOR ({css_selector})")
            return (By.CSS_SELECTOR, css_selector)

        # --- 3. <tag>文本 (标签+文本) 定位 【已优化】---
        if re.match(r"^<\w+>.*$", locator_str):
            tag_name = re.match(r"^<(\w+)>", locator_str).group(1)
            text_content = locator_str[len(tag_name) + 2:].strip()

            # 使用 normalize-space(.) 忽略子标签和空格，精确匹配元素的全部文本内容
            xpath = f"//{tag_name}[normalize-space(.)='{text_content}']"

            print(f"解析定位器: '{locator_str}' -> By.XPATH (标签+文本: {xpath})")
            return (By.XPATH, xpath)

        # --- 4. 纯文本定位 (默认 fallback，模糊匹配) ---
        # XPath: 查找包含该文本的任何元素 (模糊匹配)
        xpath = f"//*[contains(text(), '{locator_str}')]"
        print(f"解析定位器: '{locator_str}' -> By.XPATH (纯文本: {xpath})")
        return (By.XPATH, xpath)