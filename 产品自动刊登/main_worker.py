import traceback
import sys
import datetime
import time
from PyQt5.QtCore import QThread, pyqtSignal, QObject
from selenium import webdriver
from selenium.webdriver.edge.options import Options as EdgeOptions

# 导入拆分的模块
try:
    from browser_utils import BrowserBase
    from auth_actions import AuthManager
    from nav_actions import NavManager
    from editor_actions import EditorManager

    print("✅ 模块导入成功")
except ImportError as e:
    print(f"❌ 模块导入失败: {e}")


class ListingWorker(QThread):
    log_signal = pyqtSignal(str, str)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self, config_data, is_headless, sku_list, excel_path):
        super().__init__()
        self.config_data = config_data
        self.is_headless = is_headless
        self.sku_list = sku_list
        self.excel_path = excel_path
        self.is_running = True
        self.driver = None

    def _log_wrapper(self, msg, color="black"):
        try:
            print(f"[{color}] {msg}")
            self.log_signal.emit(str(msg), str(color))
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
        return webdriver.Edge(options=options)

    def run(self):
        print("▶️ 线程 run() 方法开始执行", flush=True)
        try:
            self._log_wrapper("🚀 任务启动...", "blue")
            self.driver = self._init_driver()

            auth_mgr = AuthManager(self.driver, self.config_data, self._log_wrapper)
            nav_mgr = NavManager(self.driver, self.config_data, self._log_wrapper)
            edit_mgr = EditorManager(self.driver, self.config_data, self._log_wrapper)

            # 1. 登录
            if not auth_mgr.perform_login(
                    self.config_data.get('USERNAME', ''),
                    self.config_data.get('PASSWORD', ''),
                    self.config_data.get('ORG_CODE', '156')
            ): raise Exception("登录失败")

            # 2. 进入系统
            if not nav_mgr.nav_to_listing_system():
                raise Exception("无法进入刊登系统")

            # 3. SKU 循环
            for sku in self.sku_list:
                if not self.is_running: break

                self._log_wrapper(f"📦 开始处理 SKU: {sku}", "blue")

                # === 单个 SKU 重试循环 (最多2次) ===
                max_retries = 2
                retry_count = 0
                success_flag = False

                while retry_count < max_retries:
                    if not self.is_running: break
                    try:
                        # [步骤A] 确保在列表页 (如果是非第一次重试，必须先刷新)
                        if retry_count > 0:
                            self._log_wrapper("🔄 正在刷新页面清理环境...", "gray")
                            self.driver.refresh()
                            time.sleep(3)  # 等待刷新白屏结束

                        nav_mgr.enter_product_page()

                        # [步骤B] 搜索 SKU
                        if not nav_mgr.search_and_edit_sku(sku):
                            self._update_excel(sku, "搜索失败")
                            break  # 搜都搜不到，就不重试了，直接下一个SKU

                        # [步骤C] 编辑器流程 (这里包含了等待加载、选店铺等)
                        # 如果这里超时，editor_actions 会抛出异常
                        edit_mgr.setup_listing_env(self.config_data.get('ACCOUNT_NAME', ''))

                        # [步骤D] 多站点操作
                        edit_mgr.process_all_sites()

                        self._update_excel(sku, "成功")
                        success_flag = True
                        break  # 成功了，跳出重试循环

                    except Exception as e:
                        retry_count += 1
                        self._log_wrapper(f"⚠️ 出错 (第 {retry_count} 次重试): {str(e)}", "orange")

                        # 如果还没达到最大重试次数，不要 break，让 while 继续
                        if retry_count >= max_retries:
                            self._log_wrapper(f"❌ SKU {sku} 最终失败", "red")
                            self._update_excel(sku, f"失败: {str(e)}")

                # 退出内层 while 后，继续外层 for 处理下一个 SKU

            self._log_wrapper("🏁 所有任务完成", "green")
            self.finished_signal.emit()

        except Exception as e:
            traceback.print_exc()
            self.error_signal.emit(str(e))
        finally:
            if self.driver: self.driver.quit()

    def _update_excel(self, sku, status):
        print(f"📝 [Excel模拟写入] SKU: {sku} -> 状态: {status}")

    def stop(self):
        self.is_running = False