import json
import os
import copy

# 共享盘路径 (保持你原有的设置)
SHARED_ROOT_DIR = r'\\192.168.10.66\erp'
CONFIG_FILE = os.path.join(SHARED_ROOT_DIR, 'listing_element_config.json')

DEFAULT_CONFIG = {
    "LOGIN_URL": "https://saaserp-pos.yibainetwork.com/#/login_page",
    "ORG_CODE": "156",
    "ACCOUNTS": [],  # 账号列表由UI保存
    "TEXT_SOURCE": "AI智能文案",  # 默认文案策略

    # --- 新增：AI 模型配置 ---
    "AI_SETTINGS": {
        "ENABLED": True,
        # 以此名称来定位 Tab，对应 HTML 中的文本
        "TARGET_MODEL": "DeepSeek V3-A",
        "MODELS": {
            "ChatGPT": {"timeout": 30},
            "DeepSeek V3-A": {"timeout": 60},
            "DeepSeek V3-H": {"timeout": 90}
        }
    },

    "ELEMENT_CONFIG": [
        # ========================================================
        # 00. 核心层级 (Root -> Body -> Main)
        # ========================================================
        {
            "module": "00. 核心层级容器",
            "elements": [
                {"name": "容器_Root", "locator": "//body", "position": "页面根节点", "index": "1", "timeout": 20,
                 "rest": 1},
                {"name": "容器_Body", "locator": "body", "position": "Root内部", "index": "1", "timeout": 10,
                 "rest": 0},
                {"name": "容器_Main", "locator": ".//div[@class='main-content']", "position": "Body内部", "index": "1",
                 "timeout": 10, "rest": 0},
            ]
        },

        # ========================================================
        # 01. 登录模块
        # ========================================================
        {
            "module": "01. 登录与认证",
            "elements": [
                {"name": "账号输入框", "locator": "//input[@placeholder='请输入手机号/工号']", "position": "登录页",
                 "index": "1", "timeout": 5, "rest": 0},
                {"name": "密码输入框", "locator": "//input[@placeholder='请输入密码']", "position": "登录页",
                 "index": "1", "timeout": 5, "rest": 0},
                {"name": "登录按钮", "locator": "//span[contains(text(), '登录')]", "position": "登录页", "index": "1",
                 "timeout": 5, "rest": 1},
                {"name": "确认登录按钮", "locator": "//span[contains(text(), '确认登录')]", "position": "多组织弹窗",
                 "index": "1", "timeout": 5, "rest": 2},
                {"name": "组织输入框", "locator": "//input[@placeholder='请选择组织代码']", "position": "多组织弹窗",
                 "index": "1", "timeout": 5, "rest": 0},
                {"name": "组织列表项", "locator": "//div[contains(@class,'ivu-select-dropdown')]//li",
                 "position": "下拉菜单", "index": "1", "timeout": 3, "rest": 0}
            ]
        },

        # ========================================================
        # A. 导航模块 (更新 SKU 校验)
        # ========================================================
        {
            "module": "A. 菜单与搜索",
            "elements": [
                {"name": "导航_ERP菜单", "locator": "//div[contains(text(), 'ERP')]", "position": "顶部菜单",
                 "index": "1", "timeout": 10, "rest": 1},
                {"name": "导航_刊登管理", "locator": "//li[contains(text(), '刊登管理')]", "position": "二级菜单",
                 "index": "1", "timeout": 5, "rest": 1},
                {"name": "菜单_产品列表", "locator": "//li[contains(text(), '产品列表')]", "position": "左侧菜单",
                 "index": "1", "timeout": 5, "rest": 1},
                {"name": "搜索_SKU输入框", "locator": "//input[@placeholder='请输入SKU']", "position": "搜索栏",
                 "index": "1", "timeout": 5, "rest": 0},
                {"name": "搜索_查询按钮", "locator": "//button//span[contains(text(), '查询')]", "position": "搜索栏",
                 "index": "1", "timeout": 5, "rest": 2},

                # --- 新增：列表行校验元素 ---
                # 找到包含该 SKU 的 tr 行，确保按钮和 SKU 在同一行
                {"name": "列表_表格行", "locator": "//tr", "position": "列表", "index": "1", "timeout": 5, "rest": 0},
                {"name": "列表_SKU文本", "locator": "class=\"ui-link\"", "position": "行内", "index": "1", "timeout": 5,
                 "rest": 0},
                {"name": "列表_刊登按钮", "locator": "//span[contains(text(), '精细刊登')]", "position": "行内",
                 "index": "1", "timeout": 5, "rest": 1},

                {"name": "弹窗_下一步按钮", "locator": "//span[contains(text(), '下一步')]", "position": "初始配置弹窗",
                 "index": "1", "timeout": 10, "rest": 1},
            ]
        },

        # ========================================================
        # B1. 编辑器-基础与状态 (拆分后的核心配置)
        # ========================================================
        {
            "module": "B1. 编辑器-基础与状态",
            "elements": [
                # 店铺选择
                {"name": "容器_店铺区域", "locator": "//label[contains(text(),'店铺')]/..", "position": "顶部配置",
                 "index": "1", "timeout": 5, "rest": 0},
                {"name": "店铺_输入框", "locator": ".//input", "position": "店铺区域内", "index": "1", "timeout": 5,
                 "rest": 0},
                {"name": "店铺_下拉选项",
                 "locator": "//div[contains(@class, 'ivu-select-dropdown') and not(contains(@style, 'display: none'))]//li",
                 "position": "下拉菜单", "index": "1", "timeout": 3, "rest": 1},

                # 状态检查：翻译按钮可点击代表加载完成
                {"name": "翻译按钮_状态锚点", "locator": "//button[contains(., '翻译')]", "position": "检查是否可点",
                 "index": "1", "timeout": 60, "rest": 1},

                # 站点状态区域
                {"name": "状态_容器", "locator": "class=\"self_tabs_style\"", "position": "顶部", "index": "1",
                 "timeout": 5, "rest": 0},
                {"name": "状态_站点项", "locator": ".//span[contains(@class, 'item')]", "position": "容器内",
                 "index": "1", "timeout": 5, "rest": 0},
                # 解析：KAUS
                {"name": "状态_名称", "locator": "./button/span/span[1]", "position": "站点项内", "index": "1",
                 "timeout": 5, "rest": 0},
                # 解析：[已推送] 或 []
                {"name": "状态_标记", "locator": "./button/span/span[2]", "position": "站点项内", "index": "1",
                 "timeout": 5, "rest": 0},
            ]
        },

        # ========================================================
        # B2. 编辑器-功能(AI/图片)
        # ========================================================
        {
            "module": "B2. 编辑器-功能(AI/图片)",
            "elements": [
                # AI 相关
                {"name": "文案_AI按钮", "locator": "//span[contains(text(), 'AI智能文案')]", "position": "工具栏",
                 "index": "1", "timeout": 5, "rest": 2},
                # AI 选项 Tab 容器
                {"name": "AI弹窗_Tab容器", "locator": "class=\"ui-main-tab-box\"", "position": "AI弹窗", "index": "1",
                 "timeout": 5, "rest": 0},
                {"name": "AI弹窗_生成按钮",
                 "locator": "//div[contains(@class,'ivu-modal')]//span[contains(text(), '生成文案')]",
                 "position": "AI弹窗", "index": "1", "timeout": 5, "rest": 0},
                {"name": "AI弹窗_应用按钮",
                 "locator": "//div[contains(@class,'ivu-modal')]//span[contains(text(), '应用所有文案')]",
                 "position": "AI弹窗", "index": "1", "timeout": 5, "rest": 1},

                # 侵权检测
                {"name": "文案_侵权检测按钮", "locator": "//span[contains(text(), '一键检测侵权词')]",
                 "position": "底部/文案", "index": "1", "timeout": 5, "rest": 1},

                # 占位 - 图片选择
                {"name": "图片_选择按钮", "locator": "//span[contains(text(), '选择图片')]", "position": "工具栏",
                 "index": "1", "timeout": 5, "rest": 1},
            ]
        },

        # ========================================================
        # B3. 编辑器-提交与提示
        # ========================================================
        {
            "module": "B3. 编辑器-提交与提示",
            "elements": [
                # 底部按钮
                {"name": "按钮_保存当前", "locator": ".//button[contains(., '保存当前页')]", "position": "底部",
                 "index": "1", "timeout": 5, "rest": 1},
                {"name": "按钮_同步", "locator": ".//button[contains(., '同步至未推送站点')]", "position": "底部",
                 "index": "1", "timeout": 5, "rest": 1},
                {"name": "按钮_翻译", "locator": ".//button[contains(., '翻译')]", "position": "底部", "index": "1",
                 "timeout": 5, "rest": 1},
                {"name": "按钮_提交所有", "locator": "//button[contains(., '保存并提交所有站点')]",
                 "position": "底部全局", "index": "1", "timeout": 5, "rest": 2},

                # 退出相关
                {"name": "按钮_取消", "locator": "//span[contains(text(), '取消')]", "position": "底部固定栏",
                 "index": "1", "timeout": 5, "rest": 1},
                {"name": "退出确认_确定关闭", "locator": "//span[contains(text(), '确定关闭')]", "position": "全局弹窗",
                 "index": "1", "timeout": 3, "rest": 1},

                # 成功提示 (Message/Toast)
                {"name": "提示_通用成功", "locator": "//div[contains(text(), '操作成功')]", "position": "全局提示",
                 "index": "1", "timeout": 5, "rest": 0},
                {"name": "提示_同步成功", "locator": "//div[contains(text(), '同步至未推送站点成功')]",
                 "position": "全局提示", "index": "1", "timeout": 10, "rest": 0},
                # 翻译成功可能有不同文案，用 or 连接
                {"name": "提示_翻译成功",
                 "locator": "//div[contains(text(), '全部站点翻译成功') or contains(text(), '全部保存成功')]",
                 "position": "全局提示", "index": "1", "timeout": 15, "rest": 0},

                # 错误与必填
                {"name": "必填_错误容器", "locator": "//div[contains(@class, 'ivu-form-item-error')]",
                 "position": "全局表单", "index": "1", "timeout": 1, "rest": 0},

                # 弹窗关闭
                {"name": "全局_任意弹窗关闭", "locator": "class=\"ivu-modal-close\"", "position": "全局", "index": "1",
                 "timeout": 2, "rest": 0},
                {"name": "全局_任意确认按钮", "locator": "//span[contains(text(),'确定')]", "position": "全局",
                 "index": "1", "timeout": 2, "rest": 1},
                {"name": "侵权确认_确定按钮",
                 "locator": "//div[contains(@class,'ivu-modal')]//span[contains(text(),'确定')]",
                 "position": "全局弹窗", "index": "1", "timeout": 3, "rest": 1},
                {"name": "报错弹窗_关闭按钮", "locator": "//a[contains(@class, 'ivu-modal-close')]",
                 "position": "模态框右上角", "index": "1", "timeout": 2, "rest": 1},

                # Tab 遍历用 (失败扫尾)
                {"name": "容器_Tabs区域", "locator": "//div[contains(@class, 'ivu-tabs-nav-scroll')]",
                 "position": "Main顶部", "index": "1", "timeout": 5, "rest": 0},
            ]
        }
    ]
}


class ConfigManager:
    def __init__(self):
        self.config_file = CONFIG_FILE
        self.config_data = self.load_config()

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    local_data = json.load(f)
                    # 补充缺失的 AI 配置 (防止旧配置文件覆盖了新功能)
                    if "AI_SETTINGS" not in local_data:
                        local_data["AI_SETTINGS"] = DEFAULT_CONFIG["AI_SETTINGS"]
                    return local_data
            except Exception:
                return copy.deepcopy(DEFAULT_CONFIG)
        else:
            return copy.deepcopy(DEFAULT_CONFIG)

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
        except Exception:
            return False


config_manager = ConfigManager()