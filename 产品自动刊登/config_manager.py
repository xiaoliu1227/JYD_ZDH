import json
import os
import copy

SHARED_ROOT_DIR = r'\\192.168.10.66\erp'
CONFIG_FILE = os.path.join(SHARED_ROOT_DIR, 'listing_element_config.json')

DEFAULT_CONFIG = {
    "LOGIN_URL": "https://saaserp-pos.yibainetwork.com/#/login_page",
    "ORG_CODE": "156",
    "ACCOUNTS": [],
    "ELEMENT_CONFIG": [
        # ========================================================
        # 0. 核心层级 (Root -> Body -> Main)
        # ========================================================
        {
            "module": "00. 核心层级容器",
            "elements": [
                # [Python代码中已使用更强的动态定位逻辑覆盖此项，此处保留做备用]
                {"name": "容器_Root",
                 "locator": "//body/textarea/following-sibling::div[@data-v-3e50dd5e and @data-v-5e14dbfd and @data-transfer='true']",
                 "position": "页面根节点", "index": "1", "timeout": 20, "rest": 1},
                {"name": "容器_Body", "locator": ".//div[contains(@class, 'ivu-modal-body')]", "position": "Root内部",
                 "index": "1", "timeout": 10, "rest": 0},
                {"name": "容器_Main", "locator": ".//div[contains(@class, 'd-main')]", "position": "Body内部",
                 "index": "1", "timeout": 10, "rest": 0},
            ]
        },

        # ========================================================
        # 1. 模块布局 (已更新：预留4大业务模块)
        # ========================================================
        {
            "module": "01. 模块布局定位",
            "elements": [
                {"name": "容器_店铺区域", "locator": ".//div[@class='s-h-h clearFix']", "position": "Body内部",
                 "index": "1", "timeout": 10, "rest": 0},

                {"name": "容器_Tabs区域", "locator": ".//div[contains(@class, 'mult-header-h')]",
                 "position": "Body内部", "index": "1", "timeout": 10, "rest": 0},

                # 基于 Main
                {"name": "容器_布局Wrapper", "locator": "./div[1]", "position": "Main第1个子DIV", "index": "1",
                 "timeout": 5, "rest": 0},
                {"name": "容器_按钮模块", "locator": "./div[2]", "position": "Main第2个子DIV", "index": "1",
                 "timeout": 5, "rest": 0},

                # 基于 Active Site (当前激活的站点容器)
                {"name": "容器_站点模块Wrapper", "locator": "./div[1]", "position": "站点内第1个DIV", "index": "1",
                 "timeout": 5, "rest": 0},

                # [新增/修改] 核心业务模块 (相对于 容器_站点模块Wrapper)
                # Div 1: 刊登配置
                {"name": "容器_刊登配置", "locator": "./div[1]", "position": "模块Wrapper第1个子DIV", "index": "1",
                 "timeout": 5, "rest": 0},
                # Div 2: 产品信息
                {"name": "容器_产品信息", "locator": "./div[2]", "position": "模块Wrapper第2个子DIV", "index": "1",
                 "timeout": 5, "rest": 0},
                # Div 3: 价格模块
                {"name": "容器_价格信息", "locator": "./div[3]", "position": "模块Wrapper第3个子DIV", "index": "1",
                 "timeout": 5, "rest": 0},
                # Div 4: 文案模块 (原配置)
                {"name": "容器_文案模块", "locator": "./div[4]", "position": "模块Wrapper第4个子DIV", "index": "1",
                 "timeout": 5, "rest": 0},
            ]
        },

        # ========================================================
        # 业务模块
        # ========================================================
        {
            "module": "A. 登录与导航",
            "elements": [
                {"name": "账号输入框", "locator": "placeholder=\"请输入手机号或邮箱\"", "position": "当前元素",
                 "index": "1", "timeout": 10, "rest": 0},
                {"name": "密码输入框", "locator": "placeholder=\"请输入登录密码\"", "position": "当前元素",
                 "index": "1", "timeout": 10, "rest": 0},
                {"name": "登录按钮", "locator": "<span>登录", "position": "当前元素", "index": "1", "timeout": 10,
                 "rest": 2},
                {"name": "确认登录按钮", "locator": "<span>确认登录", "position": "当前元素", "index": "1",
                 "timeout": 10, "rest": 2},
                {"name": "组织选择弹窗", "locator": "class=\"el-dialog__body\"", "position": "当前元素", "index": "1",
                 "timeout": 5, "rest": 1},
                {"name": "组织输入框", "locator": "placeholder=\"请选择\"", "position": "当前元素", "index": "1",
                 "timeout": 5, "rest": 1},
                {"name": "组织列表项", "locator": "<span>156", "position": "当前元素", "index": "1", "timeout": 5,
                 "rest": 1},
                {"name": "导航_ERP菜单", "locator": "<span>ERP", "position": "当前元素", "index": "1", "timeout": 10,
                 "rest": 1},
                {"name": "导航_刊登管理", "locator": "<span>刊登管理", "position": "当前元素", "index": "1",
                 "timeout": 10, "rest": 2},
            ]
        },
        {
            "module": "B. 列表与店铺",
            "elements": [
                {"name": "菜单_刊登管理", "locator": "//li[contains(., '刊登管理')]", "position": "当前元素",
                 "index": "1", "timeout": 10, "rest": 1},
                {"name": "菜单_产品列表", "locator": "<span>产品列表", "position": "当前元素", "index": "1",
                 "timeout": 10, "rest": 1},
                {"name": "搜索_SKU输入框", "locator": "placeholder=\"请输入SKU\"", "position": "当前元素", "index": "1",
                 "timeout": 10, "rest": 1},
                {"name": "搜索_查询按钮", "locator": "<span>查询", "position": "当前元素", "index": "1", "timeout": 10,
                 "rest": 3},
                {"name": "列表_刊登按钮", "locator": "<span>刊登", "position": "当前元素", "index": "1", "timeout": 10,
                 "rest": 1},
                {"name": "弹窗_下一步按钮", "locator": "<span>下一步", "position": "当前元素", "index": "1",
                 "timeout": 5, "rest": 2},

                # 基于 容器_店铺区域
                {"name": "店铺_输入框", "locator": ".//input", "position": "店铺容器内", "index": "1", "timeout": 10,
                 "rest": 1},
                # 全局查找下拉
                {"name": "店铺_下拉列表项", "locator": "//div[contains(@class,'ivu-select-dropdown')]//li",
                 "position": "全局下拉", "index": "1", "timeout": 5, "rest": 1},
            ]
        },

        # ========================================================
        # 弹窗模块
        # ========================================================
        {
            "module": "X. AI弹窗模块",
            "elements": [
                {"name": "AI弹窗_Root", "locator": "//body/div[contains(@style, 'top: 5vh') or @top='5vh']",
                 "position": "Body子节点", "index": "1", "timeout": 10, "rest": 0},
                {"name": "文案_AI按钮", "locator": "<span>AI智能文案", "position": "文案模块内", "index": "1",
                 "timeout": 120, "rest": 2},
                # [注意] 改为 .// 开头，配合强制点击逻辑
                {"name": "AI弹窗_生成按钮", "locator": ".//button//span[normalize-space()='生成文案']",
                 "position": "弹窗内", "index": "1", "timeout": 10, "rest": 2},
                {"name": "AI弹窗_应用按钮", "locator": ".//span[normalize-space()='应用所有文案']",
                 "position": "弹窗内", "index": "1",
                 "timeout": 10, "rest": 1},
                {"name": "AI弹窗_取消按钮", "locator": "<span>取消", "position": "弹窗内", "index": "1", "timeout": 5,
                 "rest": 1},
                {"name": "AI弹窗_标题输入框",
                 "locator": ".//label[normalize-space()='标题']/following-sibling::div//textarea", "position": "弹窗内",
                 "index": "1", "timeout": 5, "rest": 0},
            ]
        },
        {
            "module": "Y. 侵权弹窗模块",
            "elements": [
                {"name": "侵权弹窗_Root_Rel", "locator": "following-sibling::div[1]", "position": "AI弹窗兄弟",
                 "index": "1", "timeout": 5, "rest": 0},
                {"name": "文案_侵权检测按钮", "locator": "<span>一键检测侵权词/敏感词", "position": "文案模块内",
                 "index": "1", "timeout": 10, "rest": 2},
                {"name": "侵权弹窗_确定按钮", "locator": "<span>确定", "position": "弹窗内", "index": "1", "timeout": 5,
                 "rest": 1},
                {"name": "侵权弹窗_取消按钮", "locator": "<span>取消", "position": "弹窗内", "index": "1", "timeout": 5,
                 "rest": 1},
            ]
        },
        # ========================================================
        # [新增] 提交反馈与错误处理
        # ========================================================
        {
            "module": "Z. 提交反馈弹窗",
            "elements": [
                {"name": "退出确认弹窗_确定按钮",
                 "locator": "//div[@class='ivu-modal-confirm-footer']//span[contains(text(),'确定')]",
                 "position": "全局", "index": "1", "timeout": 5, "rest": 1},

                # [核心新增] 用于捕获包含 "提示" 头部的错误弹窗
                {"name": "提示弹窗_Root",
                 "locator": "//div[contains(@class,'ivu-modal-wrap') and not(contains(@style,'display: none')) and .//div[@class='ivu-modal-header-inner' and text()='提示']]",
                 "position": "全局", "index": "1", "timeout": 5, "rest": 0},

                # 获取错误信息 (获取 mess-box 下所有的 span 文本)
                {"name": "提示弹窗_错误信息",
                 "locator": ".//div[contains(@class, 'mess-box')]//span",
                 "position": "提示弹窗内", "index": "1", "timeout": 2, "rest": 0},

                # 关闭按钮 (优先点这个)
                {"name": "提示弹窗_关闭图标",
                 "locator": ".//a[@class='ivu-modal-close']",
                 "position": "提示弹窗内", "index": "1", "timeout": 2, "rest": 1},

                # 兜底关闭点击目标 (页面上的 "1.选择平台" 文字，点击它通常能触发遮罩层关闭)
                {"name": "页面_空白点击目标",
                 "locator": "//span[contains(text(), '1.选择平台')]",
                 "position": "全局背景", "index": "1", "timeout": 5, "rest": 1},
            ]
        },

        # ========================================================
        # 底部按钮
        # ========================================================
        {
            "module": "H. 底部功能按钮",
            "elements": [
                {"name": "按钮_取消", "locator": "<span>取消", "position": "按钮模块内", "index": "1", "timeout": 10,
                 "rest": 1},
                {"name": "按钮_同步", "locator": "<span>同步至未推送站点", "position": "按钮模块内", "index": "1",
                 "timeout": 10, "rest": 1},
                {"name": "按钮_翻译", "locator": "<span>翻译", "position": "按钮模块内", "index": "1", "timeout": 10,
                 "rest": 1},
                {"name": "按钮_保存当前", "locator": "<span>保存当前页", "position": "按钮模块内", "index": "1",
                 "timeout": 10, "rest": 1},
                {"name": "按钮_保存所有", "locator": "<span>保存所有站点", "position": "按钮模块内", "index": "1",
                 "timeout": 10, "rest": 1},
                {"name": "按钮_提交当前", "locator": "<span>保存并提交当前页", "position": "按钮模块内", "index": "1",
                 "timeout": 10, "rest": 1},
                {"name": "按钮_提交所有", "locator": "<span>保存并提交所有站点", "position": "按钮模块内", "index": "1",
                 "timeout": 30, "rest": 1},
            ]
        }
    ]
}


