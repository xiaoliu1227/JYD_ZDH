import time
from selenium.webdriver.common.by import By

from 产品自动刊登.actions.editor_core import EditorCore


class EditorFeatures(EditorCore):
    """
    编辑器功能模块 (B2)
    职责：AI文案生成、侵权检测、图片处理占位
    """

    def run_ai_optimization(self):
        """执行AI智能文案优化流程"""
        # 1. 读取配置
        ai_cfg = self.config_data.get("AI_SETTINGS", {})
        if not ai_cfg.get("ENABLED", True):
            self.log("🤖 AI 功能已禁用，跳过", "gray")
            return

        self.log("🤖 开始 AI 文案优化...", "blue")

        # 2. 打开 AI 弹窗
        self.force_click(self.find("文案_AI按钮"), "AI智能文案")
        self.wait_loading_mask()

        # 3. 切换模型 (根据配置的目标模型名称)
        target_model = ai_cfg.get("TARGET_MODEL", "DeepSeek V3-A")
        self._switch_ai_model(target_model)

        # 4. 获取该模型的超时设置 (默认60秒)
        timeout = ai_cfg.get("MODELS", {}).get(target_model, {}).get("timeout", 60)

        # 5. 生成文案
        self.log(f"   ⚡ 正在生成文案 (模型: {target_model}, 超时等待: {timeout}s)...", "blue")
        self.force_click(self.find("AI弹窗_生成按钮"), "生成文案")

        # 6. 等待生成结果 (使用特定超时)
        # AI生成时通常有全局遮罩，或者按钮状态变化，wait_loading_mask 是最稳妥的
        self.wait_loading_mask(timeout=timeout)

        # 7. 应用文案
        self.log("   📥 应用生成的文案...", "gray")
        self.force_click(self.find("AI弹窗_应用按钮"), "应用所有文案")

        # 8. 等待应用完成 (遮罩消失)
        self.wait_loading_mask()
        self.log("✅ AI 优化完成", "green")

    def _switch_ai_model(self, target_model):
        """切换到指定的 AI 模型 Tab"""
        try:
            # 逻辑：查找包含目标模型文本的 span
            # HTML示例: <li class="ui-main-tab-box"><span> DeepSeek V3-A </span></li>
            xpath = f"//li[contains(@class, 'ui-main-tab-box')]//span[contains(text(), '{target_model}')]"

            tabs = self.driver.find_elements(By.XPATH, xpath)
            if tabs:
                target_tab = tabs[0]
                # 这里不判断 ui-active，直接点击确保切换
                self.force_click(target_tab, f"切换模型->{target_model}")
                # 稍作等待，让 UI 响应切换
                time.sleep(1)
            else:
                self.log(f"⚠️ 未找到模型选项: {target_model}，保持默认", "orange")
        except Exception as e:
            self.log(f"⚠️ 切换模型失败: {e}", "orange")

    def check_infringement(self):
        """执行侵权检测 (含弹窗处理)"""
        self.log("🛡️ 执行侵权检测...", "blue")

        # 1. 点击检测
        btn = self.find("文案_侵权检测按钮")
        self.force_click(btn, "一键检测侵权词")

        # 2. 稍作等待，观察是否有弹窗
        # 侵权检测通常很快，给 2 秒让弹窗渲染
        time.sleep(2)

        # 3. 处理风险弹窗
        # 如果有侵权词，会弹出一个带“确定”的提示框
        # 我们尝试查找配置中的 "侵权确认_确定按钮"
        confirm_btn = self.find("侵权确认_确定按钮", optional=True, timeout=3)

        if confirm_btn and confirm_btn.is_displayed():
            self.log("   ⚠️ 检测到风险提示 (侵权/敏感词)，正在确认忽略...", "orange")
            self.force_click(confirm_btn, "确认忽略侵权")
            # 确认后可能还有 loading
            self.wait_loading_mask()
        else:
            self.log("   ✅ 无风险弹窗，检测通过", "green")

    def handle_images_placeholder(self):
        """
        图片处理占位函数
        TODO: 后续在此处实现 '点击选择图片 -> 勾选 -> 确认' 的逻辑
        """
        self.log("🖼️ [占位] 图片处理步骤 (暂跳过)", "gray")
        # 示例:
        # self.force_click(self.find("图片_选择按钮"), "选择图片")
        # ... 业务逻辑 ...
        pass