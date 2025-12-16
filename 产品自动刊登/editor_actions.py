import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from browser_utils import BrowserBase


class EditorManager(BrowserBase):
    def setup_listing_env(self, shop_name):
        """步骤3: 弹窗确认 -> 选店铺 -> 等待底部按钮加载"""
        self.log("--- 步骤3: 初始化刊登环境 ---", "blue")

        # 1. [修复] 稳健点击【下一步】弹窗
        # 因为点击"精细刊登"后弹窗有动画，所以循环检测几次
        has_clicked_next = False
        for _ in range(5):  # 尝试 5 次，每次间隔 0.5s
            next_btn = self.find('弹窗_下一步按钮', optional=True)
            if next_btn and next_btn.is_displayed():
                self.log("   🖱️ 点击 [下一步] 弹窗", "gray")
                self.safe_click(next_btn, "下一步")
                self.wait_loading_mask()
                time.sleep(1)  # 等待遮罩消失
                has_clicked_next = True
                break
            time.sleep(0.5)

        if not has_clicked_next:
            self.log("   ℹ️ 未检测到下一步弹窗 (可能是重试或无需弹窗)", "gray")

        # 2. [修复] 重新定位 Root 和 Body
        # 必须在点完弹窗后重新找，因为 DOM 可能变了
        self.root_element = self.find('容器_Root', optional=True)
        # 如果找不到 Root (页面结构简单时)，则全局找 Body
        self.body_element = self.find('容器_Body', root=self.root_element)

        if not self.body_element:
            # 如果此时连 Body 都找不到，说明页面彻底白屏或结构错误，直接抛出异常触发重试
            raise Exception("严重错误：无法定位页面主体 (容器_Body)")

        # 3. 选店铺
        shop_container = self.find('容器_店铺区域', root=self.body_element)
        if not shop_container:
            raise Exception("未找到店铺选择区域")

        shop_in = self.find('店铺_输入框', root=shop_container)

        self.log(f"⌨️ 输入店铺名: {shop_name}", "gray")
        shop_in.click()
        shop_in.clear()
        shop_in.send_keys(shop_name)
        time.sleep(1.5)

        # 点击下拉列表中的对应项
        try:
            xpath = f"//div[contains(@class,'ivu-select-dropdown')]//li[normalize-space(text())='{shop_name}']"
            target_item = self.driver.find_element(By.XPATH, xpath)
            self.driver.execute_script("arguments[0].click();", target_item)
            self.log(f"   🖱️ 选中列表项: [{shop_name}]", "green")
        except:
            self.log(f"❌ 列表点击失败，尝试回车: {shop_name}", "orange")
            shop_in.send_keys(Keys.ENTER)

        # 4. 强校验：等待底部按钮区域出现
        # 如果超时，抛出异常 -> main_worker 捕获 -> 刷新页面 -> 重试
        if not self._wait_for_buttons_loaded(timeout=20):
            raise Exception(f"店铺 [{shop_name}] 页面加载超时 (底部按钮未显示)")

    def _wait_for_buttons_loaded(self, timeout=20):
        self.log(f"⏳ 等待页面完全加载...", "gray")
        end_time = time.time() + timeout

        while time.time() < end_time:
            try:
                # 重新获取 Body
                body = self.find('容器_Body', root=self.root_element, optional=True)
                if not body:
                    time.sleep(1);
                    continue

                # 查找底部按钮容器
                btn_module = self.find('容器_按钮模块', root=body, optional=True)

                if btn_module and btn_module.is_displayed():
                    # 检查是否有按钮
                    btns = btn_module.find_elements(By.XPATH, ".//*[self::button or contains(@class, 'f-btn')]")
                    visible_btns = [b for b in btns if b.is_displayed()]
                    if len(visible_btns) > 0:
                        self.log(f"✅ 页面加载完毕 (功能按钮就绪)", "green")
                        return True
            except:
                pass
            time.sleep(1)

        self.log("❌ 页面加载超时：底部按钮一直未出现", "red")
        return False

    def process_all_sites(self):
        """步骤4: 遍历站点 Tabs 并执行操作"""
        # 再次确保环境是最新的
        self.body_element = self.find('容器_Body', root=self.root_element)
        tabs_container = self.find('容器_Tabs区域', root=self.body_element)

        if not tabs_container:
            # 理论上上面已经校验过按钮了，这里如果还找不到，说明结构极其异常
            raise Exception("严重错误：按钮已加载但找不到 Tabs 区域")

        items = tabs_container.find_elements(By.CSS_SELECTOR, "span.item")
        total_sites = len(items)

        for i in range(total_sites):
            # 🔄 每次循环重新获取元素，防止 StaleElementReferenceException
            self.body_element = self.find('容器_Body', root=self.root_element)
            tabs_container = self.find('容器_Tabs区域', root=self.body_element)
            items = tabs_container.find_elements(By.CSS_SELECTOR, "span.item")

            if i >= len(items): break
            current_tab = items[i]
            site_name = current_tab.get_attribute("textContent").strip()

            if "已推送" in site_name:
                self.log(f"⏩ 站点 {i + 1}/{total_sites} ({site_name}) 已推送，跳过", "gray")
                continue

            self.log(f"👉 切换站点 {i + 1}/{total_sites}: {site_name}", "blue")

            # 点击切换 (使用 JS 点击更稳定)
            self.driver.execute_script("arguments[0].click();", current_tab)
            self.wait_loading_mask()
            time.sleep(2)  # 等待 Tab 内容渲染

            # 执行单站流程
            self.execute_single_site_workflow(is_first_site=(i == 0))

    def execute_single_site_workflow(self, is_first_site):
        """单站点核心流程"""
        # 1. AI 文案 (仅首站)
        if is_first_site and self.config_data.get('TEXT_SOURCE') != '跳过文案':
            self.run_ai_optimization()

        # 2. 侵权检测
        self.check_infringement()

        # 3. 保存并提交 (含错误处理)
        self.perform_save_and_submit()

    # ================= 业务功能模块 =================

    def run_ai_optimization(self):
        self.log("🤖 执行 AI 文案优化...", "black")
        copy_mod = self._get_copy_module()
        if not copy_mod: return

        ai_btn = self.find("文案_AI按钮", root=copy_mod, optional=True)
        if not self.safe_click(ai_btn, "AI按钮"): return

        # 等待 AI 弹窗
        ai_root = self._get_active_ai_root(timeout=8)
        if not ai_root:
            self.log("❌ AI 弹窗未弹出", "red")
            return

        # 尝试点击生成 (最多试3次)
        for _ in range(3):
            gen_btn = self.find("AI弹窗_生成按钮", root=ai_root, optional=True)
            if gen_btn and gen_btn.is_displayed():
                self.driver.execute_script("arguments[0].click();", gen_btn)
                time.sleep(5)  # 等待生成

            # 检查标题长度是否有变化
            title_len = self._check_ai_title_len(ai_root)
            if title_len > 10:
                self.log(f"   ✨ 文案生成成功 (标题长度: {title_len})", "green")
                break
            time.sleep(2)

        # 应用
        apply_btn = self.find("AI弹窗_应用按钮", root=ai_root, optional=True)
        if apply_btn:
            self.driver.execute_script("arguments[0].click();", apply_btn)
            time.sleep(1)

        self._force_close_popups()  # 清理现场

    def check_infringement(self):
        self.log("🛡️ 侵权检测...", "black")
        copy_mod = self._get_copy_module()
        if not copy_mod: return

        chk_btn = self.find("文案_侵权检测按钮", root=copy_mod, optional=True)
        if not self.safe_click(chk_btn, "侵权检测"): return

        time.sleep(2)  # 等待检测结果

        # 检测是否有侵权弹窗
        inf_root = self._get_active_infringement_root(timeout=3)
        if inf_root:
            self.log("   🚨 发现侵权词，尝试确认...", "orange")
            try:
                confirm = inf_root.find_element(By.XPATH, ".//button[contains(., '确定')]")
                self.driver.execute_script("arguments[0].click();", confirm)
                time.sleep(1)
            except:
                pass
        else:
            self.log("   ✅ 无侵权报警", "green")

    def perform_save_and_submit(self):
        """保存并提交 (含必填项修复重试)"""
        # 获取当前 Tab 的按钮容器
        btn_container = self._get_active_site_btn_container()
        if not btn_container:
            self.log("❌ 未找到底部按钮区域", "red")
            return

        # 1. 先点保存当前页 (稳妥起见)
        save_btn = self.find("按钮_保存当前", root=btn_container, optional=True)
        self.safe_click(save_btn, "保存当前")
        self.wait_loading_mask()
        time.sleep(1)

        # 2. 点提交并处理报错 (重试循环)
        submit_btn = self.find("按钮_提交当前", root=btn_container, optional=True)
        if not submit_btn: return

        for attempt in range(2):  # 最多重试2次
            self.log(f"🚀 提交当前站点 (第{attempt + 1}次)...", "blue")
            self.safe_click(submit_btn, "提交")
            self.wait_loading_mask()
            time.sleep(2)

            # 检查是否有错误提示 (页面红字 or 弹窗)
            has_error = False

            # A. 检查页面必填项红字
            if self._check_and_fill_mandatory():
                has_error = True

            # B. 检查侵权弹窗 (有时提交时才弹)
            inf_root = self._get_active_infringement_root(timeout=1)
            if inf_root:
                self.log("   ⚠️ 提交触发侵权确认", "orange")
                try:
                    confirm = inf_root.find_element(By.XPATH, ".//button[contains(., '确定')]")
                    self.driver.execute_script("arguments[0].click();", confirm)
                    has_error = True
                except:
                    pass

            if not has_error:
                self.log("   ✅ 提交动作完成", "green")
                break  # 成功，跳出重试
            else:
                self.log("   🔄 错误已自动处理，准备重试...", "blue")
                # 重新获取按钮防止 Stale
                btn_container = self._get_active_site_btn_container()
                submit_btn = self.find("按钮_提交当前", root=btn_container)

    # ================= 辅助工具方法 =================

    def _get_copy_module(self):
        """获取文案模块 (AI/侵权按钮在这里)"""
        try:
            main = self.find('容器_Main', root=self.body_element)
            layout = self.find('容器_布局Wrapper', root=main)
            # 找到可见的那个 site div
            site_divs = layout.find_elements(By.XPATH, "./div")
            active_div = next((s for s in site_divs if s.is_displayed()), None)
            if active_div:
                wrapper = self.find('容器_站点模块Wrapper', root=active_div)
                return self.find('容器_文案模块', root=wrapper)
        except:
            pass
        return None

    def _get_active_site_btn_container(self):
        """获取底部按钮区当前可见的 span"""
        try:
            main = self.find('容器_Main', root=self.body_element)
            btn_mod = self.find('容器_按钮模块', root=main)
            spans = btn_mod.find_elements(By.XPATH, "./span[contains(@class, 'f-btn')]")
            return next((s for s in spans if s.is_displayed()), None)
        except:
            return None

    def _get_active_ai_root(self, timeout=2):
        """获取可见的AI弹窗"""
        end = time.time() + timeout
        while time.time() < end:
            try:
                # 假设 config 里有 'AI弹窗_Root'
                popups = self.driver.find_elements(*self._parse_config()['AI弹窗_Root']['locator'])
                for p in popups:
                    # 检查里面是否有内容且可见
                    if p.is_displayed(): return p
            except:
                pass
            time.sleep(0.5)
        return None

    def _check_ai_title_len(self, root):
        try:
            inp = self.find("AI弹窗_标题输入框", root=root, optional=True)
            if inp: return len(inp.get_attribute("value"))
        except:
            pass
        return 0

    def _get_active_infringement_root(self, timeout=1):
        """检查侵权/敏感词弹窗"""
        end = time.time() + timeout
        while time.time() < end:
            try:
                wrappers = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'ivu-modal-wrap')]")
                for w in wrappers:
                    if w.is_displayed() and "侵权" in w.get_attribute("innerText"):
                        return w.find_element(By.XPATH, ".//div[contains(@class, 'ivu-modal-content')]")
            except:
                pass
            time.sleep(0.5)
        return None

    def _check_and_fill_mandatory(self):
        """检查页面必填报错并填充"""
        filled = False
        try:
            # 查找所有可见的 "带*号为必填项" 提示
            errs = self.driver.find_elements(By.XPATH, "//div[contains(text(), '必填项')]")
            visible_errs = [e for e in errs if e.is_displayed()]

            if visible_errs:
                self.log(f"   🔧 发现 {len(visible_errs)} 个必填项缺失，尝试填充...", "orange")
                # 简单填充逻辑：找到附近的 input 填 1
                for err in visible_errs:
                    try:
                        parent = err.find_element(By.XPATH, "./..")  # 回到 form-item
                        inputs = parent.find_elements(By.TAG_NAME, "input")
                        for inp in inputs:
                            if inp.is_displayed():
                                inp.clear()
                                inp.send_keys("1")
                                inp.send_keys(Keys.TAB)  # 触发验证
                                filled = True
                    except:
                        pass
        except:
            pass
        return filled

    def _force_close_popups(self):
        # 简单尝试关闭残留的 AI 弹窗
        try:
            ai = self._get_active_ai_root(timeout=0.5)
            if ai:
                cancel = self.find("AI弹窗_取消按钮", root=ai, optional=True)
                if cancel: self.driver.execute_script("arguments[0].click();", cancel)
        except:
            pass