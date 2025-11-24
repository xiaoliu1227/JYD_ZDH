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
        # --- A ~ F 保持不变 ---
        {
            "module": "A. 登录与组织选择",
            "elements": [
                {"name": "账号输入框", "locator": "placeholder=\"请输入手机号或邮箱\"", "position": "当前元素",
                 "index": "1"},
                {"name": "密码输入框", "locator": "placeholder=\"请输入登录密码\"", "position": "当前元素",
                 "index": "1"},
                {"name": "登录按钮", "locator": "<span>登录", "position": "当前元素", "index": "1"},
                {"name": "组织选择弹窗", "locator": "class=\"el-dialog__body\"", "position": "当前元素", "index": "1"},
                {"name": "组织输入框", "locator": "placeholder=\"请选择\"", "position": "当前元素", "index": "1"},
                {"name": "组织列表项", "locator": "<span>156", "position": "当前元素", "index": "1"},
                {"name": "确认登录按钮", "locator": "<span>确认登录", "position": "当前元素", "index": "1"},
            ]
        },
        {
            "module": "B. 导航流程",
            "elements": [
                {"name": "导航_ERP菜单", "locator": "<span>ERP", "position": "当前元素", "index": "1"},
                {"name": "导航_刊登管理", "locator": "<span>刊登管理", "position": "当前元素", "index": "1"},
            ]
        },
        {
            "module": "C. 产品列表与刊登",
            "elements": [
                {"name": "菜单_刊登管理", "locator": "//li[contains(., '刊登管理')]", "position": "当前元素",
                 "index": "1"},
                {"name": "菜单_产品列表", "locator": "<span>产品列表", "position": "当前元素", "index": "1"},
                {"name": "搜索_SKU输入框", "locator": "placeholder=\"请输入SKU\"", "position": "当前元素",
                 "index": "1"},
                {"name": "搜索_查询按钮", "locator": "<span>查询", "position": "当前元素", "index": "1"},
                {"name": "列表_刊登按钮", "locator": "<span>刊登", "position": "当前元素", "index": "1"},
                {"name": "弹窗_下一步按钮", "locator": "<span>下一步", "position": "当前元素", "index": "1"},
            ]
        },
        {"module": "D. 刊登编辑-基础信息", "elements": []},
        {
            "module": "E. 刊登编辑-刊登配置",
            "elements": [
                {"name": "配置_品牌输入框",
                 "locator": ".//label[contains(text(), '品牌')]/following-sibling::div//input[@type='text']",
                 "position": "当前元素", "index": "1"},
                {"name": "配置_制造商输入框",
                 "locator": ".//label[contains(text(), '制造商')]/following-sibling::div//input[@type='text']",
                 "position": "当前元素", "index": "1"},
            ]
        },
        {
            "module": "F. 刊登编辑-产品信息",
            "elements": [
                {"name": "信息_选择图片按钮", "locator": "<span>选择图片", "position": "当前元素", "index": "1"},
            ]
        },
        # --- G. 刊登编辑-产品文案 ---
        {
            "module": "G. 刊登编辑-产品文案",
            "elements": [
                {"name": "文案_侵权检测按钮", "locator": "<span>一键检测侵权词/敏感词", "position": "当前元素",
                 "index": "1"},
                {"name": "文案_AI按钮", "locator": "<span>AI智能文案", "position": "当前元素", "index": "1"},

                {"name": "AI弹窗_生成按钮", "locator": "//button//span[normalize-space()='生成文案']",
                 "position": "当前元素", "index": "1"},
                {"name": "AI弹窗_应用按钮", "locator": "<span>应用所有文案", "position": "当前元素", "index": "1"},
                {"name": "AI弹窗_取消按钮", "locator": "<span>取消", "position": "当前元素", "index": "1"},
                {"name": "AI弹窗_标题输入框",
                 "locator": ".//label[normalize-space()='标题']/following-sibling::div//textarea",
                 "position": "当前元素", "index": "1"},

                {"name": "侵权弹窗_确定按钮", "locator": "<span>确定", "position": "当前元素", "index": "1"},
                {"name": "侵权弹窗_取消按钮", "locator": "<span>取消", "position": "当前元素", "index": "1"},
            ]
        },
        # --- H. 刊登编辑-功能按钮 ---
        {
            "module": "H. 刊登编辑-功能按钮",
            "elements": [
                # 改回简单匹配，逻辑层会处理可见性
                {"name": "按钮_取消", "locator": "<span>取消", "position": "当前元素", "index": "1"},

                {"name": "按钮_同步未推送", "locator": "<span>同步至未推送站点", "position": "当前元素", "index": "1"},
                {"name": "按钮_翻译", "locator": "<span>翻译", "position": "当前元素", "index": "1"},
                {"name": "按钮_保存当前", "locator": "<span>保存当前页", "position": "当前元素", "index": "1"},
                {"name": "按钮_保存所有", "locator": "<span>保存所有站点", "position": "当前元素", "index": "1"},
                {"name": "按钮_提交当前", "locator": "<span>保存并提交当前页", "position": "当前元素", "index": "1"},
                {"name": "按钮_提交所有", "locator": "<span>保存并提交所有站点", "position": "当前元素", "index": "1"},
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
                                code_ele["position"] = saved.get("position", code_ele["position"])
                                code_ele["index"] = saved.get("index", code_ele["index"])
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