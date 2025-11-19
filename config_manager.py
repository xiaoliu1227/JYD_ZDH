import os
import json
from PyQt5.QtWidgets import QMessageBox

CONFIG_FILE = 'automation_config.json'
# 定义流程模块的映射关系。此字典现在是所有文件共享的数据源。
PROCESS_MODULES = {
    "workflow_full_login": {
        "module": "process_login", "class": "LoginProcess",
        "elements": [
            "login_page_username_input", "login_page_password_input", "login_page_login_button",
            "org_popup_dialog", "org_popup_input", "org_popup_list_item", "org_popup_confirm_button",
            "home_page_notification_popup", "home_page_notification_close_button"
        ]
    },
    "workflow_view_product_info": {
        "module": "process_view_product", "class": "ViewProductProcess",
        "elements": [
            "nav_product_icon", "nav_product_distribution_list", "product_list_sku_input",
            "product_list_search_button", "product_list_view_detail_button", "detail_popup_dialog",
            "detail_info_table"
        ]
    },
    "workflow_logout": {
        "module": "process_logout", "class": "LogoutProcess",
        "elements": ["home_page_logout_button"]
    }
}

# 默认配置结构 (新增 logout_button 元素和 workflow_logout 流程)
DEFAULT_CONFIG = {
    "accounts": {},
    "elements": {
        "login_page_username_input": {"description": "登录页-账号输入框", "by": "auto",
                                      "value": "placeholder=\"请输入手机号或邮箱\""},
        "login_page_password_input": {"description": "登录页-密码输入框", "by": "auto",
                                      "value": "placeholder=\"请输入登录密码\""},
        "login_page_login_button": {"description": "登录页-登录按钮", "by": "auto", "value": "<span>登录"},
        "org_popup_dialog": {"description": "组织选择弹窗-整个弹窗", "by": "auto",
                             "value": "class=\"el-dialog__body\""},
        "org_popup_input": {"description": "组织选择弹窗-输入框", "by": "auto", "value": "placeholder=\"请选择\""},
        "org_popup_list_item": {"description": "组织选择弹窗-列表项", "by": "auto", "value": "<span>156"},
        "org_popup_confirm_button": {"description": "组织选择弹窗-确认按钮", "by": "auto", "value": "<span>确认登录"},
        "home_page_notification_popup": {"description": "首页-弹窗(可选)", "by": "auto", "value": ""},
        "home_page_notification_close_button": {"description": "首页-关闭按钮(可选)", "by": "auto", "value": ""},
        "nav_product_icon": {"description": "导航栏-商品主图标（用于悬停）", "by": "auto", "value": "i:商品"},
        "nav_product_distribution_list": {"description": "导航栏-分销商品列表", "by": "auto",
                                          "value": "span:分销商品列表"},
        "product_list_sku_input": {"description": "商品列表页-SKU输入框", "by": "auto",
                                   "value": "placeholder=\"SKU编码\""},
        "product_list_search_button": {"description": "商品列表页-查询按钮", "by": "auto", "value": "button:查询"},
        "product_list_view_detail_button": {"description": "商品列表页-查看详情按钮", "by": "auto",
                                            "value": "span:查看详情"},
        "detail_popup_dialog": {"description": "详情弹窗-主容器（用于等待）", "by": "auto",
                                "value": "class=\"el-dialog\""},
        "detail_info_table": {"description": "详情弹窗-基本信息区域的Table", "by": "auto",
                              "value": "id=\"basic-info-table\""},
        # 【新增】退出按钮元素
        "home_page_logout_button": {"description": "首页-退出登录按钮", "by": "auto", "value": "span:退出登录"}
    },
    "workflows": {
        "workflow_full_login": {"description": "标准登录流程", "module": "process_login", "class": "LoginProcess"},
        "workflow_view_product_info": {"description": "查看产品信息并提取表格", "module": "process_view_product",
                                       "class": "ViewProductProcess"},
        # 【新增】退出登录流程
        "workflow_logout": {"description": "退出登录流程", "module": "process_logout", "class": "LogoutProcess"}
    }
}


def load_config():
    if not os.path.exists(CONFIG_FILE):
        try:
            save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG
        except Exception as e:
            QMessageBox.critical(None, "错误", f"创建配置失败: {e}")
            return None
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if "accounts" not in data: data["accounts"] = {}

            # 配置同步/合并逻辑
            default_elements = DEFAULT_CONFIG.get('elements', {})
            if "elements" not in data: data["elements"] = {}

            for key, default_info in default_elements.items():
                if key not in data["elements"]:
                    data["elements"][key] = default_info
                else:
                    data["elements"][key]["description"] = default_info["description"]
                    if "by" not in data["elements"][key]:
                        data["elements"][key]["by"] = "auto"

            return data
    except Exception as e:
        QMessageBox.critical(None, "错误", f"加载配置失败: {e}")
        return None


def save_config(config_data):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        QMessageBox.critical(None, "保存错误", f"无法保存: {e}")
        return False