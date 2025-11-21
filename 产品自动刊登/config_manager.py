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
        # --- 0. 页面结构基座 ---
        {
            "module": "0. 页面结构基座",
            "elements": [
                {
                    "name": "结构_内容包装器",
                    "locator": "//body/textarea/following-sibling::div[1]/div[2]/div/div/div[2]/div/div[3]",
                    "position": "当前元素", "index": "1"
                },
                {
                    "name": "结构_激活站点容器",
                    "locator": "./div[1]/div[not(contains(@style, 'display: none'))]",
                    "position": "当前元素", "index": "1"
                },
                # 【新增】AI 弹窗的候选列表 (会匹配到 N 个)
                {
                    "name": "结构_AI弹窗列表",
                    "locator": "//body/div[@data-transfer='true' and @class='v-transfer-dom']",
                    "position": "当前元素", "index": "1"
                }
            ]
        },

        # --- A, B, C, D 模块保持不变 (省略以节省篇幅) ---
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
                {"name": "弹窗_平台隐藏值",
                 "locator": "//label[contains(text(),'平台')]/following-sibling::div//input[@type='hidden']",
                 "position": "当前元素", "index": "1"},
                {"name": "弹窗_下一步按钮", "locator": "<span>下一步", "position": "当前元素", "index": "1"},
            ]
        },
        {
            "module": "D. 刊登编辑-基础信息",
            "elements": [
                {"name": "编辑_店铺输入框", "locator": "placeholder=\"请选择\"", "position": "当前元素", "index": "3"},
                {"name": "编辑_店铺列表容器", "locator": "class=\"ivu-select-dropdown-list\"", "position": "当前元素",
                 "index": "6"},
                {"name": "编辑_站点容器", "locator": "class=\"self_tabs_style\"", "position": "当前元素", "index": "2"},
            ]
        },

        # --- E, F 模块 (相对定位) ---
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
                {"name": "信息_锚点", "locator": ".//h5[contains(text(), '产品信息')]", "position": "当前元素",
                 "index": "1"},
            ]
        },

        # --- 【重点修改】模块 G：产品文案 ---
        {
            "module": "G. 刊登编辑-产品文案",
            "elements": [
                # 1. 触发按钮 (在主页面 active_container 里) -> 保持 .//
                {"name": "文案_打开AI按钮", "locator": ".//button//span[contains(text(), 'AI智能文案')]",
                 "position": "当前元素", "index": "1"},

                # 2. 弹窗内部元素 (在 ai_popup 容器里) -> 改为 .//
                # 生成按钮
                {"name": "AI_生成按钮", "locator": ".//button//span[contains(text(), '生成文案')]",
                 "position": "当前元素", "index": "1"},
                # 标题输出框 (层级较深，使用相对定位查找)
                {"name": "AI_标题输出框",
                 "locator": ".//label[contains(text(),'标题')]/following-sibling::div//textarea",
                 "position": "当前元素", "index": "1"},
                # 应用按钮
                {"name": "AI_应用所有按钮", "locator": ".//button//span[contains(text(), '应用所有文案')]",
                 "position": "当前元素", "index": "1"},

                # 3. 侵权检测 (在主页面 active_container 里) -> 保持 .//
                {"name": "文案_检测侵权按钮", "locator": ".//button//span[contains(text(), '一键检测侵权词')]",
                 "position": "当前元素", "index": "1"},

                # 4. 侵权确认弹窗 (全局弹窗) -> 保持 //
                {"name": "侵权_弹窗确认按钮",
                 "locator": "//div[contains(@class,'ivu-modal-footer')]//button//span[contains(text(),'确定')]",
                 "position": "当前元素", "index": "1"},
            ]
        },

        {
            "module": "H. 刊登编辑-功能按钮",
            "elements": [
                {"name": "按钮_保存", "locator": ".//span[contains(text(), '保存当前页')]", "position": "当前元素",
                 "index": "1"},
                {"name": "按钮_发布", "locator": ".//span[contains(text(), '保存并推入刊登')]", "position": "当前元素",
                 "index": "1"},
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
                if "ACCOUNTS" in file_data: final_config["ACCOUNTS"] = file_data["ACCOUNTS"]
                if "LOGIN_URL" in file_data: final_config["LOGIN_URL"] = file_data["LOGIN_URL"]
                if "ORG_CODE" in file_data: final_config["ORG_CODE"] = file_data["ORG_CODE"]

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
            except:
                self.save_config(final_config)
        else:
            self.save_config(final_config)
        self.config_data = final_config
        return self.config_data

    def save_config(self, data):
        self.config_data = data
        directory = os.path.dirname(self.config_file)
        if not os.path.exists(directory): return False
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, ensure_ascii=False, indent=4)
            return True
        except:
            return False


config_manager = ConfigManager()