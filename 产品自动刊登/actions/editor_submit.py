import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from 产品自动刊登.actions.editor_features import EditorFeatures


class EditorSubmit(EditorFeatures):
    """
    编辑器提交模块 (B3)
    职责：流水线提交、成功状态强校验、失败站点循环修复
    """

    def process_submission_flow(self):
        """执行完整的提交与修复流程"""
        self.log("🚀 进入提交流水线...", "blue")

        # 1. 保存当前页 (基础数据)
        self._execute_strict_step("按钮_保存当前", "提示_通用成功", "保存当前页")

        # 2. 同步至未推送站点
        self._execute_strict_step("按钮_同步", "提示_同步成功", "同步站点")

        # 3. 翻译 (耗时较长，超时设为 90秒)
        self._execute_strict_step("按钮_翻译", "提示_翻译成功", "全站翻译", timeout=90)

        # 4. 提交所有站点
        self.log("🚀 执行：保存并提交所有站点...", "blue")
        submit_all_btn = self.find("按钮_提交所有")
        self.force_click(submit_all_btn, "提交所有")

        # 提交后会出现遮罩，等待消失
        self.wait_loading_mask()

        # 5. 提交后清理 (可能有大量系统弹窗)
        self.force_close_all_popups()

        # 6. 汇报提交后状态
        self.log_all_site_status("提交后初次状态")

        # 7. 进入循环修复流程 (处理失败的站点)
        self._loop_fix_failed_tabs()

        # 8. 最终汇报
        self.log_all_site_status("修复后最终状态")

    def _execute_strict_step(self, btn_key, msg_key, desc, timeout=15):
        """执行动作并严格等待配置中的成功提示"""
        self.log(f"   👉 动作: {desc}", "black")

        # 查找并点击按钮
        btn = self.find(btn_key)
        self.force_click(btn, desc)

        # 等待成功提示
        try:
            msg_locator = self._parse_config().get(msg_key)['locator']
            # 使用 presence_of_element_located 捕捉瞬时提示
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, msg_locator))
            )
            self.log(f"   ✅ {desc} 成功 (捕获到系统提示)", "green")
            # 稍作等待，让提示框消失，避免遮挡后续点击
            time.sleep(1.5)
        except Exception as e:
            self.log(f"   ⚠️ {desc} 未检测到明确成功提示 (或超时)，尝试继续...", "orange")

    def _loop_fix_failed_tabs(self):
        """遍历所有 Tab，对非成功状态的站点进行单站修复"""
        self.log("🔧 开始检查并修复失败站点...", "blue")

        try:
            # 1. 获取 Tab 容器
            container = self.find("状态_容器", optional=True)
            if not container:
                self.log("   ⚠️ 无法找到站点 Tab 栏，跳过修复", "orange")
                return

            # 获取当前站点总数
            items = container.find_elements(By.XPATH, ".//span[contains(@class, 'item')]")
            count = len(items)

            # 按索引遍历，因为点击切换后 DOM 可能会刷新
            for i in range(count):
                # 重新获取当前 item (防止 StaleElementReferenceException)
                container = self.find("状态_容器")
                current_item = container.find_elements(By.XPATH, ".//span[contains(@class, 'item')]")[i]

                # 解析状态
                try:
                    name_el = current_item.find_element(By.XPATH, "./button/span/span[1]")
                    site_name = name_el.text.strip()

                    status_el = current_item.find_element(By.XPATH, "./button/span/span[2]")
                    raw_status = status_el.get_attribute("textContent").strip()  # "[]" 或 "[已推送]"
                except:
                    continue

                # 成功状态跳过
                if "[已推送]" in raw_status:
                    continue

                # 开始修复
                self.log(f"   🛠️ 正在修复站点: {site_name} (状态: {raw_status})", "blue")

                # 切换 Tab
                btn = current_item.find_element(By.TAG_NAME, "button")
                self.force_click(btn, f"切换站点-{site_name}")
                time.sleep(1)  # 等待 Tab 内容渲染

                # 执行单站修复
                self._fix_single_site_page()

        except Exception as e:
            self.log(f"❌ 循环修复流程异常: {e}", "red")

    def _fix_single_site_page(self):
        """单页面修复逻辑：侵权复检 -> 尝试提交 -> 补填必填项 -> 重试"""
        try:
            # A. 再次侵权检测 (防止因侵权词拦截提交)
            self.check_infringement()

            # B. 尝试提交 (保存当前页触发校验)
            save_btn = self.find("按钮_保存当前")
            self.force_click(save_btn, "尝试提交当前页")
            time.sleep(1.5)  # 等待校验结果出现

            # C. 检测必填项错误 (红色框)
            errors = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'ivu-form-item-error')]")

            if errors:
                self.log(f"      ⚠️ 检测到 {len(errors)} 个必填项错误，尝试自动填充...", "orange")

                # 执行填充
                self._fill_mandatory_fields(errors)

                # 填充后再次提交
                self.force_click(save_btn, "重试提交当前页")
                self.wait_loading_mask()

                # 关闭可能的报错弹窗 (如 "操作失败" 或 "服务器繁忙")
                self.force_close_all_popups()
            else:
                self.log("      ✅ 无明显的必填项错误提示", "gray")

        except Exception as e:
            self.log(f"      ❌ 单站修复失败: {e}", "gray")

    def _fill_mandatory_fields(self, error_elements):
        """遍历错误容器，智能填充 input 或 select"""
        for index, err_div in enumerate(error_elements):
            try:
                # 尝试找到内部的 input
                inputs = err_div.find_elements(By.TAG_NAME, "input")
                if not inputs:
                    continue

                target = inputs[0]
                if not (target.is_displayed() and target.is_enabled()):
                    continue

                # 判断类型
                if target.get_attribute("readonly"):
                    # --- 下拉框处理 ---
                    # iView 的下拉框通常是 readonly input，点击后在 body 生成 dropdown
                    self.log(f"         🔻 修复第 {index + 1} 项: 选择下拉框第一个选项", "gray")
                    self.force_click(target, "点击下拉框")
                    time.sleep(0.5)

                    # 查找所有可见的下拉选项 (必须是可见的，排除其他未打开的)
                    # ivu-select-dropdown 是全局的，用 style!=none 过滤
                    options = self.driver.find_elements(By.XPATH,
                                                        "//div[contains(@class,'ivu-select-dropdown') and not(contains(@style,'display: none'))]//li")

                    if options:
                        self.force_click(options[0], "选中第一项")
                    else:
                        # 兜底：如果找不到选项，尝试按回车
                        target.send_keys("\n")
                else:
                    # --- 文本框处理 ---
                    self.log(f"         ✍️ 修复第 {index + 1} 项: 填充文本 '1'", "gray")
                    target.clear()
                    target.send_keys("1")

            except Exception as e:
                pass