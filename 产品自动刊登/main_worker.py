import sys
import os
import time
import pandas as pd
from PyQt5.QtCore import QThread, pyqtSignal
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options

# 引入新架构模块
from config_manager import config_manager
from auth_actions import AuthManager
from nav_actions import NavManager
from actions.editor_manager import EditorManager


class WorkerThread(QThread):
    log_signal = pyqtSignal(str, str)  # msg, color
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal()

    def __init__(self, excel_path, account_name, is_headless=False):
        super().__init__()
        self.excel_path = excel_path
        self.account_name = account_name
        self.is_headless = is_headless
        self.driver = None
        self.is_running = True

    def log(self, msg, color="black"):
        self.log_signal.emit(msg, color)

    def init_driver(self):
        self.log("🚀 正在启动浏览器...", "blue")
        edge_options = Options()
        if self.is_headless:
            edge_options.add_argument("--headless")
            edge_options.add_argument("--disable-gpu")

        edge_options.add_argument("--start-maximized")
        edge_options.add_argument("--ignore-certificate-errors")
        edge_options.add_argument("--ignore-ssl-errors")
        # 防止监测
        edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        edge_options.add_experimental_option('useAutomationExtension', False)

        service = Service('msedgedriver.exe')  # 确保驱动在目录下
        driver = webdriver.Edge(service=service, options=edge_options)
        driver.implicitly_wait(3)
        return driver

    def run(self):
        try:
            # 1. 读取 Excel 数据
            df = pd.read_excel(self.excel_path)
            # 假设 Excel 有 'SKU' 列，如果没有则取第一列
            sku_col = 'SKU' if 'SKU' in df.columns else df.columns[0]
            sku_list = df[sku_col].dropna().astype(str).tolist()

            self.log(f"📂 读取到 {len(sku_list)} 个 SKU 待处理", "blue")

            # 2. 初始化驱动
            self.driver = self.init_driver()

            # 3. 初始化各模块
            auth = AuthManager(self.driver, self.log_signal)
            nav = NavManager(self.driver, self.log_signal)
            editor = EditorManager(self.driver, self.log_signal)

            # 4. 执行登录
            # 假设 config 中有账户密码配置，这里简化为从 config 读取或由 UI 传递
            # 这里为了演示，从 config_manager 读取默认账号或写死，实际应从 UI 传入
            # 暂时使用 config 中的默认值
            acc_cfg = config_manager.config_data.get("ACCOUNTS", [])
            # 简单逻辑：如果有账号配置就用第一个，否则需在 UI 完善传参
            username = acc_cfg[0]['username'] if acc_cfg else "你的账号"
            password = acc_cfg[0]['password'] if acc_cfg else "你的密码"
            org_code = config_manager.config_data.get("ORG_CODE", "156")

            if not auth.perform_login(username, password, org_code):
                self.log("❌ 登录失败，任务终止", "red")
                return

            # 5. 导航至工作台
            if not nav.nav_to_listing_system():
                self.log("❌ 导航失败，任务终止", "red")
                return

            # 6. 循环处理 SKU
            total = len(sku_list)
            for index, sku in enumerate(sku_list):
                if not self.is_running: break

                self.log(f"\n========== 正在处理第 {index + 1}/{total} 个 SKU: {sku} ==========", "purple")
                self.progress_signal.emit(int((index / total) * 100))

                max_retries = 2
                for retry in range(max_retries):
                    try:
                        # A. 搜索并进入编辑器
                        # 注意：如果上一个 SKU 失败导致还在编辑器内，需要先检测
                        if "product_list" not in self.driver.current_url:
                            self.log("⚠️ 页面位置异常，尝试强制返回列表...", "orange")
                            nav.enter_product_list_page()

                        found = nav.search_and_edit_sku(sku)
                        if not found:
                            self.log(f"⚠️ 无法找到 SKU: {sku}，跳过", "orange")
                            break  # 跳出重试，处理下一个 SKU

                        # B. 执行全流程
                        # 获取店铺名，这里假设全用同一个，或者 Excel 里有 'Shop' 列
                        # shop_name = df.iloc[index]['Shop']
                        shop_name = "KAPA-US"  # 示例默认值，实际应读取 Excel

                        editor.process_full_cycle(shop_name)

                        self.log(f"✅ SKU {sku} 处理完毕", "green")
                        break  # 成功，退出重试循环

                    except Exception as e:
                        err_msg = str(e)
                        self.log(f"❌ SKU {sku} 处理异常 (尝试 {retry + 1}): {err_msg}", "red")

                        # 特殊处理：如果是加载超时 (Editor_Loading_Timeout)
                        if "Editor_Loading_Timeout" in err_msg or "element" in err_msg:
                            self.log("🔄 触发浏览器刷新机制...", "blue")
                            try:
                                self.driver.refresh()
                                time.sleep(5)
                                nav.enter_product_list_page()  # 刷新后要回到列表
                            except:
                                pass

                        # 如果是最后一次尝试，记录失败
                        if retry == max_retries - 1:
                            self.log(f"❌ SKU {sku} 最终失败，跳过", "red")

                # 稍作休息
                time.sleep(2)

            self.progress_signal.emit(100)
            self.log("\n🏁 所有任务已完成！", "green")

        except Exception as e:
            self.log(f"❌ 线程发生致命错误: {e}", "red")
        finally:
            if self.driver:
                self.log("👋 关闭浏览器...", "gray")
                self.driver.quit()
            self.finished_signal.emit()

    def stop(self):
        self.is_running = False