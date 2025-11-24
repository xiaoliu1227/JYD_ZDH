import time
import re
import traceback
from PyQt5.QtCore import QThread, pyqtSignal, QMutex, QWaitCondition
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    StaleElementReferenceException,
    WebDriverException,
    NoSuchElementException,
    TimeoutException,
    ElementClickInterceptedException
)

# ==========================================
# 1. 硬编码页面构造
# ==========================================

ROOT_XPATH = "//body/textarea/following-sibling::div[1]"
PREFIX_XPATH = "./div[2]/div/div/div[2]/div"

SHOP_INPUT_XPATH = f"{PREFIX_XPATH}/div[1]/div[1]/form/div[1]/div/div/div[1]/div/input"
SHOP_LIST_XPATH = f"{PREFIX_XPATH}/div[1]/div[1]/form/div[1]/div/div/div[2]/ul[2]"
SITE_CONTAINER_XPATH = f"{PREFIX_XPATH}/div[1]/div[2]/div[1]"
BUTTON_BAR_XPATH = f"{PREFIX_XPATH}/div[3]/div[2]"


class LocatorParser:
    @staticmethod
    def parse(locator_str: str) -> tuple:
        locator_str = locator_str.strip()
        if not locator_str: return None, None

        if locator_str.startswith('//') or locator_str.startswith('(') or locator_str.startswith('.//'):
            return (By.XPATH, locator_str)
        if locator_str.startswith('#') or locator_str.startswith('.'):
            return (By.CSS_SELECTOR, locator_str)
        attr_match = re.match(r'^([\w-]+)=\"(.*?)\"$', locator_str) or re.match(r"^([\w-]+)='(.*?)'$", locator_str)
        if attr_match:
            return (By.CSS_SELECTOR, f"[{attr_match.group(1)}='{attr_match.group(2)}']")

        if locator_str.startswith("<span>"):
            text = locator_str.replace("<span>", "").strip()
            return (By.XPATH, f".//span[contains(text(), '{text}')]")

        return (By.XPATH, f".//*[contains(text(), '{locator_str}')]")


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
        self.driver = None
        self.shop_name = config_data.get('ACCOUNT_NAME', '')
        self.text_source = config_data.get('TEXT_SOURCE', '网页AI生成')
        self.is_paused = False

    # ==========================================
    # 基础工具方法
    # ==========================================

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
                if by: parsed[ele['name']] = {'locator': (by, val), 'position': ele.get('position', '当前元素'),
                                              'index': int(ele.get('index', 1))}
        return parsed

    def _find(self, driver, wait, name, root_element=None, timeout=10):
        while self.is_running:
            cfg = self._parse_config().get(name)
            if not cfg:
                self._trigger_pause(f"配置缺失: {name}")
                continue
            try:
                locator = cfg['locator']
                ctx = root_element if root_element else driver

                if root_element:
                    el = ctx.find_element(*locator)
                else:
                    el = WebDriverWait(driver, timeout).until(EC.presence_of_element_located(locator))

                self._highlight(driver, el, "red")
                self.log_signal.emit(f"✅ 找到: {name}", "black")
                return el
            except Exception as e:
                self._trigger_pause(f"未找到: {name}\n{str(e)}")

    def _highlight(self, driver, element, color="red"):
        try:
            driver.execute_script(f"arguments[0].style.border='3px solid {color}'", element)
        except:
            pass

    def _safe_click(self, driver, element, name):
        try:
            element.click()
        except:
            driver.execute_script("arguments[0].click();", element)

    def _safe_input(self, driver, element, text):
        try:
            element.clear()
        except:
            pass
        element.send_keys(text)

    def _wait_loading_mask(self, driver, timeout=10):
        try:
            WebDriverWait(driver, timeout).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, ".el-loading-mask")))
        except:
            pass

    def _trigger_pause(self, reason):
        self.is_paused = True
        self.pause_required_signal.emit(reason)
        while self.is_paused and self.is_running:
            time.sleep(1)

    def resume_work(self, new_config_data=None):
        if new_config_data:
            self.config_data = new_config_data
            self.log_signal.emit("🔄 配置已更新，继续运行...", "green")
        self.is_paused = False

    def stop(self):
        self.is_running = False
        self.is_paused = False
        self.shutdown_driver()

    def shutdown_driver(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

    # ==========================================
    # 核心校验工具
    # ==========================================

    def _validate_unique_visible(self, driver, xpath, name, root_element=None):
        context = root_element if root_element else driver
        try:
            candidates = context.find_elements(By.XPATH, xpath)
        except Exception as e:
            self.log_signal.emit(f"❌ [{name}] XPath 语法错误: {e}", "red")
            return None

        visible_elements = [e for e in candidates if e.is_displayed()]
        count = len(visible_elements)

        if count == 0:
            self.log_signal.emit(f"⚠️ [{name}] 元素不可见", "red")
            return None
        elif count > 1:
            self.log_signal.emit(f"❌ [{name}] 发现 {count} 个可见元素，不唯一", "red")
            for e in visible_elements: self._highlight(driver, e, "purple")
            return None
        else:
            target = visible_elements[0]
            self._highlight(driver, target, "red")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", target)
            return target

    def _force_close_any_popup(self, driver):
        try:
            # 查找特定位置的弹窗
            popups = driver.find_elements(By.XPATH, "//body/div[@top='5vh']")

            for popup in popups:
                if not popup.is_displayed():
                    continue

                # 尝试在当前弹窗和下一个div中查找取消按钮
                elements_to_check = [popup]

                # 添加下一个div sibling
                try:
                    next_div = popup.find_element(By.XPATH, "./following-sibling::div[1]")
                    if next_div.is_displayed():
                        elements_to_check.append(next_div)
                except:
                    pass

                # 在这些元素中查找取消按钮
                for element in elements_to_check:
                    try:
                        cancel_btn = element.find_element(By.XPATH, ".//button//span[contains(text(), '取消')]")
                        driver.execute_script("arguments[0].click();", cancel_btn)
                        time.sleep(0.5)
                        break  # 点击成功后跳出循环
                    except:
                        continue

        except Exception:
            # 可以记录日志，这里保持静默处理
            pass

    # ==========================================
    # 业务流程逻辑
    # ==========================================

    def run(self):
        try:
            self.log_signal.emit("🚀 正在启动 Edge 浏览器...", "blue")
            self.driver = self._init_driver()
            wait = WebDriverWait(self.driver, 20)

            self._execute_login(self.driver, wait)
            if not self.is_running: return

            self._execute_navigation(self.driver, wait)
            if not self.is_running: return

            self._execute_listing_loop(self.driver, wait)

            self.log_signal.emit("✅ 全量结构校验任务结束。", "green")
            self.finished_signal.emit()

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            err_msg = str(e)
            if "disconnected" in err_msg or "no such window" in err_msg:
                self.log_signal.emit("⚠️ 浏览器已关闭，任务停止。", "red")
            else:
                self.log_signal.emit(f"❌ 严重错误: {err_msg}", "red")
                self.error_signal.emit(err_msg)
        finally:
            pass

    def _execute_login(self, driver, wait):
        self.log_signal.emit("--- 开始登录流程 ---", "blue")
        driver.get(self.config_data.get('LOGIN_URL', ''))

        self._find(driver, wait, '账号输入框').send_keys(self.config_data.get('USERNAME', ''))
        self._find(driver, wait, '密码输入框').send_keys(self.config_data.get('PASSWORD', ''))

        btn = self._find(driver, wait, '登录按钮')
        self._safe_click(driver, btn, "登录")

        try:
            self._wait_loading_mask(driver, 3)
            self._find(driver, wait, '组织选择弹窗', timeout=5)
            self._find(driver, wait, '组织输入框').send_keys(self.config_data.get('ORG_CODE', '156'))
            time.sleep(0.5)
            self._safe_click(driver, self._find(driver, wait, '组织列表项'), "选组织")
            self._safe_click(driver, self._find(driver, wait, '确认登录按钮'), "确认登录")
        except:
            pass
        wait.until(EC.url_contains("home_page"))

    def _execute_navigation(self, driver, wait):
        self.log_signal.emit("--- 开始导航流程 ---", "blue")
        try:
            erp = self._find(driver, wait, '导航_ERP菜单', timeout=5)
            ActionChains(driver).move_to_element(erp).perform()
        except:
            pass
        handles = driver.window_handles
        self._safe_click(driver, self._find(driver, wait, '导航_刊登管理'), "刊登管理")
        WebDriverWait(driver, 10).until(EC.new_window_is_opened(handles))
        driver.switch_to.window([w for w in driver.window_handles if w not in handles][0])

    def _execute_listing_loop(self, driver, wait):
        self.log_signal.emit("--- 进入业务页面 ---", "blue")
        try:
            menu = self._find(driver, wait, '菜单_刊登管理', timeout=5)
            ActionChains(driver).move_to_element(menu).perform()
        except:
            pass
        self._safe_click(driver, self._find(driver, wait, '菜单_产品列表'), "产品列表")
        self._wait_loading_mask(driver)

        if not self.sku_list:
            self.log_signal.emit("SKU 列表为空", "red");
            return

        sku = self.sku_list[0]
        self.log_signal.emit(f"🔍 处理 SKU: {sku}", "blue")

        # 搜索
        search_success = False
        for retry in range(3):
            self.log_signal.emit(f"⏳ 准备搜索 (Wait 3s)...", "black")
            time.sleep(3)
            inp = self._find(driver, wait, '搜索_SKU输入框')
            inp.clear();
            self._safe_input(driver, inp, sku)
            self._safe_click(driver, self._find(driver, wait, '搜索_查询按钮'), "查询")
            self._wait_loading_mask(driver)
            time.sleep(2)

            list_btn_cfg = self._parse_config().get('列表_刊登按钮')
            if not list_btn_cfg:
                self.log_signal.emit("❌ 配置缺失: 列表_刊登按钮", "red");
                return

            all_btns = driver.find_elements(*list_btn_cfg['locator'])
            visible_btns = [b for b in all_btns if b.is_displayed()]

            if len(visible_btns) == 1:
                self.log_signal.emit("✅ 搜索结果唯一，准备刊登", "green")
                self._safe_click(driver, visible_btns[0], "刊登")
                search_success = True;
                break
            elif len(visible_btns) == 0:
                self.log_signal.emit(f"⚠️ 未找到结果，重试...", "red")
            else:
                self.log_signal.emit(f"⚠️ 结果不唯一，重试...", "red")

        if not search_success: return

        # 弹窗
        for i in range(5):
            try:
                btn_cfg = self._parse_config().get('弹窗_下一步按钮')
                if not btn_cfg: break
                nxt = WebDriverWait(driver, 2).until(EC.visibility_of_element_located(btn_cfg['locator']))
                self.log_signal.emit(f"检测到弹窗，强制等待 3s...", "black")
                time.sleep(3);
                nxt.click();
                time.sleep(1)
            except:
                break

        self._wait_loading_mask(driver)
        self.log_signal.emit("进入编辑页面...", "blue")
        time.sleep(3)

        # Root & Shop
        self.log_signal.emit(f"1️⃣ 定位 Root...", "black")
        root_element = self._validate_unique_visible(driver, ROOT_XPATH, "Root节点")
        if not root_element: return

        if not self.shop_name:
            self.log_signal.emit("❌ 未配置店铺名称！", "red");
            return

        self.log_signal.emit(f"2️⃣ 选择店铺: {self.shop_name} ...", "blue")
        if not self._handle_shop_selection(driver, root_element): return

        if not self._wait_for_site_status_stable(driver, root_element): return

        try:
            container = root_element.find_element(By.XPATH, SITE_CONTAINER_XPATH)
            site_items = container.find_elements(By.CSS_SELECTOR, "span.item")
            site_count = len(site_items)
            self.log_signal.emit(f"📊 准备遍历 {site_count} 个站点...", "blue")
        except Exception as e:
            self.log_signal.emit(f"❌ 获取站点列表失败: {e}", "red");
            return

        for i in range(site_count):
            if not self.is_running: break
            self.log_signal.emit("----------------------------------------", "black")

            try:
                current_root = driver.find_element(By.XPATH, ROOT_XPATH)
                current_container = current_root.find_element(By.XPATH, SITE_CONTAINER_XPATH)
                target_item = current_container.find_elements(By.CSS_SELECTOR, "span.item")[i]

                current_site_index = i + 1
                full_text = target_item.get_attribute("textContent").replace("\n", " ").strip()
                site_name = full_text.split('[')[0].strip()

                self.log_signal.emit(f"👉 [{current_site_index}/{site_count}] 切换: {site_name}", "blue")

                try:
                    target_item.click()
                except ElementClickInterceptedException:
                    self.log_signal.emit("   ⚠️ 点击被拦截，尝试清理弹窗...", "red")
                    self._force_close_any_popup(driver)
                    target_item.click()

                time.sleep(2)

                active_root = self._validate_unique_visible(driver, ROOT_XPATH, "Root节点")
                if not active_root: continue

                # 模块校验
                path = f"{PREFIX_XPATH}/div[3]/div[1]/div[{current_site_index}]/div/div[1]"
                if self._validate_unique_visible(driver, path, "刊登配置", active_root): pass

                path = f"{PREFIX_XPATH}/div[3]/div[1]/div[{current_site_index}]/div/div[2]"
                info_mod = self._validate_unique_visible(driver, path, "产品信息", active_root)
                if info_mod: self._check_image_button(driver, info_mod)

                path = f"{PREFIX_XPATH}/div[3]/div[1]/div[{current_site_index}]/div/div[4]/div[1]"
                text_mod = self._validate_unique_visible(driver, path, "产品文案", active_root)
                if text_mod:
                    self._check_text_buttons(driver, text_mod)
                    self._execute_ai_popup_check(driver, text_mod, current_site_index)
                    self._execute_infringement_check(driver, text_mod, current_site_index)

                # --- 修复：按钮栏校验 (传入站点索引) ---
                btn_mod = self._validate_unique_visible(driver, BUTTON_BAR_XPATH, "操作按钮", active_root)
                if btn_mod:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", btn_mod)
                    time.sleep(0.5)
                    # 传入 current_site_index
                    self._check_action_buttons(driver, btn_mod, current_site_index)

                # self._force_close_any_popup(driver)

            except Exception as ex:
                self.log_signal.emit(f"❌ 遍历异常: {ex}", "red")

        self.log_signal.emit("========================================", "blue")
        self.log_signal.emit("🛑 校验结束。", "green")
        return

    # ==========================================
    # 核心修复：按钮栏定位
    # ==========================================

    def _check_action_buttons(self, driver, module_element, site_index):
        """
        根据站点索引，精准定位对应的 Span。
        逻辑：Container -> (Ignore) -> Span(X) -> ...
        """

        # 1. 公用按钮 (始终存在且可见)
        try:
            # 假设它在容器最后，或者用文本匹配
            submit_all = module_element.find_element(By.XPATH, ".//span[contains(text(), '保存并提交所有站点')]")
            self._highlight(driver, submit_all, "green")
            self.log_signal.emit("   ✅ 找到: 按钮_提交所有", "green")
        except:
            self.log_signal.emit("   ❌ 按钮_提交所有 缺失", "red")

        # 2. 查找对应站点的 Span (第 site_index 个 span)
        try:
            spans = module_element.find_elements(By.TAG_NAME, "span")

            save_current_btn_xpath = ".//span[contains(text(), '保存当前页')]/ancestor::span[1]"
            # 找到所有这样的容器
            containers = module_element.find_elements(By.XPATH, save_current_btn_xpath)

            # 取第 site_index 个 (如果是按顺序排列的话)
            # 或者取可见的那个
            target_container = None

            # 优先尝试取可见的
            for c in containers:
                if c.is_displayed():
                    target_container = c
                    break

            if target_container:
                self._highlight(driver, target_container, "blue")  # 蓝色框出当前按钮区

                # 检查内部6个按钮
                btn_keys = ["按钮_取消", "按钮_同步未推送", "按钮_翻译", "按钮_保存当前",
                            "按钮_保存所有", "按钮_提交当前"]

                found_count = 0
                for key in btn_keys:
                    cfg = self._parse_config().get(key)
                    try:
                        btn = target_container.find_element(*cfg['locator'])
                        self._highlight(driver, btn, "green")
                        found_count += 1
                    except:
                        self.log_signal.emit(f"   ❌ {key} 缺失", "red")

                if found_count == 6:
                    self.log_signal.emit("   ✅ 私有按钮(6个)全部齐备", "green")
            else:
                self.log_signal.emit("   ❌ 未找到当前站点的按钮容器 (可见性检查失败)", "red")

        except Exception as e:
            self.log_signal.emit(f"   ❌ 按钮栏检查错误: {e}", "red")

    # --- 其他内部检查 ---
    def _check_image_button(self, driver, mod):
        cfg = self._parse_config().get("信息_选择图片按钮")
        if not cfg: return
        try:
            all_btns = mod.find_elements(*cfg['locator'])
            visible_btns = [b for b in all_btns if b.is_displayed()]
            count = len(visible_btns)
            if count == 1:
                self.log_signal.emit("   ✅ 图片按钮唯一", "green")
                self._highlight(driver, visible_btns[0], "green")
            elif count > 1:
                self.log_signal.emit("   ⚠️ 多个图片按钮 -> 跳过", "red")
            else:
                self.log_signal.emit("   ❌ 无图片按钮", "red")
        except:
            pass

    def _check_text_buttons(self, driver, mod):
        for k in ["文案_侵权检测按钮", "文案_AI按钮"]:
            cfg = self._parse_config().get(k)
            if not cfg: continue
            try:
                el = mod.find_element(*cfg['locator'])
                if el.is_displayed():
                    self._highlight(driver, el, "green")
                    self.log_signal.emit(f"   ✅ {k} OK", "green")
                else:
                    self.log_signal.emit(f"   ❌ {k} 不可见", "red")
            except:
                self.log_signal.emit(f"   ❌ {k} 缺失", "red")

    def _execute_ai_popup_check(self, driver, text_mod, site_index):
        self.log_signal.emit("   🤖 校验 AI...", "black")
        try:
            btn = text_mod.find_element(*self._parse_config().get("文案_AI按钮")['locator'])
            driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", btn)
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(3)
        except:
            return

        pop_xp = f"//body/div[@top='5vh'][{site_index}]"
        pop = self._validate_unique_visible(driver, pop_xp, "AI弹窗")
        if not pop: return

        for k in ["AI弹窗_生成按钮", "AI弹窗_应用按钮"]:
            try:
                self._highlight(driver, pop.find_element(*self._parse_config().get(k)['locator']), "green")
            except:
                self.log_signal.emit(f"   ❌ {k} 缺失", "red")

        try:
            self._highlight(driver, pop.find_element(*self._parse_config().get("AI弹窗_标题输入框")['locator']),
                            "green")
        except:
            self.log_signal.emit("   ❌ 标题框缺失", "red")

        time.sleep(2)
        try:
            c = pop.find_element(*self._parse_config().get("AI弹窗_取消按钮")['locator'])
            driver.execute_script("arguments[0].click();", c);
            time.sleep(1.5)
        except:
            pass

    def _execute_infringement_check(self, driver, text_mod, site_index):
        self.log_signal.emit("   🛡️ 侵权检测...", "black")
        try:
            btn = text_mod.find_element(*self._parse_config().get("文案_侵权检测按钮")['locator'])
            driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", btn)
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(5)
        except:
            return

        xp = f"//body/div[@top='5vh'][{site_index}]/following-sibling::div[1]"
        for _ in range(2):
            try:
                p = driver.find_element(By.XPATH, xp)
                if p.is_displayed() and "侵权" in p.get_attribute("textContent"):
                    self.log_signal.emit("   ⚠️ 发现弹窗", "red")
                    self._highlight(driver, p, "red")
                    try:
                        c = p.find_element(*self._parse_config().get("侵权弹窗_取消按钮")['locator'])
                        driver.execute_script("arguments[0].click();", c)
                        self.log_signal.emit("   ✅ 已取消", "green")
                        time.sleep(2)
                    except:
                        pass
                    break
                else:
                    time.sleep(2)
            except:
                time.sleep(2)

    def _handle_shop_selection(self, driver, root):
        ib = self._validate_unique_visible(driver, SHOP_INPUT_XPATH, "输入框", root)
        if not ib: return False
        try:
            ib.click(); ib.clear(); ib.send_keys(self.shop_name); time.sleep(1)
        except:
            return False

        lc = self._validate_unique_visible(driver, SHOP_LIST_XPATH, "列表", root)
        if not lc:
            try:
                lc = driver.find_element(By.CSS_SELECTOR, ".ivu-select-dropdown:not([style*='display: none'])")
                self._highlight(driver, lc, "red")
            except:
                return False

        try:
            li = lc.find_element(By.XPATH, f".//li[contains(text(), '{self.shop_name}')]")
            self._highlight(driver, li, "red")
            li.click();
            self.log_signal.emit(f"✅ 已选: {self.shop_name}", "green");
            return True
        except:
            ib.send_keys(u'\ue007');
            return True

    def _wait_for_site_status_stable(self, driver, root):
        self.log_signal.emit("⏳ 等待加载...", "black");
        time.sleep(10)
        last = []
        for _ in range(12):
            if not self.is_running: return False
            try:
                con = root.find_element(By.XPATH, SITE_CONTAINER_XPATH)
                items = con.find_elements(By.CSS_SELECTOR, "span.item")
                curr = [i.get_attribute("textContent").strip() for i in items]
                if not curr: time.sleep(5); continue

                bad = False
                for t in curr:
                    if "[" not in t or "]" not in t: bad = True; break
                if bad: time.sleep(5); continue

                if curr == last: return True
                last = curr;
                time.sleep(5)
            except:
                time.sleep(5)
        return False