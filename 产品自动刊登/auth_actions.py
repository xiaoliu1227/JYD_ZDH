from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from browser_utils import BrowserBase
import time


class AuthManager(BrowserBase):
    def perform_login(self, username, password, org_code):
        self.log("--- 步骤1: 开始登录 ---", "blue")
        try:
            self.driver.get("https://saaserp-pos.yibainetwork.com")

            # 检测是否已登录
            if "home_page" in self.driver.current_url:
                self.log("✅ 已在首页，跳过登录", "green")
                return True

            user_in = self.find('账号输入框')
            if user_in:
                user_in.clear()
                user_in.send_keys(username)

            pwd_in = self.find('密码输入框')
            if pwd_in:
                pwd_in.clear()
                pwd_in.send_keys(password)

            self.safe_click(self.find('登录按钮'), "登录按钮")

            # 处理组织选择
            confirm_btn = self.find('确认登录按钮', optional=True)
            if confirm_btn:
                org_in = self.find('组织输入框', optional=True)
                if org_in:
                    org_in.send_keys(org_code)
                    time.sleep(0.5)
                    self.safe_click(self.find('组织列表项', optional=True))
                self.safe_click(confirm_btn, "确认登录按钮")

            WebDriverWait(self.driver, 20).until(EC.url_contains("home_page"))
            self.log("✅ 登录成功", "green")
            return True
        except Exception as e:
            self.log(f"❌ 登录流程异常: {e}", "red")
            return False