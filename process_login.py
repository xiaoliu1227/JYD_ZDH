from base_executor import BaseExecutor


class LoginProcess:
    """
    流程 1: 完整的登录、选择组织、关闭通知流程
    """

    def __init__(self, executor: BaseExecutor):
        self.ex = executor  # 存储 BaseExecutor 实例，通过它来调用核心方法
        self.log = self.ex.log

    def execute_workflow(self):
        self.log("--- 启动登录流程 ---")

        # 1. 确保在登录页
        self.ex.ensure_on_page("https://saaserp-pos.yibainetwork.com/#/login_page")

        # 2. 输入账号和密码
        self.ex.safe_type("login_page_username_input", self.ex.substitute_value("{username}"))
        self.ex.safe_type("login_page_password_input", self.ex.substitute_value("{password}"))

        # 3. 点击登录
        self.ex.click("login_page_login_button")

        # 4. 选择组织弹窗
        self.ex.wait_visible("org_popup_dialog", timeout=5)
        self.ex.safe_type("org_popup_input", "156")  # 直接输入156
        self.ex.wait_visible("org_popup_list_item", timeout=3)
        self.ex.click("org_popup_list_item")  # 点击列表项
        self.ex.click("org_popup_confirm_button")  # 点击确认登录

        # 5. 等待跳转
        self.ex.wait_url_contains("home_page", timeout=10)

        # 6. 关闭通知弹窗 (可选)
        self.ex.check_and_close_popup(
            "home_page_notification_popup",
            "home_page_notification_close_button"
        )

        self.log("--- 登录流程执行完毕 ---")