import time

from 产品自动刊登.actions.editor_submit import EditorSubmit


class EditorManager(EditorSubmit):
    """
    编辑器总控模块 (Facade)
    职责：统筹调用 Core/Features/Submit 各层逻辑，提供对外统一接口
    """

    def process_full_cycle(self, shop_name):
        """执行一个 SKU 的完整刊登周期"""

        # 1. 环境初始化 (选店铺 + 等待加载)
        self.setup_listing_env(shop_name)

        # 2. 功能执行 (AI / 图片)
        self.run_ai_optimization()
        # self.handle_images_placeholder() # 预留

        # 3. 提交流水线 (保存->同步->翻译->提交->修复)
        self.process_submission_flow()

        # 4. 退出编辑
        self.exit_editor()

    def exit_editor(self):
        """退出编辑器返回列表"""
        self.log("🔚 任务结束，正在退出编辑器...", "blue")

        # 点击取消
        self.force_click(self.find("按钮_取消"), "取消按钮")
        time.sleep(1)

        # 如果有确认退出弹窗
        confirm_exit = self.find("退出确认_确定关闭", optional=True, timeout=3)
        if confirm_exit and confirm_exit.is_displayed():
            self.force_click(confirm_exit, "确认关闭")

        self.wait_loading_mask()
        self.log("✅ 已返回列表页", "green")