import time
import json
import traceback
import sys
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By


class SilentFullCycleSpy:
    def __init__(self):
        print("🕵️ 初始化：静默版全流程监控工具 (v2)...")
        self.driver = self._init_driver()
        self.all_logs = []
        self.start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.current_target_handle = None

    def _init_driver(self):
        options = EdgeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--ignore-certificate-errors")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        return webdriver.Edge(options=options)

    def smart_switch_context(self):
        """
        智能切换上下文：
        不轮询，而是判断哪个窗口最像是用户正在操作的窗口。
        策略：优先锁定 URL 包含关键业务词汇的窗口，或者是最新打开的窗口。
        """
        try:
            handles = self.driver.window_handles
            if not handles: return

            # 策略 A: 如果只有一个窗口，直接锁定
            if len(handles) == 1:
                if self.current_target_handle != handles[0]:
                    self.driver.switch_to.window(handles[0])
                    self.current_target_handle = handles[0]
                    # print(f"🔒 锁定唯一窗口: {self.driver.title[:10]}")
                return

            # 策略 B: 多窗口情况，寻找最优目标
            # 优先找包含 'editor', 'publish', 'product_list' 的页面
            best_handle = None

            # 先检查当前锁定的窗口是否依然有效且符合条件（避免频繁切换）
            if self.current_target_handle in handles:
                try:
                    self.driver.switch_to.window(self.current_target_handle)
                    curr_url = self.driver.current_url
                    # 如果当前已经在编辑页或列表页，就别动了，防止干扰用户
                    if 'editor' in curr_url or 'publish' in curr_url or 'product_list' in curr_url:
                        return
                except:
                    pass  # 句柄可能失效了，重新找

            # 如果需要重新找目标：优先找最新打开的窗口（通常是列表点出来的编辑页）
            # handles 列表通常按打开顺序排列，最后一个是最新的
            latest_handle = handles[-1]

            if self.current_target_handle != latest_handle:
                self.driver.switch_to.window(latest_handle)
                self.current_target_handle = latest_handle
                print(f"👉 [自动跟随] 切换监控至新窗口: {self.driver.title[:15]}...")

        except Exception as e:
            # 忽略切换过程中的瞬时错误
            pass

    def inject_js(self):
        """向当前锁定的窗口注入探针"""
        js_code = """
        (function() {
            if (window._spy_active) return false;
            window._spy_active = true;
            window._spy_logs = [];

            // 视觉标记：在右下角放一个小绿点，不遮挡操作
            let badge = document.createElement('div');
            badge.innerText = "REC";
            badge.style = 'position:fixed; bottom:5px; right:5px; padding:2px 5px; background:red; color:white; font-size:10px; z-index:999999; border-radius:3px; pointer-events:none; opacity:0.7;';
            document.body.appendChild(badge);

            console.log("🚀 [Spy] 探针启动");

            function addLog(type, summary, detail) {
                if(!summary && !detail) return;
                window._spy_logs.push({
                    t: new Date().toLocaleTimeString(),
                    type: type,
                    summary: summary.trim(),
                    detail: detail.trim(),
                    url: window.location.href
                });
            }

            // 1. 点击监听
            window.addEventListener('click', function(e) {
                let t = e.target;
                let text = t.innerText || t.value || '';
                if (!text && t.parentElement) text = t.parentElement.innerText || '';
                text = text.replace(/[\\n\\r]/g, ' ').substring(0, 30);

                let cls = t.className || '';
                if(typeof cls !== 'string') cls = 'Object';

                addLog('🖱️ [点击]', text, `Tag:<${t.tagName}> Class:${cls}`);
            }, true);

            // 2. DOM 监听
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((m) => {
                    m.addedNodes.forEach(node => {
                        if (node.nodeType !== 1) return;

                        let cls = (node.className || '').toString();
                        let txt = (node.innerText || '').replace(/[\\n\\r]/g, ' ').substring(0, 100);

                        // 关键词库
                        const keywords = [
                            'modal', 'mask', 'loading', 'message', 'notice', 'dialog', 
                            'tip', 'error', 'warn', 'alert', 'mess-box', 'ivu-', 'el-', 'toast'
                        ];

                        let isTarget = keywords.some(k => cls.includes(k));
                        if (!isTarget && txt.length > 1 && txt.length < 50) isTarget = true;

                        if (isTarget) {
                            addLog('🔥 [弹窗/DOM]', txt || '(无文本)', `Class: ${cls}`);

                            // 延时抓取补充内容
                            if (cls.includes('modal') || cls.includes('mess')) {
                                setTimeout(() => {
                                    try {
                                        let newTxt = node.innerText.replace(/[\\n\\r]/g, ' ');
                                        if(newTxt && newTxt !== txt) {
                                            addLog('    ↳ [补充内容]', newTxt.substring(0, 80), '延时捕获');
                                        }
                                    } catch(e){}
                                }, 300);
                            }
                        }
                    });

                    // 状态变化
                    if (m.type === 'attributes' && m.attributeName === 'style') {
                        let node = m.target;
                        let cls = (node.className || '').toString();
                        if (cls.includes('mask') || cls.includes('loading') || cls.includes('modal')) {
                            let isVis = node.style.display !== 'none' && node.style.visibility !== 'hidden';
                            addLog('🔄 [状态变更]', `可见性: ${isVis}`, `Class: ${cls}`);
                        }
                    }
                });
            });

            observer.observe(document.body, {childList: true, subtree: true, attributes: true, attributeFilter: ['style', 'class']});
            return true;
        })();
        """
        try:
            return self.driver.execute_script(js_code)
        except:
            return False

    def collect_logs(self):
        """只从当前锁定的窗口收集日志"""
        try:
            # 1. 尝试注入 (如果页面刷新了)
            self.inject_js()

            # 2. 拉取日志
            logs = self.driver.execute_script(
                "if(window._spy_logs) { var t = window._spy_logs; window._spy_logs = []; return t; } else { return []; }")
            if logs:
                title = self.driver.title[:15]
                for l in logs: l['context'] = f"{title}"
                self.all_logs.extend(logs)
                # 实时打印
                for l in logs:
                    print(f"[{l['t']}] {l['type']}: {l['summary']}")
        except:
            pass

    def save_to_file(self):
        filename = "log.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"=== ERP 流程诊断日志 (v2) ===\n")
            f.write(f"Record Time: {self.start_time} ~ {datetime.now().strftime('%H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")

            for log in self.all_logs:
                line = f"[{log['t']}] {log['type']}: {log['summary']}\n"
                if log['detail']:
                    line += f"      Info: {log['detail']}\n"
                f.write(line)

        print(f"\n✅ 日志已保存: {filename}")

    def run(self):
        self.driver.get("https://saaserp-pos.yibainetwork.com")

        print("\n" + "=" * 60)
        print("🤫 静默监控模式已启动 (不会乱切窗口)")
        print("1. 请像平常一样操作网页。")
        print("2. 脚本会自动锁定你最新打开的窗口进行记录。")
        print("3. 操作完成后，按 [Ctrl+C] 生成日志。")
        print("   (右下角会出现红色 REC 标记，代表监控生效中)")
        print("=" * 60 + "\n")

        try:
            while True:
                # 1. 智能判断当前应该监控哪个窗口
                self.smart_switch_context()

                # 2. 收集日志
                self.collect_logs()

                time.sleep(1)  # 频率降低，减少干扰

        except KeyboardInterrupt:
            print("\n🛑 停止记录...")
        except Exception:
            traceback.print_exc()
        finally:
            self.save_to_file()
            self.driver.quit()


if __name__ == "__main__":
    spy = SilentFullCycleSpy()
    spy.run()