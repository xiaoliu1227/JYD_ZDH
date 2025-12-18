import sys
import os
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from 产品自动刊登.browser_utils import BrowserBase

# 处理跨目录导入 browser_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))



class EditorCore(BrowserBase):
    """
    编辑器核心模块 (B1)
    职责：环境初始化、店铺选择、加载状态判断、站点状态读取、全局弹窗清理
    """

    def setup_listing_env(self, shop_name):
        self.log("--- 步骤3: 编辑器环境初始化 ---", "blue")

        # 1. 选择店铺
        self._select_shop(shop_name)

        # 2. 死等页面加载 (翻译按钮可点击)
        # 从配置中获取超时时间，默认 60s
        trans_cfg = self._parse_config().get("翻译按钮_状态锚点", {})
        wait_time = trans_cfg.get("timeout", 60)
        self.log(f"   ⏳ 等待编辑器核心加载 (超时设定: {wait_time}s)...", "blue")

        try:
            WebDriverWait(self.driver, wait_time).until(
                EC.element_to_be_clickable(trans_cfg['locator'])
            )
            self.log("   ✅ 编辑器加载完毕 (翻译按钮已激活)", "green")
        except Exception:
            # 抛出异常，让主程序捕获后执行 driver.refresh()
            self.log("❌ 页面加载超时 (卡在Loading)，请求刷新重试", "red")
            raise Exception("Editor_Loading_Timeout")

        # 3. 输出初始站点状态
        self.log_all_site_status("初始加载完成")

    def _select_shop(self, shop_name):
        """处理店铺选择与遮罩死锁"""
        self.log(f"🏪 选择店铺: {shop_name}", "black")

        # 定位输入框 (强制点击避免点不中)
        shop_in = self.find('店铺_输入框')
        self.force_click(shop_in, "店铺输入框")

        shop_in.clear()
        shop_in.send_keys(shop_name)

        # 等待下拉菜单出现
        self.find('店铺_下拉选项', timeout=5)

        # 尝试点击匹配项
        # 如果配置的定位符是通用的 li，这里可能需要根据文本过滤
        try:
            # 使用 XPath 模糊匹配文本，确保点到对的
            xpath = f"//div[contains(@class, 'ivu-select-dropdown') and not(contains(@style, 'display: none'))]//li[contains(text(), '{shop_name}')]"
            target = self.driver.find_element(By.XPATH, xpath)
            self.force_click(target, f"店铺选项-{shop_name}")
        except:
            # 兜底：直接找配置里的第一个可见 li
            self.force_click(self.find('店铺_下拉选项'), "店铺下拉项(兜底)")

        self.wait_loading_mask()

    def log_all_site_status(self, stage_name):
        """
        解析 DOM 获取所有站点状态
        结构: div.self_tabs_style -> span.item -> button -> span -> span[2] (状态文本)
        """
        self.log(f"📊 [站点状态报告 - {stage_name}]", "purple")

        try:
            # 1. 找到容器
            container = self.find("状态_容器", optional=True)
            if not container:
                self.log("   ⚠️ 未找到站点状态栏", "gray")
                return

            # 2. 找到所有站点项
            items = container.find_elements(By.XPATH, ".//span[contains(@class, 'item')]")

            status_list = []
            for item in items:
                try:
                    # 提取站点名 (span[1])
                    site_name_el = item.find_element(By.XPATH, "./button/span/span[1]")
                    site_name = site_name_el.text.strip()

                    # 提取状态 (span[2]) - 可能是 hidden 的，使用 textContent
                    status_el = item.find_element(By.XPATH, "./button/span/span[2]")
                    raw_status = status_el.get_attribute("textContent").strip()  # 获取 "[]" 或 "[已推送]"

                    # 3. 状态判断逻辑
                    if "[已推送]" in raw_status:
                        display_status = "✅已推送"
                    elif "[]" in raw_status:
                        display_status = "⬜未推送"
                    else:
                        display_status = f"⚠️{raw_status}"  # 其他状态如 [无电压]

                    status_list.append(f"{site_name}: {display_status}")
                except:
                    continue

            # 4. 打印日志
            if status_list:
                self.log(" | ".join(status_list), "black")
            else:
                self.log("   ⚠️ 未解析到任何站点信息", "gray")

        except Exception as e:
            self.log(f"❌ 状态解析异常: {e}", "gray")

    def force_close_all_popups(self):
        """
        强力清理页面残留弹窗
        策略：循环查找并点击所有可见的 '关闭(X)' 和 '确定' 按钮，直到页面清净
        """
        self.log("🧹 执行全局弹窗清理...", "gray")
        max_loops = 5
        for _ in range(max_loops):
            try:
                # 重新查找所有可能的关闭/确定按钮
                # ivu-modal-close 是通用的 X 按钮
                closes = self.driver.find_elements(By.CLASS_NAME, "ivu-modal-close")
                # 查找包含“确定”的按钮
                confirms = self.driver.find_elements(By.XPATH, "//span[normalize-space(text())='确定']")

                clicked_any = False

                for btn in closes + confirms:
                    if btn.is_displayed():
                        try:
                            self.driver.execute_script("arguments[0].click();", btn)
                            clicked_any = True
                            time.sleep(0.5)
                        except:
                            pass

                if not clicked_any:
                    break  # 没有可点击的弹窗了，退出循环
            except:
                break

    def force_click(self, element, name=""):
        """继承自 BrowserBase 但强化日志"""
        if not element: return
        try:
            self.driver.execute_script("arguments[0].click();", element)
            # self.log(f"   ⚡ 点击: {name}", "gray")
        except Exception as e:
            self.log(f"❌ 点击失败 [{name}]: {e}", "red")