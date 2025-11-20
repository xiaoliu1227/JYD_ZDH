import json
import os

# 默认的配置文件名
CONFIG_FILE = 'element_config.json'

# **【定义模块化结构的默认配置】**
DEFAULT_CONFIG = {
    "LOGIN_URL": "https://saaserp-pos.yibainetwork.com/#/login_page",
    "ORG_CODE": "156",
    "SKU_FILE_PATH": "skus.xlsx",
    "ACCOUNTS": [],

    # 元素配置按模块划分 (代码结构优先)
    "ELEMENT_CONFIG": [
        {
            "module": "A. 登录与组织选择",
            "elements": [
                {"name": "账号输入框", "locator": "placeholder=\"请输入手机号或邮箱\""},
                {"name": "密码输入框", "locator": "placeholder=\"请输入登录密码\""},
                {"name": "登录按钮", "locator": "<span>登录"},

                {"name": "组织选择弹窗", "locator": "class=\"el-dialog__body\""},
                {"name": "组织输入框", "locator": "placeholder=\"请选择\""},
                {"name": "组织列表项", "locator": "<span>156"},
                {"name": "确认登录按钮", "locator": "<span>确认登录"},
            ]
        },
        {
            "module": "B. 导航与流程",
            "elements": [
                {"name": "导航_商品主图标", "locator": "class=\"coll_span white\""},
                {"name": "导航_分销商品列表", "locator": "<span>分销商品列表"},
            ]
        },
        {
            "module": "C. 商品查询与详情",
            "elements": [
                {"name": "product_list_sku_input", "locator": "//textarea"},
                {"name": "product_list_search_button", "locator": "<span>查询"},
                {"name": "product_list_view_detail_button", "locator": "查看详情"},

                {"name": "detail_popup_dialog", "locator": "aria-label=\"商品详情\""},
                {"name": "detail_info_table", "locator": "//div[@class='el-dialog__body']//table"},
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
        """
        从文件加载配置。

        返回: 完整的配置字典。
        """
        self.config_data = self.default_config.copy()

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

                    print(f"配置文件 {self.config_file} 加载成功。")
                    return self.config_data
            except json.JSONDecodeError as e:
                print(f"警告: 配置文件 {self.config_file} 格式错误 ({e})，使用默认配置结构。")
                return self.default_config
        else:
            print(f"配置文件 {self.config_file} 不存在，使用默认配置结构。")
            return self.default_config

    def save_config(self, data):
        """
        将数据保存到配置文件中。
        """
        self.config_data = data
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, ensure_ascii=False, indent=4)
            print(f"配置已保存到 {self.config_file}")
            return True
        except Exception as e:
            print(f"错误: 保存配置文件时出错: {e}")
            return False


# 实例化管理器，解决 AttributeError
config_manager = ConfigManager()