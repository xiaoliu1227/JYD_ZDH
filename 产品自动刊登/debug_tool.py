import time
import re
import traceback
import datetime
from PyQt5.QtCore import QThread, pyqtSignal
from selenium import webdriver
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException


class LocatorParser:
    @staticmethod
    def parse(locator_str: str) -> tuple:
        locator_str = locator_str.strip()
        if not locator_str: return None, None

        # 1. 优先识别 ./ 开头的相对路径
        if locator_str.startswith('./'):
            return (By.XPATH, locator_str)

        # 2. 常规 XPath
        if locator_str.startswith('//') or locator_str.startswith('(') or locator_str.startswith('.//'):
            return (By.XPATH, locator_str)

        # 3. CSS
        if locator_str.startswith('#') or locator_str.startswith('.'):
            return (By.CSS_SELECTOR, locator_str)

        # 4. 属性
        attr_match = re.match(r'^([\w-]+)=\"(.*?)\"$', locator_str) or re.match(r"^([\w-]+)='(.*?)'$", locator_str)
        if attr_match:
            return (By.CSS_SELECTOR, f"[{attr_match.group(1)}='{attr_match.group(2)}']")

        # 5. Span 文本 [关键修正：使用 normalize-space 忽略 HTML 中的空格]
        if locator_str.startswith("<span>"):
            text = locator_str.replace("<span>", "").strip()
            return (By.XPATH, f".//span[normalize-space(text())='{text}']")

        # 6. 默认文本 [关键修正：使用 normalize-space]
        return (By.XPATH, f".//*[normalize-space(text())='{locator_str}']")


class RestartSkuException(Exception):
    pass


