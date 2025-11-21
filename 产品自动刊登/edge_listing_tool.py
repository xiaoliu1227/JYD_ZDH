import time
import re
from PyQt5.QtCore import QThread, pyqtSignal, QMutex, QWaitCondition
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (ElementNotInteractableException,
                                        ElementClickInterceptedException,
                                        StaleElementReferenceException,
                                        WebDriverException,
                                        NoSuchElementException,
                                        TimeoutException)


class LocatorParser:
    @staticmethod
    def parse(locator_str: str) -> tuple:
        locator_str = locator_str.strip()
        if not locator_str: return None, None
        # 智能判断
        if locator_str.startswith('//') or locator_str.startswith('.') or locator_str.startswith('#'):
            return (By.XPATH, locator_str) if locator_str.startswith('//') or locator_str.startswith('.//') else (
                By.CSS_SELECTOR, locator_str)
        # 属性
        attr_match = re.match(r'^([\w-]+)=\"(.*?)\"$', locator_str) or re.match(r"^([\w-]+)='(.*?)'$", locator_str)
        if attr_match: return (By.CSS_SELECTOR, f"[{attr_match.group(1)}='{attr_match.group(2)}']")
        # 文本
        if re.match(r"^<\w+>.*$", locator_str) or locator_str.startswith("<span"):
            if locator_str.startswith("<span>"): return (By.XPATH,
                                                         f"//span[contains(text(), '{locator_str.replace('<span>', '').strip()}')]")
        return (By.XPATH, f"//*[contains(text(), '{locator_str}')]")


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

        self.mutex = QMutex()
        self.cond = QWaitCondition()
        self.is_paused = False

    def stop(self):
        self.is_running = False
        self.resume_work()

    def resume_work(self, new_config_data=None):
        self.mutex.lock()
        if new_config_data:
            self.config_data = new_config_data
            self.log_signal.emit("🔄 配置已更新，继续运行...", "green")
        self.is_paused = False
        self.cond.wakeAll()
        self.mutex.unlock()

    def run(self):
        try:
            self.log_signal.emit("正在启动浏览器...", "black")
            self.driver = self._init_driver()
            wait = WebDriverWait(self.driver, 20)

            # 1. 登录
            self._execute_login(self.driver, wait)
            if not self.is_running: return

            # 2. 导航
            self._execute_navigation(self.driver, wait)
            if not self.is_running: return

            # 3. 循环处理
            self._execute_listing_loop(self.driver, wait)

            self.finished_signal.emit()

        except Exception as e:
            import traceback
            err_msg = str(e)
            if "disconnected" in err_msg or "no such window" in err_msg:
                self.log_signal.emit("⚠️ 浏览器已断开，任务停止。", "red")
            else:
                self.log_signal.emit(f"❌ 运行错误: {err_msg}", "red")
                self.error_signal.emit(err_msg)
        finally:
            pass

    def _init_driver(self):
        options = EdgeOptions()
        if self.is_headless:
            options.add_argument("--headless");
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
        else:
            options.add_argument("--start-maximized")
        return webdriver.Edge(options=options)

    def _parse_config(self):
        parsed = {}
        for mod in self.config_data.get('ELEMENT_CONFIG', []):
            for ele in mod['elements']:
                by, val = LocatorParser.parse(ele['locator'])
                if by: parsed[ele['name']] = {'locator': (by, val), 'position': ele.get('position', '当前元素'),
                                              'index': int(ele.get('index', 1))}
        return parsed

    def _find(self, driver, wait, name, root_element=None):
        while self.is_running:
            current_config_map = self._parse_config()
            cfg = current_config_map.get(name)

            if not cfg:
                self._trigger_pause(f"代码错误：配置中找不到元素 '{name}'")
                continue

            locator, index, position = cfg['locator'], cfg['index'], cfg['position']
            context = root_element if root_element else driver

            try:
                if index > 1:
                    def find_all(d):
                        eles = context.find_elements(*locator)
                        return eles if len(eles) >= index else False

                    found = WebDriverWait(driver, 5).until(find_all)
                    base = found[index - 1]
                else:
                    if root_element:
                        # 在元素下查找，手动轮询
                        base = None
                        for _ in range(10):  # 5秒
                            try:
                                els = context.find_elements(*locator)
                                if els:
                                    base = els[0]
                                    break
                            except:
                                pass
                            time.sleep(0.5)
                        if not base: raise NoSuchElementException(f"Relative lookup failed: {locator}")
                    else:
                        base = WebDriverWait(driver, 5).until(EC.presence_of_element_located(locator))

                if position == "父元素":
                    base = base.find_element(By.XPATH, "./..")
                elif position == "子元素":
                    base = base.find_element(By.XPATH, "./*[1]")
                elif position == "上一个":
                    base = base.find_element(By.XPATH, "preceding-sibling::*[1]")
                elif position == "下一个":
                    base = base.find_element(By.XPATH, "following-sibling::*[1]")

                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", base)
                except:
                    pass
                return base

            except Exception as e:
                self.log_signal.emit(f"⚠️ 抓取失败[{name}]: {str(e).splitlines()[0]}", "red")
                self._trigger_pause(f"抓取失败: {name}")

    def _trigger_pause(self, reason):
        self.is_paused = True
        self.pause_required_signal.emit(reason)
        self.log_signal.emit(f"⏸️ 程序已暂停 ({reason})", "red")
        self.mutex.lock()
        if self.is_paused:
            self.cond.wait(self.mutex)
        self.mutex.unlock()

    def _safe_click(self, driver, element, name="元素"):
        try:
            element.click()
        except Exception as e:
            self.log_signal.emit(f"点击 {name} 受阻，尝试强制点击...", "blue")
            driver.execute_script("arguments[0].click();", element)

    def _safe_input(self, driver, element, text):
        try:
            element.clear()
        except:
            driver.execute_script("arguments[0].value = '';", element)
        try:
            element.send_keys(text)
        except:
            time.sleep(1); element.send_keys(text)

    def _wait_loading(self, driver, wait, timeout=10):
        try:
            masks = driver.find_elements(By.CSS_SELECTOR, ".el-loading-mask")
            for m in masks:
                if m.is_displayed():
                    WebDriverWait(driver, timeout).until(
                        EC.invisibility_of_element_located((By.CSS_SELECTOR, ".el-loading-mask")))
                    break
        except:
            pass

    def _get_active_container(self, driver):
        self.log_signal.emit("🔍 正在定位【页面结构基座】...", "black")
        wrapper = self._find(driver, None, '结构_内容包装器')
        active_site = self._find(driver, None, '结构_激活站点容器', root_element=wrapper)
        self.log_signal.emit("✅ 成功锁定当前站点操作区域。", "green")
        return active_site

    def _get_active_ai_popup(self, driver):
        self.log_signal.emit("寻找激活的 AI 弹窗...", "black")
        # 使用 parse 解析配置中的 locator
        raw_locator = self._parse_config()['结构_AI弹窗列表']['locator']
        candidates = driver.find_elements(*raw_locator)

        for div in candidates:
            try:
                if div.find_element(By.CSS_SELECTOR, ".ivu-modal").is_displayed():
                    return div
            except:
                continue
        self.log_signal.emit("⚠️ 未找到可见 AI 弹窗。", "red")
        return None

    def _wait_for_site_status(self, driver, timeout=60):
        self.log_signal.emit("开始监控站点加载状态...", "black")
        end_time = time.time() + timeout
        last_log_time = 0

        try:
            container = self._find(driver, None, '编辑_站点容器')
        except:
            return False

        while time.time() < end_time:
            try:
                if driver.find_elements(By.CSS_SELECTOR, ".el-loading-mask"):
                    masks = [m for m in driver.find_elements(By.CSS_SELECTOR, ".el-loading-mask") if m.is_displayed()]
                    if masks: time.sleep(0.5); continue

                try:
                    items = container.find_elements(By.CSS_SELECTOR, "span.item")
                except StaleElementReferenceException:
                    container = self._find(driver, None, '编辑_站点容器');
                    continue

                if not items:
                    if time.time() - last_log_time >= 5:
                        self.log_signal.emit("⏳ 容器内暂无按钮...", "blue")
                        last_log_time = time.time()
                    time.sleep(0.5);
                    continue

                all_ready = True
                status_logs = []
                for item in items:
                    try:
                        name = item.find_element(By.CSS_SELECTOR, "button > span > span:nth-child(1)").get_attribute(
                            "textContent").strip()
                        status = item.find_element(By.CSS_SELECTOR, "button > span > span:nth-child(2)").get_attribute(
                            "textContent").strip()
                        mark = "★" if "iskeep" in item.get_attribute("class") else ""
                        status_logs.append(f"{mark}{name}{status}")
                        if "[" not in status or "]" not in status: all_ready = False; continue
                        content = status.split('[')[1].split(']')[0].strip()
                        if content == "": continue
                        if bool(re.search(r'[\u4e00-\u9fa5]', content)): continue
                        all_ready = False
                    except:
                        all_ready = False; break

                if time.time() - last_log_time >= 5:
                    self.log_signal.emit(f"⏳ 监控: {' | '.join(status_logs)}", "blue")
                    last_log_time = time.time()

                if all_ready and len(items) > 0:
                    self.log_signal.emit(f"✅ 站点加载完毕!", "green")
                    return True
            except:
                time.sleep(0.5); continue
            time.sleep(0.5)
        self.log_signal.emit("⚠️ 等待超时。", "red");
        return False

    # --- 流程 ---
    def _execute_login(self, driver, wait):
        self.log_signal.emit("开始登录...", "blue")
        driver.get(self.config_data.get('LOGIN_URL', ''))
        self._find(driver, wait, '账号输入框').send_keys(self.config_data.get('USERNAME', ''))
        self._find(driver, wait, '密码输入框').send_keys(self.config_data.get('PASSWORD', ''))
        self._find(driver, wait, '登录按钮').click()
        self._wait_loading(driver, wait)
        self._find(driver, wait, '组织选择弹窗')
        self._find(driver, wait, '组织输入框').send_keys(self.config_data.get('ORG_CODE', '156'))
        time.sleep(1)
        try:
            self._find(driver, wait, '组织列表项').click()
        except:
            pass
        self._find(driver, wait, '确认登录按钮').click()
        wait.until(EC.url_contains("home_page"))

    def _execute_navigation(self, driver, wait):
        windows_before = driver.window_handles
        self.log_signal.emit("导航...", "black")
        try:
            erp = self._find(driver, wait, '导航_ERP菜单')
            WebDriverWait(driver, 5).until(EC.visibility_of(erp))
            ActionChains(driver).move_to_element(erp).perform()
            time.sleep(1.5)
        except:
            pass
        btn = self._find(driver, wait, '导航_刊登管理')
        self._safe_click(driver, btn, "菜单")
        wait.until(EC.new_window_is_opened(windows_before))
        driver.switch_to.window([w for w in driver.window_handles if w not in windows_before][0])

    def _execute_listing_loop(self, driver, wait):
        try:
            menu = self._find(driver, wait, '菜单_刊登管理')
            WebDriverWait(driver, 5).until(EC.visibility_of(menu))
            ActionChains(driver).move_to_element(menu).perform()
            time.sleep(1)
        except:
            pass

        prod_btn = self._find(driver, wait, '菜单_产品列表')
        self._safe_click(driver, prod_btn, "产品列表")
        self._wait_loading(driver, wait)

        if not self.sku_list: return
        sku = self.sku_list[0]
        self.log_signal.emit(f"--- 处理 SKU: {sku} ---", "blue")

        self._wait_loading(driver, wait, timeout=5)

        inp = self._find(driver, wait, '搜索_SKU输入框')
        self._safe_input(driver, inp, sku)
        search_btn = self._find(driver, wait, '搜索_查询按钮')
        self._safe_click(driver, search_btn, "查询")
        self._wait_loading(driver, wait, timeout=15)
        time.sleep(1)

        list_btn = self._find(driver, wait, '列表_刊登按钮')
        self._safe_click(driver, list_btn, "刊登")

        # 循环点击下一步
        self.log_signal.emit("点击下一步...", "blue")
        time.sleep(2)
        success = False
        next_btn_cfg = self._parse_config().get('弹窗_下一步按钮')
        for i in range(15):
            try:
                if not next_btn_cfg: break
                btn = WebDriverWait(driver, 2).until(EC.presence_of_element_located(next_btn_cfg['locator']))
                if btn.is_displayed() and btn.is_enabled():
                    btn.click()
                    self.log_signal.emit(f"点击 {i + 1}...", "black")
                    time.sleep(2)
                else:
                    success = True; break
            except:
                success = True; break

        if not success: self.log_signal.emit("⚠️ 强制进入编辑页...", "red")

        self.log_signal.emit("等待编辑页...", "blue")
        self._wait_loading(driver, wait)
        time.sleep(2)

        if not self.shop_name: return
        self.log_signal.emit(f"选择店铺: {self.shop_name}", "black")

        shop_input = self._find(driver, wait, '编辑_店铺输入框')
        self._safe_click(driver, shop_input, "店铺输入框")
        time.sleep(0.5)
        self._safe_input(driver, shop_input, self.shop_name)
        time.sleep(1.5)

        try:
            list_container = self._find(driver, wait, '编辑_店铺列表容器')
            target_xpath = f".//li[contains(., '{self.shop_name}')]"
            target_option = list_container.find_element(By.XPATH, target_xpath)
            self._safe_click(driver, target_option, f"店铺-{self.shop_name}")
            self.log_signal.emit(f"✅ 已选中店铺", "green")

            # 1. 等待站点
            self._wait_for_site_status(driver)

            # 2. 获取容器
            active_container = self._get_active_container(driver)

            # 3. 填单
            self._fill_module_config(driver, wait, active_container)
            self._fill_module_info(driver, wait, active_container)
            self._fill_module_text(driver, wait, active_container)
            self._handle_submission(driver, wait)

        except Exception as ex:
            self.log_signal.emit(f"⚠️ 流程异常: {str(ex)}", "red")

        self.log_signal.emit("🛑 流程结束。", "green")

    # --- 模块逻辑 ---
    def _fill_module_config(self, driver, wait, container):
        self.log_signal.emit("--> 模块 E: 刊登配置", "blue")
        try:
            self._get_active_container(driver)  # 仅测试
        except:
            pass

    def _fill_module_info(self, driver, wait, container):
        self.log_signal.emit("--> 模块 F: 产品信息", "blue")

    def _fill_module_text(self, driver, wait, container):
        self.log_signal.emit(f"--> 模块 G: 产品文案", "blue")
        if "网页" not in self.text_source: return

        try:
            # 1. 打开 AI
            self.log_signal.emit("打开 AI 弹窗...", "black")
            ai_btn = self._find(driver, wait, '文案_打开AI按钮', root_element=container)
            self._safe_click(driver, ai_btn, "AI按钮")

            time.sleep(2)
            # 2. 定位 AI 弹窗容器
            ai_popup = self._get_active_ai_popup(driver)
            if not ai_popup: raise Exception("AI 弹窗定位失败")

            # 3. 生成
            gen_btn = self._find(driver, wait, 'AI_生成按钮', root_element=ai_popup)
            self._safe_click(driver, gen_btn, "生成")

            self.log_signal.emit("AI 生成中...", "blue")
            title_box = self._find(driver, wait, 'AI_标题输出框', root_element=ai_popup)

            start = time.time();
            generated = False
            while time.time() - start < 120:
                val = title_box.get_attribute("value")
                if val and len(val) > 30:
                    generated = True;
                    self.log_signal.emit(f"✅ 生成完毕", "green");
                    break
                time.sleep(2)
            if not generated: self.log_signal.emit("⚠️ 生成超时", "red")

            apply_btn = self._find(driver, wait, 'AI_应用所有按钮', root_element=ai_popup)
            self._safe_click(driver, apply_btn, "应用按钮")
            time.sleep(1)

            # 4. 侵权检测
            self.log_signal.emit("侵权检测...", "black")
            check_btn = self._find(driver, wait, '文案_检测侵权按钮', root_element=container)
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", check_btn)
            self._safe_click(driver, check_btn, "侵权检测")

            time.sleep(1.5)
            try:
                # 弹窗确认是全局的
                confirm_cfg = self._parse_config()['侵权_弹窗确认按钮']
                confirm_btn = WebDriverWait(driver, 3).until(EC.visibility_of_element_located(confirm_cfg['locator']))
                self._safe_click(driver, confirm_btn, "侵权确认")
                self.log_signal.emit("已确认侵权", "blue")
            except:
                self.log_signal.emit("无侵权阻断", "green")

        except Exception as e:
            self.log_signal.emit(f"❌ 文案错误: {e}", "red")

    def _handle_submission(self, driver, wait):
        self.log_signal.emit("--> 模块 H: 功能提交", "blue")
        try:
            wrapper = self._find(driver, None, '结构_内容包装器')
            btn_container = wrapper.find_element(By.XPATH, "./div[2]")
            # save_btn = self._find(driver, wait, '按钮_保存', root_element=btn_container)
        except:
            pass