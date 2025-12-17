import time
from selenium.webdriver.common.by import By
from browser_utils import BrowserBase
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class NavManager(BrowserBase):
    def nav_to_listing_system(self):
        self.log("--- 步骤2: 导航至刊登系统 ---", "blue")

        # 1. 检查是否已在正确页面 (避免重复导航)
        if "message_center" in self.driver.current_url or "product_list" in self.driver.current_url:
            self.log("✅ 已在刊登系统，跳过导航", "green")
            return True

        try:
            # 2. 强制点击 ERP 菜单
            # 使用 force_click 避免 hover 菜单弹出的遮挡问题
            erp_menu = self.find('导航_ERP菜单')
            self.force_click(erp_menu, "ERP菜单")
            time.sleep(0.5)  # 稍作缓冲

            # 3. 强制点击 刊登管理
            nav_btn = self.find('导航_刊登管理')

            # 记录当前窗口句柄，用于捕捉新窗口
            handles_before = self.driver.window_handles
            self.force_click(nav_btn, "刊登管理")

            # 4. 切换到新窗口
            WebDriverWait(self.driver, 10).until(EC.new_window_is_opened(handles_before))
            new_window = [w for w in self.driver.window_handles if w not in handles_before][0]
            self.driver.switch_to.window(new_window)

            # 5. 确保页面加载
            self.wait_loading_mask()
            self.log("✅ 导航成功，进入工作台", "green")
            return True

        except Exception as e:
            self.log(f"❌ 导航失败: {e}", "red")
            return False

    def enter_product_list_page(self):
        """确保进入产品列表页"""
        if "product_list" in self.driver.current_url:
            return True

        self.log("📂 切换至产品列表...", "blue")
        try:
            # 尝试点击左侧菜单
            menu_btn = self.find('菜单_产品列表', optional=True)
            if menu_btn:
                self.force_click(menu_btn, "产品列表菜单")
            else:
                # 兜底：直接跳转 URL
                self.driver.get("https://salecentersaas.yibainetwork.com/#/product_list")

            self.wait_loading_mask()
            return True
        except Exception as e:
            self.log(f"❌ 切换列表页失败: {e}", "red")
            return False

    def search_and_edit_sku(self, sku):
        self.log(f"🔍 搜索 SKU: {sku}", "blue")

        # 0. 确保在列表页
        self.enter_product_list_page()

        # 1. 输入并查询
        inp = self.find('搜索_SKU输入框')
        if not inp: return False

        inp.clear()
        inp.send_keys(sku)

        search_btn = self.find('搜索_查询按钮')
        self.force_click(search_btn, "查询按钮")

        # 等待表格加载
        self.wait_loading_mask()
        time.sleep(1)  # 表格渲染缓冲

        # 2. 【核心】行内强校验逻辑
        # 需求：找到包含 <span class="ui-link">{sku}</span> 的那一行，然后点那一行里的“精细刊登”
        self.log(f"   🧐 正在定位 SKU 所在行...", "gray")

        try:
            # 使用 XPath 定位包含特定 SKU 文本的 TR 元素
            # 逻辑：查找一个 tr，它内部包含一个 class为ui-link 且文本等于 sku 的 span
            # 注意：normalize-space() 用于去除可能的首尾空格
            target_tr_xpath = f"//tr[.//span[contains(@class, 'ui-link') and normalize-space(text())='{sku}']]"

            target_tr = self.driver.find_element(By.XPATH, target_tr_xpath)
            self._highlight(target_tr, "orange")  # 高亮找到的行

            # 在该行内查找“精细刊登”按钮
            edit_btn = target_tr.find_element(By.XPATH, ".//span[contains(text(), '精细刊登')]")

            self.log("   ✅ 校验通过：找到对应 SKU 行及操作按钮", "green")
            self.force_click(edit_btn, "精细刊登")

            # 3. 处理初始弹窗 (点击下一步)
            # 这个弹窗可能加载慢，给足等待时间
            self.log("   ⏳ 等待初始配置弹窗...", "gray")

            # 从配置获取等待时间，默认 10秒
            cfg = self._parse_config().get("弹窗_下一步按钮", {})
            timeout = cfg.get("timeout", 10)

            next_btn = self.find('弹窗_下一步按钮', timeout=timeout)
            if next_btn:
                self.force_click(next_btn, "下一步")
                self.wait_loading_mask()
                return True
            else:
                self.log("❌ 未出现下一步按钮，可能未选中产品或弹窗加载失败", "red")
                return False

        except Exception as e:
            self.log(f"❌ 定位失败: 未在列表中找到 SKU {sku} 或 按钮不可见. 错误: {e}", "red")
            return False

    def force_click(self, element, name=""):
        """JS 强制点击，忽略遮挡"""
        if not element: return
        try:
            self.driver.execute_script("arguments[0].click();", element)
            # self.log(f"   ⚡ 点击: {name}", "gray") 
        except Exception as e:
            self.log(f"❌ 强制点击失败 [{name}]: {e}", "red")