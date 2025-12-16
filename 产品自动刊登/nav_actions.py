from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from browser_utils import BrowserBase
import time


class NavManager(BrowserBase):
    def nav_to_listing_system(self):
        self.log("--- 步骤2: 跳转刊登系统 ---", "blue")
        try:
            if "message_center" in self.driver.current_url or "product_list" in self.driver.current_url:
                self.log("✅ 已在刊登系统", "green")
                return True

            erp_menu = self.find('导航_ERP菜单')
            ActionChains(self.driver).move_to_element(erp_menu).perform()

            nav_btn = self.find('导航_刊登管理')
            handles_before = self.driver.window_handles
            self.safe_click(nav_btn, "刊登管理")

            WebDriverWait(self.driver, 10).until(EC.new_window_is_opened(handles_before))
            new_window = [w for w in self.driver.window_handles if w not in handles_before][0]
            self.driver.switch_to.window(new_window)

            WebDriverWait(self.driver, 15).until(EC.url_contains("message_center"))
            self.log("✅ 进入消息中心", "green")
            return True
        except Exception as e:
            self.log(f"❌ 导航失败: {e}", "red")
            return False

    def enter_product_page(self):
        # [核心] 如果已经在列表页，直接返回
        if "product_list" in self.driver.current_url:
            self.wait_loading_mask()
            return True

        self.log("📂 导航至产品列表...", "blue")
        try:
            # 兼容：如果菜单收起了，需要先移到菜单上
            menu_listing = self.find('菜单_刊登管理', optional=True)
            if menu_listing:
                try:
                    ActionChains(self.driver).move_to_element(menu_listing).perform()
                    self.safe_click(self.find('菜单_产品列表', optional=True))
                except:
                    # 如果 Hover 失败，尝试直接点击
                    pass

            # 兜底：如果上面没点到，直接 JS 跳转 URL 可能更快
            # self.driver.get("https://salecentersaas.yibainetwork.com/#/product_list")

            WebDriverWait(self.driver, 15).until(EC.url_contains("product_list"))
            self.wait_loading_mask()
            return True
        except Exception as e:
            self.log(f"❌ 切换产品列表失败: {e}", "red")
            return False

    def search_and_edit_sku(self, sku):
        self.log(f"🔍 搜索 SKU: {sku}", "blue")
        inp = self.find('搜索_SKU输入框')
        if not inp: return False

        inp.clear()
        inp.send_keys(sku)

        self.safe_click(self.find('搜索_查询按钮'), "查询")
        time.sleep(2)
        self.wait_loading_mask()

        try:
            cfg = self._parse_config().get('列表_刊登按钮')
            btns = self.driver.find_elements(*cfg['locator'])
            visible_btns = [b for b in btns if b.is_displayed()]

            if len(visible_btns) == 1:
                self.safe_click(visible_btns[0], "精细刊登")
                return True
            else:
                self.log(f"⚠️ SKU搜索结果不唯一或未找到", "orange")
                return False
        except Exception as e:
            self.log(f"❌ 搜索操作异常: {e}", "red")
            return False