class ListingWorker(QThread):
    log_signal = pyqtSignal(str, str)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)
    pause_required_signal = pyqtSignal(str)

    def __init__(self, config_data, is_headless, sku_list=None):
        super().__init__()
        self.config_data = config_data
        self.is_headless = is_headless
        self.sku_list = sku_list or []
        self.is_running = True
        self.is_paused = False
        self.driver = None

        self.shop_name = config_data.get('ACCOUNT_NAME', '')
        self.current_site_index = 0
        self.need_restart_current_sku = False

    def stop(self):
        """安全停止线程"""
        self.is_running = False
        self.is_paused = False  # 强制解除暂停，防止死锁
        self.requestInterruption()

    def _log(self, msg, color="black"):
        self.log_signal.emit(msg, color)
        try:
            date_str = datetime.datetime.now().strftime("%Y-%m-%d")
            with open(f"log_{date_str}.txt", "a", encoding="utf-8") as f:
                f.write(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        except:
            pass

    def _init_driver(self):
        options = EdgeOptions()
        if self.is_headless:
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
        else:
            options.add_argument("--start-maximized")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--log-level=3")
        return webdriver.Edge(options=options)

    def _parse_config(self):
        parsed = {}
        for mod in self.config_data.get('ELEMENT_CONFIG', []):
            for ele in mod['elements']:
                by, val = LocatorParser.parse(ele['locator'])
                if by:
                    parsed[ele['name']] = {
                        'locator': (by, val),
                        'timeout': ele.get('timeout', 10),
                        'rest': ele.get('rest', 2)
                    }
        return parsed

    def request_manual_pause(self):
        self.is_paused = True
        self._log("⏸️ 用户请求暂停...", "orange")

    def resume_work(self, new_config_data=None):
        if new_config_data:
            self.config_data = new_config_data
            self._log("🔄 配置已更新", "green")
        self.is_paused = False
        self.need_restart_current_sku = True
        self._log("▶️ 准备重试当前SKU流程...", "green")

    def _check_pause(self):
        if not self.is_running: return  # 如果停止了，直接返回

        if self.is_paused:
            self.pause_required_signal.emit("流程受阻或手动暂停")
            while self.is_paused and self.is_running:
                time.sleep(1)
            if self.need_restart_current_sku:
                self.need_restart_current_sku = False
                raise RestartSkuException("User resumed from pause")

    def _wait_visible_then_rest(self, driver, name, timeout=None, rest=None, root=None, optional=False):
        self._check_pause()
        ctx = root if root else driver

        cfg = self._parse_config().get(name)
        if not cfg:
            msg = f"❌ 配置缺失: {name}"
            if optional: return None
            self._log(msg, "red")
            self.is_paused = True
            self._check_pause()
            return None

        use_timeout = cfg['timeout'] if timeout is None else timeout
        use_rest = cfg['rest'] if rest is None else rest

        self._log(f"🔎 正在定位: [{name}]...", "gray")

        try:
            el = WebDriverWait(ctx, use_timeout).until(
                EC.visibility_of_element_located(cfg['locator'])
            )
            self._highlight(driver, el, "green")
            log_color = "gray" if optional else "green"
            self._log(f"   ✅ 成功锁定: [{name}]", log_color)
            if use_rest > 0: time.sleep(use_rest)
            return el
        except TimeoutException:
            if optional:
                # self._log(f"   ℹ️ 可选元素 [{name}] 未出现", "gray")
                return None
            self._log(f"❌ 超时失败: [{name}] 未在 {use_timeout}s 内可见", "red")
            self.is_paused = True
            self._check_pause()
        except RestartSkuException:
            raise
        except Exception as e:
            if optional: return None
            self._log(f"❌ 异常 [{name}]: {e}", "red")
            self.is_paused = True
            self._check_pause()
        return None

    def _find(self, driver, name, root=None, optional=False):
        return self._wait_visible_then_rest(driver, name, root=root, optional=optional)

    def _find_in_root(self, root, name, optional=False):
        return self._wait_visible_then_rest(self.driver, name, root=root, optional=optional)

    def _highlight(self, driver, element, color="red"):
        try:
            driver.execute_script(f"arguments[0].style.border='2px solid {color}'", element)
        except:
            pass

    def _safe_click(self, driver, element, name=""):
        if not element: return False
        action_name = name if name else "元素"
        self._log(f"   🖱️ 点击: {action_name}", "black")
        try:
            element.click()
            return True
        except:
            try:
                driver.execute_script("arguments[0].click();", element)
                return True
            except Exception as e:
                self._log(f"❌ 点击失败 [{action_name}]: {e}", "red")
                return False

    def _wait_loading_mask(self, driver, timeout=15):
        try:
            WebDriverWait(driver, timeout).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, ".el-loading-mask")))
        except:
            pass

    # --- 弹窗逻辑 ---
    def _get_active_ai_root(self, driver, timeout=0):
        self._check_pause()
        cfg = self._parse_config().get("AI弹窗_Root")
        if not cfg: return None
        end = time.time() + timeout
        while True:
            if not self.is_running: return None
            try:
                all_popups = driver.find_elements(*cfg['locator'])
                if self.current_site_index < len(all_popups):
                    target = all_popups[self.current_site_index]
                    child = target.find_element(By.XPATH, "./div[1]")
                    if "display: none" not in (child.get_attribute("style") or ""):
                        self._highlight(driver, target, "blue")
                        return target
            except:
                pass
            if timeout == 0: break
            if time.time() >= end: break
            time.sleep(0.5)
        return None

    def _get_active_infringement_root(self, driver, timeout=0):
        """
        [精准修正] 获取【侵权检测】弹窗
        逻辑：
        1. 遍历所有可见的 modal-wrap
        2. 必须包含特定表头文字
        3. 必须包含可见的 '确定' 按钮
        """
        self._check_pause()
        end = time.time() + timeout

        while True:
            if not self.is_running: return None
            try:
                # 1. 找所有弹窗容器
                wrappers = driver.find_elements(By.XPATH, "//div[contains(@class, 'ivu-modal-wrap')]")

                for w in wrappers:
                    # 排除不可见和遮罩层较低的(虽然z-index不好直接判定，但is_displayed能过滤大部分)
                    if not w.is_displayed(): continue

                    try:
                        # 2. 验证内容特征 (防止误判为主编辑窗口)
                        # 使用 innerText 获取所有文本，检查是否包含特定的表头
                        content_text = w.get_attribute("innerText")
                        if "侵权词/敏感词/商标词/黑名单" not in content_text:
                            continue

                        # 3. 验证是否包含可见的 '确定' 按钮
                        # 这一步至关重要，用来区分主窗口(无确定按钮)和弹窗(有确定按钮)
                        confirm_btns = w.find_elements(By.XPATH, ".//button[contains(., '确定')]")
                        has_visible_btn = False
                        for btn in confirm_btns:
                            if btn.is_displayed():
                                has_visible_btn = True
                                break

                        if has_visible_btn:
                            # 找到了！高亮并返回内容层
                            modal_content = w.find_element(By.XPATH, ".//div[contains(@class, 'ivu-modal-content')]")
                            self._highlight(driver, modal_content, "orange")
                            return modal_content

                    except:
                        pass
            except:
                pass

            if timeout == 0: break
            if time.time() >= end: break
            time.sleep(0.5)

        return None

    def _flow_infringement_check(self, body_root, wait_time=10):
        self._log("🛡️ 侵权检测...", "black")
        copy_mod = self._get_copy_module(body_root)
        if not copy_mod: return

        chk_btn = self._find_in_root(copy_mod, "文案_侵权检测按钮", optional=True)
        if not self._safe_click(self.driver, chk_btn, "侵权检测"): return
        time.sleep(wait_time)

        # 1. 获取精准定位的弹窗
        inf_root = self._get_active_infringement_root(self.driver, timeout=5)

        if inf_root:
            self._log("   🚨 发现侵权弹窗 (双重验证通过)", "orange")
            confirmed = False

            # 2. 在锁定的弹窗内点击按钮
            for i in range(10):
                try:
                    # 直接找可见的 "确定" 按钮
                    btns = inf_root.find_elements(By.XPATH, ".//button[contains(., '确定')]")
                    target_btn = None
                    for b in btns:
                        if b.is_displayed():
                            target_btn = b
                            break

                    if target_btn:
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});",
                                                   target_btn)
                        time.sleep(0.5)
                        self._safe_click(self.driver, target_btn, "确认侵权")
                        confirmed = True
                        self._log("   ✅ 已点击确认按钮", "green")
                        break
                except:
                    pass
                time.sleep(1)

            if not confirmed:
                self._log("   ❌ 弹窗已找到但无法点击按钮", "red")
        else:
            self._log("   ✅ 无侵权 (未发现警告弹窗)", "green")

    def _force_close_popups(self):
        ai = self._get_active_ai_root(self.driver, timeout=0.5)
        if ai:
            btn = self._find_in_root(ai, "AI弹窗_取消按钮", optional=True)
            if btn: self._safe_click(self.driver, btn, "关闭残留AI")
            time.sleep(0.5)
        inf = self._get_active_infringement_root(self.driver, timeout=0.5)
        if inf:
            # 尝试使用特征定位关闭
            try:
                btn = inf.find_element(By.XPATH,
                                       ".//div[@class='ivu-modal-footer']//button[contains(@class, 'ivu-btn-default')]")
                self._safe_click(self.driver, btn, "关闭残留侵权")
            except:
                pass
            time.sleep(0.5)

    # ==========================================
    # 🚀 主流程
    # ==========================================
    def run(self):
        login_retry = 0
        while self.is_running and login_retry < 3:
            try:
                self._log("🚀 启动任务...", "blue")
                self.driver = self._init_driver()
                if not self._step_1_login(): raise Exception("登录失败")
                if not self._step_2_nav_to_listing(): raise Exception("导航失败")
                self._step_3_sku_loop()
                self._log("✅ 所有 SKU 处理完毕", "green")
                self.finished_signal.emit()
                break
            except Exception as e:
                self._log(f"❌ 全局异常: {e}", "red")
                traceback.print_exc()
                if self.driver:
                    try:
                        self.driver.quit()
                    except:
                        pass
                login_retry += 1
                time.sleep(3)
        # 只有在异常退出时才发错误信号，手动停止不发
        if login_retry >= 3 and self.is_running:
            self.error_signal.emit("三次启动尝试均失败")

    def _step_1_login(self):
        self._log("--- 步骤1: 登录 ---", "blue")
        try:
            self.driver.get("https://saaserp-pos.yibainetwork.com")
            try:
                self._wait_visible_then_rest(self.driver, '账号输入框', optional=True)
            except:
                pass
            if "login" in self.driver.current_url:
                user_in = self._find(self.driver, '账号输入框')
                user_in.clear()
                user_in.send_keys(self.config_data.get('USERNAME', ''))
                pwd_in = self._find(self.driver, '密码输入框')
                pwd_in.clear()
                pwd_in.send_keys(self.config_data.get('PASSWORD', ''))
                self._safe_click(self.driver, self._find(self.driver, '登录按钮'), "登录按钮")
                confirm_btn = self._wait_visible_then_rest(self.driver, '确认登录按钮', optional=True)
                if confirm_btn:
                    org_in = self._find(self.driver, '组织输入框', optional=True)
                    if org_in:
                        org_in.send_keys(self.config_data.get('ORG_CODE', '156'))
                        time.sleep(0.5)
                        self._safe_click(self.driver, self._find(self.driver, '组织列表项', optional=True))
                    self._safe_click(self.driver, confirm_btn, "确认登录按钮")
            WebDriverWait(self.driver, 20).until(EC.url_contains("home_page"))
            self._log("✅ 登录成功", "green")
            return True
        except RestartSkuException:
            raise
        except Exception as e:
            self._log(f"登录异常: {e}", "red")
            return False

    def _step_2_nav_to_listing(self):
        self._log("--- 步骤2: 切换刊登 ---", "blue")
        try:
            self._check_pause()
            erp_menu = self._find(self.driver, '导航_ERP菜单')
            ActionChains(self.driver).move_to_element(erp_menu).perform()
            nav_btn = self._wait_visible_then_rest(self.driver, '导航_刊登管理')
            if not nav_btn: return False
            handles_before = self.driver.window_handles
            self._safe_click(self.driver, nav_btn, "刊登管理菜单")
            WebDriverWait(self.driver, 10).until(EC.new_window_is_opened(handles_before))
            new_window = [w for w in self.driver.window_handles if w not in handles_before][0]
            self.driver.switch_to.window(new_window)
            self.work_window_handle = new_window
            WebDriverWait(self.driver, 15).until(EC.url_contains("message_center"))
            self._log("✅ 进入 Message Center", "green")
            return True
        except RestartSkuException:
            raise
        except Exception as e:
            self._log(f"导航异常: {e}", "red")
            return False

    def _step_3_sku_loop(self):
        for i, sku in enumerate(self.sku_list):
            if not self.is_running: break
            self._log(f"📦 [进度 {i + 1}/{len(self.sku_list)}] 处理 SKU: {sku}", "blue")
            success = False
            for retry in range(2):
                if not self.is_running: break
                try:
                    self._process_single_sku_flow(sku)
                    success = True
                    break
                except RestartSkuException:
                    self._log(f"🔁 配置已修复，重试...", "blue")
                    self._recover_page_state()
                    continue
                except Exception as e:
                    self._log(f"⚠️ 失败重试: {e}", "orange")
                    self._recover_page_state()
            if not success: self._log(f"❌ SKU {sku} 失败", "red")

    def _recover_page_state(self):
        try:
            self.driver.refresh()
            time.sleep(5)
            self._wait_loading_mask(self.driver)
        except:
            pass

    def _process_single_sku_flow(self, sku):
        self._check_pause()
        try:
            nav = self._find(self.driver, '菜单_刊登管理', optional=True)
            if nav:
                ActionChains(self.driver).move_to_element(nav).perform()
                self._safe_click(self.driver, self._find(self.driver, '菜单_产品列表', optional=True))
        except:
            pass
        self._wait_loading_mask(self.driver)
        WebDriverWait(self.driver, 15).until(EC.url_contains("product_list"))

        self._search_sku_logic(sku)

        time.sleep(2)
        try:
            btn_cfg = self._parse_config().get('弹窗_下一步按钮')
            if btn_cfg:
                all_next_btns = self.driver.find_elements(*btn_cfg['locator'])
                for btn in all_next_btns:
                    if btn.is_displayed():
                        self._log("   ✅ 点击 [下一步]", "green")
                        self._safe_click(self.driver, btn)
                        self._wait_loading_mask(self.driver)
                        time.sleep(2)
                        break
        except:
            pass

        # 层级定位
        root = self._wait_visible_then_rest(self.driver, '容器_Root')
        if not root: raise Exception("无法定位 Root")
        body = self._find_in_root(root, '容器_Body')
        if not body: raise Exception("无法定位 Body")

        shop_container = self._find_in_root(body, '容器_店铺区域')
        if not shop_container: raise Exception("无法定位 店铺区域")
        self._select_shop_logic(shop_container)

        if not self._wait_for_site_loading_strict(body):
            raise Exception("站点加载超时")

        self._execute_multi_site_logic(body)

        self._log("🏁 退出当前 SKU", "black")
        self._force_close_popups()

        # 取消按钮在当前可见的站点Span里找
        active_btn_container = self._get_active_site_btn_container(self._get_buttons_module(body))
        if active_btn_container:
            if self._safe_click(self.driver, self._find_in_root(active_btn_container, "按钮_取消", optional=True),
                                "取消"):
                time.sleep(1)
                confirm = self._find(self.driver, "退出确认弹窗_确定按钮", optional=True)
                if confirm: self._safe_click(self.driver, confirm, "确认退出")

        self._wait_loading_mask(self.driver)
        time.sleep(2)

    def _search_sku_logic(self, sku):
        inp = self._wait_visible_then_rest(self.driver, '搜索_SKU输入框')
        inp.clear()
        inp.send_keys(sku)
        self._safe_click(self.driver, self._find(self.driver, '搜索_查询按钮'), "查询")
        time.sleep(3)
        self._wait_loading_mask(self.driver)
        btns_cfg = self._parse_config().get('列表_刊登按钮')
        all_btns = self.driver.find_elements(*btns_cfg['locator'])
        vis = [b for b in all_btns if b.is_displayed()]
        if len(vis) == 1:
            self._safe_click(self.driver, vis[0], "精细刊登")
        else:
            raise Exception("商品搜索不唯一或未找到")

    def _select_shop_logic(self, shop_container):
        shop_in = self._find_in_root(shop_container, '店铺_输入框')
        if not shop_in: raise Exception("找不到店铺输入框")
        shop_in.click()
        shop_in.clear()
        shop_in.send_keys(self.shop_name)
        time.sleep(1)
        try:
            cfg = self._parse_config().get('店铺_下拉列表项')
            xpath = cfg['locator'][1] + f"[normalize-space(text())='{self.shop_name}']"
            self.driver.find_element(By.XPATH, xpath).click()
        except:
            shop_in.send_keys(Keys.ENTER)

    def _wait_for_site_loading_strict(self, body_root):
        self._log("⏳ 等待站点加载...", "blue")
        ai_btn_cfg = self._parse_config().get('文案_AI按钮')
        if not ai_btn_cfg: return False
        end = time.time() + ai_btn_cfg.get('timeout', 120)
        while time.time() < end:
            self._check_pause()
            btns = body_root.find_elements(*ai_btn_cfg['locator'])
            vis = len([b for b in btns if b.is_displayed()])
            if len(btns) >= 1 and vis >= 1: return True
            time.sleep(2)
        return False

    def _get_copy_module(self, body_root):
        try:
            main = self._find_in_root(body_root, '容器_Main')
            layout = self._find_in_root(main, '容器_布局Wrapper')
            site_divs = layout.find_elements(By.XPATH, "./div")
            active = next((s for s in site_divs if s.is_displayed()), None)
            if not active: return None
            return self._find_in_root(self._find_in_root(active, '容器_站点模块Wrapper'), '容器_文案模块')
        except:
            return None

    def _get_buttons_module(self, body_root):
        try:
            main = self._find_in_root(body_root, '容器_Main')
            # 先获取对象，不要直接 return
            btn_module = self._find_in_root(main, '容器_按钮模块')
            return btn_module
        except:
            return None

    def _get_active_site_btn_container(self, btn_module):
        """
        获取当前可见的 <span class="f-btn">
        结构: Footer -> Button(隐) -> Span(显) -> Span(隐)... -> Button(显)
        """
        if not btn_module: return None
        try:
            # 查找所有 class 为 f-btn 的 span
            # 注意：这里用 .//span 是因为有时结构会有微调，或者直接用 ./span
            site_groups = btn_module.find_elements(By.XPATH, "./span[contains(@class, 'f-btn')]")

            for group in site_groups:
                # 只要它是显示的，就是我们要找的当前站点操作区
                if group.is_displayed():
                    self._highlight(self.driver, group, "blue")
                    return group
        except Exception as e:
            self._log(f"定位站点按钮组失败: {e}", "gray")
        return None

    def _get_global_submit_btn(self, btn_module, timeout=5):
        """
        [修正版] 基于 HTML 结构定位全局提交按钮
        结构: ui-footer 下有多个 span 和两个 button。
        目标是: ui-footer 的直接子元素中的最后一个 button。
        """
        if not btn_module: return None

        end_time = time.time() + timeout
        while True:
            try:
                # 1. 查找 btn_module (ui-footer) 下的所有直接子 button
                # XPath: ./button
                btns = btn_module.find_elements(By.XPATH, "./button")

                if btns:
                    # 2. 根据分析，最后一个 button 就是目标
                    target = btns[-1]

                    # 3. 验证可见性
                    if target.is_displayed():
                        # 高亮为紫色以便确认
                        self._highlight(self.driver, target, "purple")
                        return target
            except:
                pass

            if time.time() > end_time: break
            time.sleep(0.5)

        return None

    def _verify_function_buttons(self, body_root):
        self._log("   🧐 验证功能按钮...", "black")
        btn_module = self._get_buttons_module(body_root)

        # 1. 全局按钮 (直接使用结构定位)
        global_btn = self._get_global_submit_btn(btn_module, timeout=5)
        if not global_btn:
            self._log("❌ 缺失 [按钮_提交所有] (结构定位失败)", "red")
            self.is_paused = True
            self._check_pause()
            return

        # 2. 站点按钮 (在可见Span下找)
        active_span = self._get_active_site_btn_container(btn_module)
        if not active_span:
            self._log("❌ 无法定位当前站点的按钮容器(Span)", "red")
            self.is_paused = True
            self._check_pause()
            return

        local_btns = ["按钮_取消", "按钮_同步", "按钮_翻译", "按钮_保存当前", "按钮_保存所有", "按钮_提交当前"]
        missing = []
        for name in local_btns:
            if not self._find_in_root(active_span, name, optional=True):
                missing.append(name)

        if missing:
            self._log(f"❌ 缺失按钮: {', '.join(missing)}", "red")
            self.is_paused = True
            self._check_pause()
        else:
            self._log("   ✅ 按钮校验通过", "green")

    def _execute_multi_site_logic(self, body_root):
        tabs = self._find_in_root(body_root, '容器_Tabs区域')
        items = tabs.find_elements(By.CSS_SELECTOR, "span.item")
        total = len(items)
        self.current_site_index = 0
        is_pub = "已推送" in items[0].get_attribute("textContent")
        self._log(f"👉 站点 1/{total}", "blue")

        self._verify_function_buttons(body_root)

        if not is_pub:
            self._flow_ai_generation(body_root)
            self._flow_infringement_check(body_root)
            self._handle_save_and_errors(self.driver, body_root)
            self._flow_sync_trans(body_root)
        else:
            self._flow_sync_trans(body_root)

        if total > 1:
            for i in range(1, total):
                if not self.is_running: break
                self.current_site_index = i
                tabs = self._find_in_root(body_root, '容器_Tabs区域')
                items = tabs.find_elements(By.CSS_SELECTOR, "span.item")
                if i >= len(items): break
                item = items[i]
                if "已推送" in item.get_attribute("textContent"):
                    self._log(f"👉 站点 {i + 1} 已推送", "gray")
                    continue

                self._log(f"👉 切换站点 {i + 1}", "blue")
                item.click()
                self._wait_loading_mask(self.driver)
                time.sleep(3)

                self._verify_function_buttons(body_root)
                self._flow_infringement_check(body_root, wait_time=5)
                self._handle_save_and_errors(self.driver, body_root)

    def _handle_save_and_errors(self, driver, body_root):
        # 1. 获取大的底部模块
        btn_module = self._get_buttons_module(body_root)
        if not btn_module:
            self._log("❌ 无法定位底部按钮模块", "red")
            return False

        # 2. 获取当前站点的按钮容器
        active_span = self._get_active_site_btn_container(btn_module)
        if not active_span:
            self._log("❌ 无法定位当前站点的按钮组", "red")
            return False

        self._log("💾 执行保存流程...", "black")

        # 3. 点击 [保存当前页] (局部按钮，仍在 active_span 里找)
        save_btn = self._find_in_root(active_span, "按钮_保存当前")
        if not self._safe_click(self.driver, save_btn, "保存当前页按钮"):
            return False

        self._wait_loading_mask(driver)
        time.sleep(2)

        # 4. [修改] 等待 [保存并提交所有站点] (使用结构定位：最后一个Button)
        self._log("   ⏳ 等待全局提交按钮恢复...", "gray")
        wait_success = False
        for _ in range(15):  # 约30秒超时
            g_btn = self._get_global_submit_btn(btn_module)
            if g_btn and g_btn.is_displayed():
                wait_success = True
                break
            time.sleep(2)

        if not wait_success:
            self._log("   ⚠️ 等待超时：全局提交按钮未恢复", "orange")

        # 5. 错误检测循环
        for attempt in range(2):
            has_error = False

            # A. 必填项
            try:
                errs = driver.find_elements(By.XPATH, "//div[contains(@class, 'ivu-notice') or contains(., '必填')]")
                vis = [e for e in errs if e.is_displayed() and "必填" in e.text]
                if vis:
                    self._log(f"   ⚠️ 发现必填项缺失 ({attempt + 1})", "orange")
                    try:
                        vis[0].find_element(By.CSS_SELECTOR, ".ivu-icon-ios-close").click()
                    except:
                        pass
                    self._fill_mandatory_fields()
                    has_error = True
            except:
                pass

            # B. 侵权弹窗
            inf_root = self._get_active_infringement_root(driver, timeout=1)
            if inf_root:
                self._log(f"   ⚠️ 保存触发侵权弹窗 ({attempt + 1})", "orange")
                # 使用新逻辑：在弹窗内找“确定”按钮
                try:
                    confirm = inf_root.find_element(By.XPATH,
                                                    ".//div[@class='ivu-modal-footer']//button[contains(@class, 'ivu-btn-primary')]")
                    self._safe_click(driver, confirm, "确认侵权")
                    time.sleep(1)
                except:
                    self._log("   ❌ 无法点击侵权确认按钮", "red")
                has_error = True

            # C. 重试保存
            if has_error:
                self._log("   🔄 错误已处理，重试保存...", "blue")
                # 重新获取引用，防止Stale
                btn_module = self._get_buttons_module(body_root)
                active_span = self._get_active_site_btn_container(btn_module)

                retry_btn = self._find_in_root(active_span, "按钮_保存当前")
                self._safe_click(driver, retry_btn, "重试保存")

                self._wait_loading_mask(driver)
                time.sleep(2)

                # 再次等待全局按钮 (结构定位)
                for _ in range(15):
                    g_btn = self._get_global_submit_btn(btn_module)
                    if g_btn and g_btn.is_displayed(): break
                    time.sleep(2)
            else:
                break

    def _fill_mandatory_fields(self):
        self._log("   🔧 填充必填项...", "gray")
        try:
            labels = self.driver.find_elements(By.XPATH, "//label[contains(., '*') or contains(., '必填')]")
            for lab in labels:
                if not lab.is_displayed(): continue
                try:
                    parent = lab.find_element(By.XPATH, "./..")
                    inp = parent.find_element(By.TAG_NAME, "input")
                    if not inp.get_attribute("value"): inp.send_keys("1")
                except:
                    pass
        except:
            pass

    def _flow_ai_generation(self, body_root):
        text_source = self.config_data.get('TEXT_SOURCE', '网页AI生成')
        if text_source == '跳过文案': return

        self._log("🤖 AI 文案...", "black")
        copy_mod = self._get_copy_module(body_root)
        if not copy_mod:
            self._log("❌ 未找到文案模块", "red")
            return

        ai_btn = self._find_in_root(copy_mod, "文案_AI按钮", optional=True)
        if not self._safe_click(self.driver, ai_btn, "AI按钮"): return

        self._log("   ⏳ 等待 AI 弹窗...", "black")
        ai_root = self._get_active_ai_root(self.driver, timeout=8)
        if not ai_root:
            self._log("❌ 未捕获到 AI 弹窗", "red")
            return

        for attempt in range(1, 4):
            if not self.is_running: return
            gen_btn = self._find_in_root(ai_root, "AI弹窗_生成按钮", optional=True)
            if gen_btn and gen_btn.is_displayed():
                time.sleep(1)
                self._safe_click(self.driver, gen_btn, "生成")
            time.sleep(10)
            if self._check_title_len(ai_root) > 20: break
            time.sleep(5)
            if self._check_title_len(ai_root) > 20: break

        apply_btn = self._find_in_root(ai_root, "AI弹窗_应用按钮", optional=True)
        if apply_btn: self._safe_click(self.driver, apply_btn, "应用")
        time.sleep(1)

    def _check_title_len(self, root):
        try:
            inp = self._find_in_root(root, "AI弹窗_标题输入框", optional=True)
            if inp: return len(inp.get_attribute("value"))
        except:
            pass
        return 0


    def _flow_sync_trans(self, body_root):
        self._log("🔄 同步与翻译...", "black")
        # 局部按钮
        btn_module = self._get_buttons_module(body_root)
        active_span = self._get_active_site_btn_container(btn_module)

        sync_btn = self._find_in_root(active_span, "按钮_同步", optional=True)
        if sync_btn:
            self._safe_click(self.driver, sync_btn, "同步")
            time.sleep(10)
        else:
            self._log("   ⚠️ 未找到同步", "gray")

        trans_btn = self._find_in_root(active_span, "按钮_翻译", optional=True)
        if trans_btn:
            self._safe_click(self.driver, trans_btn, "翻译")
            time.sleep(10)
        else:
            self._log("   ⚠️ 未找到翻译", "gray")