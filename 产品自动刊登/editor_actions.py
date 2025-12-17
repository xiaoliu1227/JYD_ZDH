import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from browser_utils import BrowserBase


class EditorManager(BrowserBase):

    # =======================================================
    # [兼容接口] 适配 main_worker.py 的旧调用
    # =======================================================
    def process_all_sites(self):
        self.log("⚠️ 检测到旧接口调用，已重定向至标准流程...", "gray")
        return self.process_listing_workflow()

    # =======================================================
    # 1. 初始化与环境准备
    # =======================================================
    def setup_listing_env(self, shop_name):
        self.log("--- 步骤3: 初始化刊登环境 ---", "blue")

        # 引入重试机制，防止网络波动导致加载失败
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self._enter_shop_context(shop_name)
                return  # 成功则退出
            except Exception as e:
                self.log(f"⚠️ 初始化失败 (第 {attempt + 1} 次): {e}", "orange")
                if attempt < max_retries - 1:
                    self.log("🔄 刷新页面重试...", "blue")
                    self.driver.refresh()
                    self.wait_loading_mask(timeout=20)
                else:
                    raise Exception("多次刷新仍无法加载店铺界面，流程终止")

    def _enter_shop_context(self, shop_name):
        """选择店铺并等待页面完全就绪"""
        # 1. 处理初始弹窗 (含 Amazon 隐式加载检测)
        self._handle_initial_popups()

        # 2. 强制等待遮罩消失 (核心修复：防止点击店铺时被遮挡)
        try:
            WebDriverWait(self.driver, 10).until(
                EC.invisibility_of_element_located((By.CLASS_NAME, "el-loading-mask"))
            )
        except:
            pass

        self._refresh_root()

        # 3. 选店铺
        self.log(f"🏪 选择店铺: {shop_name}", "black")
        shop_container = self.find('容器_店铺区域', root=self.body_element)

        if shop_container:
            shop_in = self.find('店铺_输入框', root=shop_container)

            # [修复] 使用 safe_click 穿透潜在的透明遮罩
            if not self.safe_click(shop_in, "店铺输入框"):
                self.log("   ⚠️ 点击被拦截，尝试 JS 强制聚焦", "orange")
                self.driver.execute_script("arguments[0].focus();", shop_in)

            time.sleep(0.5)
            shop_in.clear()
            shop_in.send_keys(shop_name)

            time.sleep(1.5)  # 等待下拉菜单渲染

            # 尝试点击下拉项
            target_item = self.find("店铺_下拉选项", optional=True)
            if target_item:
                self.safe_click(target_item, "店铺下拉项")
            else:
                self.log("   ⚠️ 未找到配置的下拉项，尝试文字匹配...", "orange")
                try:
                    # 兜底策略：直接找包含店铺名的 li 元素
                    xpath = f"//div[contains(@class,'ivu-select-dropdown') and not(contains(@style,'display: none'))]//li[contains(text(),'{shop_name}')]"
                    real_item = self.driver.find_element(By.XPATH, xpath)
                    self.safe_click(real_item, "文字匹配项")
                except:
                    shop_in.send_keys(Keys.ENTER)

        # 4. 死等核心功能加载 (最长60秒)
        self.log("   ⏳ 等待编辑器核心加载...", "blue")
        trans_cfg = self._parse_config().get("按钮_翻译")

        try:
            # 必须等待按钮变成“可点击”状态，才算加载完成
            WebDriverWait(self.driver, 60).until(
                EC.element_to_be_clickable(trans_cfg['locator'])
            )
            # 再缓冲1秒确保JS绑定
            time.sleep(1)
            self.log("   ✅ 编辑器加载完毕", "green")
        except Exception:
            raise Exception("超过60秒页面未就绪(按钮不可点)，判定为卡死")

    # =======================================================
    # [核心工具] 智能按钮查找器
    # =======================================================
    def _click_visible_button(self, btn_config_name):
        """
        全自动查找并点击可见按钮。
        解决了 "多Tab页面有多个同名隐藏按钮" 导致的定位失败问题。
        """
        try:
            # 1. 文本映射表 (防止配置文件没更新)
            text_map = {
                "按钮_保存当前": "保存当前页",
                "按钮_同步": "同步至未推送站点",
                "按钮_翻译": "翻译",
                "按钮_提交当前": "保存并提交当前页",
                "按钮_提交所有": "保存并提交所有站点",
                "按钮_取消": "取消"
            }

            target_text = text_map.get(btn_config_name, "")

            # 2. 优先通过文本全局查找 (最稳健)
            if target_text:
                xpath = f"//button[contains(., '{target_text}')]"
                btns = self.driver.find_elements(By.XPATH, xpath)
            else:
                # 降级：使用配置文件的 locator
                cfg = self._parse_config().get(btn_config_name)
                if not cfg: return False
                btns = self.driver.find_elements(*cfg['locator'])

            # 3. 遍历找到唯一可见的那个并点击
            for btn in btns:
                if btn.is_displayed():
                    return self.safe_click(btn, btn_config_name)

            self.log(f"   ❌ 未找到可见按钮: {btn_config_name}", "red")
            return False

        except Exception as e:
            self.log(f"   ⚠️ 点击异常 {btn_config_name}: {e}", "red")
            return False

    # =======================================================
    # 2. 核心业务主流程
    # =======================================================
    def process_listing_workflow(self):
        self._refresh_root()

        # --- A. AI 智能优化 ---
        if self.config_data.get('TEXT_SOURCE') != '跳过文案':
            self.run_ai_optimization_flow()

        # --- B. 侵权检测 ---
        self.check_infringement_and_confirm()

        # --- C. 图片操作 (可选，需要时取消注释) ---
        # self._handle_images_placeholder()

        # --- D. 预提交动作 ---
        self.log("💾 1. 保存当前...", "black")
        if self._click_visible_button("按钮_保存当前"):
            self.wait_success_msg()

        self.log("🔄 2. 同步站点...", "black")
        if self._click_visible_button("按钮_同步"):
            self.wait_success_msg(timeout=30)

        self.log("🌐 3. 执行翻译...", "black")
        if self._click_visible_button("按钮_翻译"):
            self._wait_for_translation_completion()

        # --- E. 提交所有 ---
        self.log("🚀 4. 提交所有站点...", "blue")
        self._click_visible_button("按钮_提交所有")

        # 检测结果
        submit_result = self._check_submit_result()

        if submit_result == "success":
            self.log("✅ 提交所有显示成功", "green")
        else:
            self.log(f"⚠️ 提交遇到阻碍: {submit_result}，进入单站修复", "orange")
            self._close_error_modal()
            # --- F. 失败站点扫尾 ---
            self._loop_fix_failed_tabs()

    # =======================================================
    # 3. 细分功能模块
    # =======================================================

    def run_ai_optimization_flow(self):
        self.log("🤖 执行AI优化...", "blue")
        ai_btn = self.find("文案_AI按钮")
        if not self.safe_click(ai_btn):
            self.log("   ❌ AI按钮未找到，跳过", "red")
            return

        time.sleep(2)

        # 尝试生成逻辑 (失败才重试)
        max_retries = 2
        for attempt in range(max_retries):
            self.log(f"   ⚡ 点击生成文案 (第 {attempt + 1} 次)...", "black")
            gen_btn = self.find("AI弹窗_生成按钮")
            self.safe_click(gen_btn)

            try:
                # 如果30秒内加载完，说明成功，直接跳出循环
                self.wait_loading_mask(timeout=30)
                self.log("   ✅ AI生成完成", "green")
                break
            except Exception:
                self.log(f"   ⚠️ 第 {attempt + 1} 次生成等待超时，准备重试...", "orange")

        time.sleep(1)
        self.log("   📝 应用所有文案", "gray")
        apply_btn = self.find("AI弹窗_应用按钮")
        self.safe_click(apply_btn)
        self.wait_loading_mask()
        self._force_close_popups()

    def check_infringement_and_confirm(self):
        """检测侵权并死等结果（弹窗确认或无风险提示）"""
        self.log("🛡️ 执行预检：侵权检测...", "black")
        detect_btn = self.find("文案_侵权检测按钮")
        if not self.safe_click(detect_btn): return

        self.wait_loading_mask(timeout=5)

        # 循环监测结果 (最长10秒)
        check_timeout = 10
        start_time = time.time()

        while time.time() - start_time < check_timeout:
            # 分支A: 有弹窗 -> 点确定
            confirm_btn = self.find("侵权确认_确定按钮", optional=True, timeout=0.1)
            if confirm_btn and confirm_btn.is_displayed():
                self.log("   ⚠️ 发现侵权弹窗，点击确定...", "orange")
                self.safe_click(confirm_btn)
                time.sleep(0.5)
                self.wait_loading_mask()
                # 强制等待弹窗完全消失
                try:
                    WebDriverWait(self.driver, 3).until_not(
                        EC.visibility_of_element_located(
                            (By.XPATH, "//div[contains(@class,'ivu-modal-confirm-footer')]"))
                    )
                except:
                    pass
                self.log("   ✅ 侵权词已清理", "green")
                return

            # 分支B: 无弹窗 -> 检查提示语
            page_src = self.driver.page_source
            if "无高风险" in page_src or "无侵权" in page_src or "敏感词!" in page_src:
                self.log("   ✅ 检测结果：无高风险侵权词", "green")
                return

            time.sleep(0.5)

        self.log("   ℹ️ 等待检测结果超时，尝试强制继续...", "gray")

    def _handle_images_placeholder(self):
        self.log("🖼️ [占位] 执行图片选择...", "gray")
        if self.safe_click(self.find("按钮_选择图片", timeout=3)):
            time.sleep(1)
            self._close_error_modal()

    def _wait_for_translation_completion(self):
        self.log("   ⏳ 等待翻译...", "gray")
        time.sleep(2)
        # 翻译时间较长，给90秒
        self.wait_loading_mask(timeout=90)
        try:
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(text(), '翻译成功')]"))
            )
            self.log("   ✅ 翻译完成", "green")
        except:
            pass

    def _check_submit_result(self):
        self.wait_loading_mask(timeout=45)
        time.sleep(0.5)
        src = self.driver.page_source
        if "推送失败" in src or "刊登失败" in src: return "error_modal"
        if "必填项" in src: return "mandatory_error"
        return "success"

    def _loop_fix_failed_tabs(self):
        self.log("=== 🧹 开始修复失败站点 ===", "blue")
        tabs_container = self.find("容器_Tabs区域")
        if not tabs_container: return

        # 遍历 Tab 尝试修复
        max_tabs = 20
        for i in range(max_tabs):
            # 每次循环重新获取 Tab 列表，防止 stale element
            tabs = self.driver.find_elements(By.XPATH,
                                             "//div[contains(@class, 'ivu-tabs-nav-scroll')]//div[contains(@class, 'ivu-tabs-tab')]")
            if i >= len(tabs): break

            current_tab = tabs[i]
            tab_name = current_tab.text.strip()

            self.log(f"👉 检查站点: {tab_name}", "black")
            try:
                current_tab.click()
            except:
                self.driver.execute_script("arguments[0].click();", current_tab)
            time.sleep(1)

            # 单站修复流程
            self.check_infringement_and_confirm()

            self.log(f"   🚀 提交: {tab_name}", "blue")
            self._click_visible_button("按钮_提交当前")

            res = self._check_submit_result()
            if res == "mandatory_error":
                self.log("   ❌ 必填项缺失，自动填充...", "orange")
                self._close_error_modal()
                if self._fill_mandatory_fields():
                    self.log("   🔧 填充完成，重试...", "blue")
                    self._click_visible_button("按钮_提交当前")
                    self.wait_loading_mask()
                else:
                    self.log("   ⚠️ 无法填充，跳过", "red")
            elif res == "error_modal":
                self.log("   ❌ 提交仍报错", "red")
                self._close_error_modal()
            else:
                self.log("   ✅ 似乎成功", "green")
            time.sleep(1)

    def _fill_mandatory_fields(self):
        """自动查找红色必填项并填充"""
        found = False
        try:
            error_boxes = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'ivu-form-item-error')]")
            for box in error_boxes:
                if not box.is_displayed(): continue

                # 填充输入框
                inputs = box.find_elements(By.TAG_NAME, "input")
                for inp in inputs:
                    if inp.is_displayed():
                        inp.clear()
                        inp.send_keys("1")
                        found = True

                # 处理下拉框 (如果没找到输入框)
                if not found:
                    selects = box.find_elements(By.CSS_SELECTOR, ".ivu-select-selection")
                    for sel in selects:
                        sel.click()
                        time.sleep(0.5)
                        # 选第一个选项
                        opts = self.driver.find_elements(By.CSS_SELECTOR, ".ivu-select-dropdown li")
                        vis = [o for o in opts if o.is_displayed()]
                        if vis:
                            vis[0].click()
                            found = True
                        # 收起下拉
                        self.driver.find_element(By.TAG_NAME, "body").click()
        except:
            pass
        return found

    def exit_editor(self):
        self.log("🚪 退出编辑器...", "black")
        self._click_visible_button("按钮_取消")
        time.sleep(1)
        confirm = self.find("退出确认_确定关闭", optional=True)
        if confirm: confirm.click()
        self.wait_loading_mask()

    # --- 辅助方法 ---
    def _close_error_modal(self):
        try:
            btn = self.driver.find_element(By.CSS_SELECTOR, "a.ivu-modal-close")
            if btn.is_displayed(): btn.click()
        except:
            pass

    def _handle_initial_popups(self):
        """处理初始弹窗，等待平台信息(Hidden Input)加载"""
        next_btn = self.find('弹窗_下一步按钮', optional=True, timeout=3)
        if next_btn and next_btn.is_displayed():
            self.log("   👀 检测到初始弹窗，等待平台信息...", "blue")
            try:
                # 核心修复：检测隐藏的 value="AMAZON" 输入框
                WebDriverWait(self.driver, 5).until(lambda d: self._is_platform_loaded())
                self.log("   ✅ 平台填充完毕", "green")
            except:
                self.log("   ⚠️ 等待平台填充超时", "orange")

            time.sleep(0.5)
            self.safe_click(next_btn, "下一步")
            self.wait_loading_mask()

    def _is_platform_loaded(self):
        try:
            # 策略1: 找 value="AMAZON" 的 input
            target = self.driver.find_elements(By.XPATH,
                                               "//div[contains(@class,'ivu-modal-body')]//input[@value='AMAZON']")
            if target: return True

            # 策略2: 遍历查找包含 AMAZON 的 input
            inputs = self.driver.find_elements(By.CSS_SELECTOR, ".ivu-modal-body input")
            for inp in inputs:
                val = inp.get_attribute("value")
                if val and "AMAZON" in val.upper(): return True
            return False
        except:
            return False

    def _force_close_popups(self):
        pass

    def _refresh_root(self):
        self.root_element = self.find('容器_Root', optional=True)
        self.body_element = self.find('容器_Body', root=self.root_element)

    def wait_success_msg(self, timeout=10):
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(text(), '成功')]"))
            )
        except:
            pass
        self.wait_loading_mask()