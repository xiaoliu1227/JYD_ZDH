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
                # SKU 输入框和查询按钮 (用于主列表页)
                {"name": "product_list_sku_input", "locator": "//textarea"},
                {"name": "product_list_search_button", "locator": "<span>查询"},
                {"name": "product_list_view_detail_button", "locator": "查看详情"},

                # 详情弹窗和数据抓取元素
                {"name": "detail_popup_dialog", "locator": "aria-label=\"商品详情\""},
                {"name": "detail_info_table", "locator": "//div[@class='el-dialog__body']//table"},
            ]
        },
    ]
}


class ConfigManager:
    """
    负责应用的配置加载、保存和默认值管理。
    采用 Python 代码结构优先原则，确保配置项不会因 JSON 文件缺失而丢失。
    """

    def __init__(self, config_file=CONFIG_FILE, default_config=DEFAULT_CONFIG):
        self.config_file = config_file
        self.default_config = default_config
        self.config_data = {}

    def load_config(self):
        """
        从文件加载配置。如果文件不存在或加载失败，则使用默认配置。

        返回: 完整的配置字典。
        """
        # 1. 默认使用代码中的结构作为起点
        self.config_data = self.default_config.copy()

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)

                    # 2. 覆盖顶层配置 (URL, ORG_CODE, 文件路径等)
                    self.config_data.update({
                        k: v for k, v in file_data.items()
                        if k not in ['ELEMENT_CONFIG', 'ACCOUNTS']
                    })

                    # 3. 合并 ACCOUNTS 列表
                    if "ACCOUNTS" in file_data:
                        self.config_data["ACCOUNTS"] = file_data["ACCOUNTS"]

                    # 4. ELEMENT_CONFIG 的模块化合并
                    #    这里只传递 JSON 中已保存的 ELEMENT_CONFIG 结构
                    if "ELEMENT_CONFIG" in file_data:
                        # 临时存储，供 AutomationToolUI 中的 _unify_element_config 使用
                        self.config_data["ELEMENT_CONFIG_FROM_FILE"] = file_data["ELEMENT_CONFIG"]

                    print(f"配置文件 {self.config_file} 加载成功。")
                    return self.config_data
            except json.JSONDecodeError as e:
                print(f"警告: 配置文件 {self.config_file} 格式错误 ({e})，使用默认配置结构。")
                # 如果 JSON 格式错误，则直接返回默认结构
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


# 【关键修复点：实例化管理器】
# 实例化管理器，方便外部模块（AutomationToolUI）通过 config_manager.load_config() 调用
config_manager = ConfigManager()