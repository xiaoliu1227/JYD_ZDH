import json
import os

# 【核心修改 1】定义共享文件夹根目录 (Windows 网络路径格式)
SHARED_ROOT_DIR = r'\\192.168.10.66\erp'

# 【核心修改 2】配置文件保存路径 -> 指向共享文件夹
# 这样所有电脑读取的都是同一份元素定位配置
CONFIG_FILE = os.path.join(SHARED_ROOT_DIR, 'element_config.json')

# **【定义模块化结构的默认配置】**
DEFAULT_CONFIG = {
    "LOGIN_URL": "https://saaserp-pos.yibainetwork.com/#/login_page",
    "ORG_CODE": "156",

    # 【核心修改 3】默认 SKU 文件路径 -> 指向共享文件夹
    # 这样打开软件时，默认就会去找共享盘里的 skus.xlsx
    "SKU_FILE_PATH": os.path.join(SHARED_ROOT_DIR, 'skus.xlsx'),

    "ACCOUNTS": [],

    # 元素配置按模块划分 (代码结构优先)
    "ELEMENT_CONFIG": [
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
            "module": "B. 导航与流程",
            "elements": [
                {"name": "导航_商品主图标", "locator": "class=\"coll_span white\"", "position": "当前元素",
                 "index": "1"},
                {"name": "导航_分销商品列表", "locator": "<span>分销商品列表", "position": "当前元素", "index": "1"},
            ]
        },
        {
            "module": "C. 商品查询与详情",
            "elements": [
                {"name": "product_list_sku_input", "locator": "//textarea", "position": "当前元素", "index": "1"},
                {"name": "product_list_search_button", "locator": "<span>查询", "position": "当前元素", "index": "1"},
                {"name": "product_list_view_detail_button", "locator": "查看详情", "position": "当前元素",
                 "index": "1"},

                {"name": "detail_popup_dialog", "locator": "aria-label=\"商品详情\"", "position": "当前元素",
                 "index": "1"},
                {"name": "detail_close_button", "locator": "class=\"el-dialog__headerbtn\"", "position": "当前元素",
                 "index": "1"},
            ]
        },
    ]
}


class ConfigManager:
    """
    负责应用的配置加载、保存和默认值管理。
    """

    def __init__(self, config_file=CONFIG_FILE, default_config=DEFAULT_CONFIG):
        self.config_file = config_file
        self.default_config = default_config
        self.config_data = {}

    def load_config(self):
        """从文件加载配置"""
        self.config_data = self.default_config.copy()

        # 检查共享路径是否存在
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)

                    self.config_data.update({
                        k: v for k, v in file_data.items()
                        if k not in ['ELEMENT_CONFIG', 'ACCOUNTS']
                    })

                    if "ACCOUNTS" in file_data:
                        self.config_data["ACCOUNTS"] = file_data["ACCOUNTS"]

                    if "ELEMENT_CONFIG" in file_data:
                        self.config_data["ELEMENT_CONFIG_FROM_FILE"] = file_data["ELEMENT_CONFIG"]

                    print(f"配置文件加载成功: {self.config_file}")
                    return self.config_data
            except json.JSONDecodeError as e:
                print(f"警告: 配置文件格式错误 ({e})，使用默认配置。")
                return self.default_config
            except Exception as e:
                print(f"读取配置文件失败 (可能是网络问题): {e}")
                return self.default_config
        else:
            print(f"配置文件不存在: {self.config_file}，将使用默认配置。")
            # 如果共享目录可访问但文件不存在，程序保存时会自动创建
            return self.default_config

    def save_config(self, data):
        """将数据保存到配置文件中"""
        self.config_data = data

        # 确保共享目录存在 (如果网络通畅但目录没了)
        directory = os.path.dirname(self.config_file)
        if not os.path.exists(directory):
            print(f"错误: 共享文件夹不可访问: {directory}")
            return False

        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, ensure_ascii=False, indent=4)
            print(f"配置已保存到: {self.config_file}")
            return True
        except Exception as e:
            print(f"错误: 保存配置文件时出错: {e}")
            return False


# 实例化管理器
config_manager = ConfigManager()