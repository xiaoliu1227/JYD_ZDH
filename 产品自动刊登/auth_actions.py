import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from browser_utils import BrowserBase


class AuthManager(BrowserBase):
    def perform_login(self, username, password, org_code):
        self.log("--- 步骤1: 执行登录流程 ---", "blue")

        # 定义最大重试次数
        max_retries = 3

        for attempt in range(max_retries):
            try:
                # 1. 打开登录页
                self.driver.get(self.config_data.get('LOGIN_URL', "https://saaserp-pos.yibainetwork.com"))

                # 2. 智能检测：是否已经登录？
                # 如果当前 URL 包含 home_page，说明浏览器记住了 Session，直接跳过
                if "home_page" in self.driver.current_url:
                    self.log("✅ 检测到已在首页，跳过登录步骤", "green")
                    return True

                # 3. 检测关键元素（账号输入框）
                # 使用 timeout=5 快速检测，如果网速慢可以适当调大，但这里为了快速重试设为 5
                self.log(f"   ⏳ 正在检测登录框 (第 {attempt + 1} 次尝试)...", "gray")
                user_in = self.find('账号输入框', timeout=5, optional=True)

                if not user_in:
                    # 未找到输入框，可能是页面加载失败或白屏
                    self.log(f"⚠️ 未检测到登录输入框，准备刷新页面重试...", "orange")
                    self.driver.refresh()
                    # 刷新后等待几秒让页面重新渲染
                    time.sleep(3)
                    continue  # 进入下一次循环

                # 4. 执行登录操作
                self.log("   🔑 输入账号密码...", "black")
                user_in.clear()
                user_in.send_keys(username)

                pwd_in = self.find('密码输入框')
                if pwd_in:
                    pwd_in.clear()
                    pwd_in.send_keys(password)

                # 点击登录
                self.safe_click(self.find('登录按钮'), "登录按钮")

                # 5. 处理多组织选择弹窗 (如果有)
                # 检测“确认登录”按钮，这通常意味着弹出了组织选择框
                confirm_btn = self.find('确认登录按钮', optional=True, timeout=5)

                if confirm_btn and confirm_btn.is_displayed():
                    self.log("   🏢 检测到组织选择弹窗...", "blue")

                    # 输入组织代码
                    org_in = self.find('组织输入框', optional=True)
                    if org_in:
                        org_in.clear()
                        org_in.send_keys(org_code)
                        time.sleep(0.5)  # 等待下拉筛选

                        # 选择下拉项 (通常是第一个匹配项)
                        self.safe_click(self.find('组织列表项', optional=True), "组织下拉项")

                    # 点击确认
                    self.safe_click(confirm_btn, "确认登录按钮")

                # 6. 最终验证
                # 等待 URL 变化或 Loading 消失
                self.wait_loading_mask()
                WebDriverWait(self.driver, 15).until(EC.url_contains("home_page"))
                self.log("✅ 登录成功，进入首页", "green")
                return True

            except Exception as e:
                self.log(f"❌ 第 {attempt + 1} 次登录尝试发生异常: {e}", "red")
                if attempt < max_retries - 1:
                    self.driver.refresh()
                    time.sleep(3)

        # 循环结束仍未返回 True，说明失败
        self.log("❌ 连续 3 次登录失败，流程终止。", "red")
        return False