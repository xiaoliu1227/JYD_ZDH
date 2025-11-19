from base_executor import BaseExecutor


class LogoutProcess:
    """
    流程 3: 退出登录流程
    """

    def __init__(self, executor: BaseExecutor):
        self.ex = executor
        self.log = self.ex.log

    def execute_workflow(self):
        self.log("--- 启动退出登录流程 ---")

        # 1. 点击退出登录按钮 (假设它在页面上可见)
        self.ex.click("home_page_logout_button", timeout=5)

        # 2. 等待页面跳转回登录页 (URL中应不再包含 home_page)
        self.ex.wait_url_contains("login_page", timeout=5)

        self.log("--- 退出登录流程执行完毕 ---")