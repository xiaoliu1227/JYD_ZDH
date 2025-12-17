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

    "ELEMENT_CONFIG": [
        # ========================================================
        # 00. 核心层级 (Root -> Body -> Main)
        # ========================================================
        {
            "module": "00. 核心层级容器",
            "elements": [
                # 页面最外层容器，用于刷新 DOM 树
                {"name": "容器_Root", "locator": "//body", "position": "页面根节点", "index": "1", "timeout": 20,
                 "rest": 1},
                # 模态框通常在这里
                {"name": "容器_Body", "locator": "body", "position": "Root内部", "index": "1", "timeout": 10,
                 "rest": 0},
                # 业务主区域
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
        # A. 导航模块
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
                {"name": "列表_刊登按钮", "locator": "//span[contains(text(), '精细刊登')]", "position": "列表操作区",
                 "index": "1", "timeout": 5, "rest": 1},
                # 可能出现的初始弹窗
                {"name": "弹窗_下一步按钮", "locator": "//span[contains(text(), '下一步')]", "position": "初始配置弹窗",
                 "index": "1", "timeout": 3, "rest": 1},
            ]
        },

        # ========================================================
        # B. 编辑器 - 核心按钮 (基于日志 10:35 - 10:37)
        # ========================================================
        {
            "module": "B. 编辑器功能按钮",
            "elements": [
                # 店铺选择
                {"name": "容器_店铺区域", "locator": "//label[contains(text(),'店铺')]/..", "position": "顶部配置",
                 "index": "1", "timeout": 5, "rest": 0},
                {"name": "店铺_输入框", "locator": ".//input", "position": "店铺区域内", "index": "1", "timeout": 5,
                 "rest": 0},
                {"name": "店铺_下拉选项", "locator": "//div[contains(@class, 'ivu-select-dropdown') and not(contains(@style, 'display: none'))]//li", "position": "下拉菜单", "index": "1", "timeout": 3, "rest": 1},
                # AI 与文案
                {"name": "文案_AI按钮", "locator": "//span[contains(text(), 'AI智能文案')]", "position": "文案模块",
                 "index": "1", "timeout": 5, "rest": 2},
                {"name": "AI弹窗_生成按钮",
                 "locator": "//div[contains(@class,'ivu-modal')]//span[contains(text(), '生成文案')]",
                 "position": "AI弹窗", "index": "1", "timeout": 5, "rest": 0},
                {"name": "AI弹窗_应用按钮",
                 "locator": "//div[contains(@class,'ivu-modal')]//span[contains(text(), '应用所有文案')]",
                 "position": "AI弹窗", "index": "1", "timeout": 5, "rest": 1},

                # 侵权检测
                {"name": "文案_侵权检测按钮", "locator": "//span[contains(text(), '一键检测侵权词')]",
                 "position": "底部/文案", "index": "1", "timeout": 5, "rest": 1},
                {"name": "侵权确认_确定按钮",
                 "locator": "//div[contains(@class,'ivu-modal')]//span[contains(text(),'确定')]",
                 "position": "全局弹窗", "index": "1", "timeout": 3, "rest": 1},

                {"name": "容器_底部工具栏", "locator": "//div[@class='ui-footer']//span[contains(@class, 'f-btn')]",
                 "position": "底部", "index": "1", "timeout": 5, "rest": 0},

                # --- 2. 局部按钮 (必须在 工具栏 容器内查找) ---
                # [重点] 使用 .// 开头，表示相对查找
                # [重点] 使用 contains(., '文本') 而不是 text()='文本'，因为HTML里有空格 " 保存当前页 "
                {"name": "按钮_保存当前", "locator": ".//button[contains(., '保存当前页')]", "position": "工具栏内",
                 "index": "1", "timeout": 5, "rest": 1},
                {"name": "按钮_同步", "locator": ".//button[contains(., '同步至未推送站点')]", "position": "工具栏内",
                 "index": "1", "timeout": 5, "rest": 1},
                {"name": "按钮_翻译", "locator": ".//button[contains(., '翻译')]", "position": "工具栏内", "index": "1",
                 "timeout": 5, "rest": 1},
                {"name": "按钮_提交当前", "locator": ".//button[contains(., '保存并提交当前页')]",
                 "position": "工具栏内", "index": "1", "timeout": 5, "rest": 2},
                {"name": "按钮_取消", "locator": ".//button[contains(., '取消')]", "position": "工具栏内", "index": "1",
                 "timeout": 5, "rest": 1},

                # --- 3. 全局按钮 (不属于 f-btn，在最外层) ---
                # 这个按钮是全局唯一的，直接用绝对路径找
                {"name": "按钮_提交所有",
                 "locator": "//div[@class='ui-footer']/button[contains(., '保存并提交所有站点')]",
                 "position": "底部最右", "index": "1", "timeout": 5, "rest": 2},

                # 退出
                {"name": "按钮_取消", "locator": "//span[contains(text(), '取消')]", "position": "底部固定栏",
                 "index": "1", "timeout": 5, "rest": 1},
                {"name": "退出确认_确定关闭", "locator": "//span[contains(text(), '确定关闭')]", "position": "全局弹窗",
                 "index": "1", "timeout": 3, "rest": 1},
            ]
        },

        # ========================================================
        # C. 异常修复与图片 (基于日志 10:36 - 10:37)
        # ========================================================
        {
            "module": "C. 异常与图片占位",
            "elements": [
                # --- 图片功能 (占位用) ---
                {"name": "按钮_选择图片", "locator": "//span[contains(text(), '选择图片')]", "position": "图片模块",
                 "index": "1", "timeout": 5, "rest": 1},
                {"name": "按钮_图片确定",
                 "locator": "//div[contains(@class,'ivu-modal')]//span[contains(text(), '确定')]",
                 "position": "图片弹窗", "index": "1", "timeout": 3, "rest": 1},

                # --- 必填项修复 ---
                # 日志显示 "带*号为必填项"，且通常伴随红色边框 class="ivu-form-item-error"
                {"name": "必填_错误容器", "locator": "//div[contains(@class, 'ivu-form-item-error')]",
                 "position": "全局表单", "index": "1", "timeout": 1, "rest": 0},
                # 用于下拉框修复
                {"name": "必填_下拉框", "locator": ".//div[contains(@class, 'ivu-select-selection')]",
                 "position": "错误容器内", "index": "1", "timeout": 1, "rest": 0},

                # --- 报错弹窗关闭 ---
                # 针对 "KAUS站点推送失败..." 这种弹窗，通常右上角有 X
                {"name": "报错弹窗_关闭按钮", "locator": "//a[contains(@class, 'ivu-modal-close')]",
                 "position": "模态框右上角", "index": "1", "timeout": 2, "rest": 1},

                # --- Tab 页签遍历 ---
                # 用于 "失败站点扫尾" 流程，遍历 KAUS, KAFR 等
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
                    return json.load(f)
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