class ConfigManager:
    def __init__(self, config_file=CONFIG_FILE, default_config=DEFAULT_CONFIG):
        self.config_file = config_file
        self.default_config = default_config
        self.config_data = {}

    def load_config(self):
        final_config = copy.deepcopy(self.default_config)
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)
                for key in ["ACCOUNTS", "LOGIN_URL", "ORG_CODE"]:
                    if key in file_data: final_config[key] = file_data[key]

                file_map = {}
                for mod in file_data.get("ELEMENT_CONFIG", []):
                    mod_name = mod.get("module")
                    if mod_name: file_map[mod_name] = {e["name"]: e for e in mod.get("elements", [])}

                for code_mod in final_config["ELEMENT_CONFIG"]:
                    mod_name = code_mod["module"]
                    if mod_name in file_map:
                        for code_ele in code_mod["elements"]:
                            ele_name = code_ele["name"]
                            if ele_name in file_map[mod_name]:
                                saved = file_map[mod_name][ele_name]
                                code_ele["locator"] = saved.get("locator", code_ele["locator"])
                                code_ele["index"] = saved.get("index", code_ele["index"])
                                code_ele["timeout"] = saved.get("timeout", code_ele.get("timeout", 10))
                                code_ele["rest"] = saved.get("rest", code_ele.get("rest", 2))
                self.save_config(final_config)
            except Exception as e:
                self.save_config(final_config)
        else:
            self.save_config(final_config)
        self.config_data = final_config
        return self.config_data

    def save_config(self, data):
        self.config_data = data
        directory = os.path.dirname(self.config_file)
        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
            except OSError:
                return False
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            return False


config_manager = ConfigManager()