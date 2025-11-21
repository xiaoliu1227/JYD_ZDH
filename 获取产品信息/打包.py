import os
import subprocess
import shutil


def build_exe():
    print("=" * 50)
    print("🚀 开始打包 EdgeAutomationTool ...")
    print("=" * 50)

    # 主文件名称
    main_file = "AutomationToolUI.py"
    exe_name = "EdgeAutomationTool"

    # 检查主文件是否存在
    if not os.path.exists(main_file):
        print(f"❌ 错误: 找不到 {main_file}，请确保脚本在项目根目录下。")
        return

    # PyInstaller 打包命令
    # -F: 打包成一个独立文件
    # -w: 不显示黑色命令行窗口 (GUI程序建议加上)
    # --clean: 清理缓存
    # --name: 指定生成的 exe 名字
    cmd = [
        "pyinstaller",
        "-F",
        "-w",
        "--clean",
        f"--name={exe_name}",
        main_file
    ]

    print(f"执行命令: {' '.join(cmd)}")

    try:
        # 直接调用系统中的 pyinstaller 命令
        subprocess.check_call(cmd, shell=True)

        print("\n" + "=" * 50)
        print("✅ 打包成功！")
        print(f"📂 EXE 文件位置: {os.path.join(os.getcwd(), 'dist', exe_name + '.exe')}")
        print("=" * 50)

        # 可选：清理打包产生的临时文件夹 build 和 .spec 文件
        # 如果你想保留这些文件用于调试，可以注释掉下面几行
        if os.path.exists("build"):
            shutil.rmtree("build")
        if os.path.exists(f"{exe_name}.spec"):
            os.remove(f"{exe_name}.spec")

    except subprocess.CalledProcessError:
        print("\n❌ 打包失败。")
        print("请检查是否已安装 PyInstaller (运行: pip install pyinstaller)")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")


if __name__ == "__main__":
    build_exe()
    input("\n按回车键退出...")