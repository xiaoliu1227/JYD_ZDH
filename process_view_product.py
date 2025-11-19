from base_executor import BaseExecutor


class ViewProductProcess:
    """
    流程 2: 查看产品信息并提取表格
    """

    def __init__(self, executor: BaseExecutor):
        self.ex = executor
        self.log = self.ex.log

    def execute_workflow(self):
        self.log("--- 启动产品查看流程 ---")

        # 1. 悬停到商品图标
        self.ex.hover("nav_product_icon")

        # 2. 点击分销商品列表 (或直接点击)
        self.ex.click("nav_product_distribution_list")

        # 3. 等待页面跳转到商品列表页
        self.ex.wait_url_contains("/distribution/list", timeout=10)

        # 4. 查找SKU输入框并输入SKU
        sku_to_search = self.ex.substitute_value("{sku}")
        self.ex.safe_type("product_list_sku_input", sku_to_search)

        # 5. 点击查询
        self.ex.click("product_list_search_button")

        # 6. 等待查询结果出现 (查看详情按钮出现即可)
        self.ex.wait_visible("product_list_view_detail_button", timeout=10)

        # 7. 点击查看详情按钮，弹出弹窗
        self.ex.click("product_list_view_detail_button")

        # 8. 等待详情弹窗出现
        self.ex.wait_visible("detail_popup_dialog", timeout=5)

        # 9. 提取表格数据
        table_data = self.ex.get_table_data("detail_info_table", timeout=10)
        self.log(f"成功提取 {len(table_data)} 行产品基本信息数据。")

        self.log("--- 产品查看流程执行完毕 ---")