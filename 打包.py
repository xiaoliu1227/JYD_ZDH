import os
import subprocess
import sys
import shutil


def install_package(package):
    """自动安装缺失的库"""
    try:
        __import__(package)
    except ImportError:
        print(f"正在安装 {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])


def build_exe():
    print("=" * 50)
    print("开始构建 Edge 自动化工具 EXE...")
    print("=" * 50)

    # 1. 检查并安装 PyInstaller
    install_package("PyInstaller")

    # 2. 定义主文件和打包参数
    main_file = "AutomationToolUI.py"
    exe_name = "EdgeAutomationTool"

    # 检查主文件是否存在
    if not os.path.exists(main_file):
        print(f"错误: 找不到主文件 {main_file}，请确保此脚本在项目根目录下运行。")
        input("按回车键退出...")
        return

    # PyInstaller 参数说明:
    # -F / --onefile : 打包成单个 exe 文件
    # -w / --noconsole : 不显示黑色控制台窗口 (GUI 程序专用)
    # --name : 指定生成 exe 的名字
    # --clean : 清理临时文件
    # --hidden-import : 强制导入某些可能未被识别的库

    cmd = [
        "pyinstaller",
        "-F",  # 单文件模式
        "-w",  # 无控制台模式 (如果你想看报错信息，可以去掉这一行)
        "--clean",
        f"--name={exe_name}",
        main_file
    ]

    print(f"执行打包命令: {' '.join(cmd)}")

    try:
        # 调用 PyInstaller
        subprocess.check_call(cmd)

        print("\n" + "=" * 50)
        print("✅ 打包成功！")
        print(f"可执行文件位置: {os.path.join(os.getcwd(), 'dist', exe_name + '.exe')}")
        print("=" * 50)

        # 自动清理生成的临时文件 (可选)
        print("正在清理临时文件...")
        if os.path.exists("build"):
            shutil.rmtree("build")
        if os.path.exists(f"{exe_name}.spec"):
            os.remove(f"{exe_name}.spec")
        print("清理完成。")

    except subprocess.CalledProcessError as e:
        print("\n❌ 打包失败，请检查错误信息。")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")


if __name__ == "__main__":
    build_exe()
    input("\n按回车键退出...")