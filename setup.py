# setup.py
"""
Text Embedding & Reranker 服务初始化脚本
- 支持通过图形界面选择模型文件夹
- 生成/更新 .env 配置文件
- 仅适用于桌面环境（需 GUI）
"""

import os
import sys
from dotenv import load_dotenv, set_key
from tkinter import Tk, filedialog

ENV_PATH = ".env"

def _str_to_bool(s: str) -> bool:
    return s.lower() in ("true", "1", "yes", "on")

def select_folder(title: str) -> str:
    """弹出文件夹选择对话框"""
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    folder = filedialog.askdirectory(title=title)
    root.destroy()
    return folder.replace("\\", "/") if folder else ""

def validate_and_save_path(env_key: str, path: str):
    if not path:
        print(f" 错误: {env_key} 不能为空！")
        sys.exit(1)
    if not os.path.isdir(path):
        print(f" 错误: 路径不存在或不是文件夹: {path}")
        sys.exit(1)
    # 检查是否包含 config.json（基本模型完整性验证）
    if not os.path.exists(os.path.join(path, "config.json")):
        print(f" 警告: {path} 中未找到 config.json，可能不是有效模型目录。")
        confirm = input(" 是否继续？(y/n): ").strip().lower()
        if confirm != "y":
            sys.exit(1)
    set_key(ENV_PATH, env_key, path)
    print(f" 已保存: {env_key} = {path}")

def main():
    print("Text Embedding & Reranker 服务初始化配置\n")
    load_dotenv()  # 加载现有配置（如果有）

    # 部署选项
    deploy_emb_input = input("是否部署 Embedding 模型? (y/n, 默认 y): ").strip().lower()
    deploy_emb = deploy_emb_input != "n"
    
    deploy_rerank_input = input("是否部署 Reranker 模型? (y/n, 默认 n): ").strip().lower()
    deploy_rerank = deploy_rerank_input == "y"

    # 保存开关
    set_key(ENV_PATH, "DEPLOY_EMBEDDING", str(deploy_emb).lower())
    set_key(ENV_PATH, "DEPLOY_RERANKER", str(deploy_rerank).lower())

    # 设备自动检测
    emb_device = "cuda" if _has_cuda() else "cpu"
    rerank_device = "cpu"  # Reranker 通常较小，可强制 CPU 或按需修改
    set_key(ENV_PATH, "EMBEDDING_DEVICE", emb_device)
    set_key(ENV_PATH, "RERANKER_DEVICE", rerank_device)

    # 模型路径选择（带图形界面）
    if deploy_emb:
        print("\n请选择 Embedding 模型文件夹（例如：Qwen3-Embedding-0.6B）")
        emb_path = select_folder("选择 Embedding 模型目录")
        validate_and_save_path("EMBEDDING_MODEL_PATH", emb_path)

    if deploy_rerank:
        print("\n请选择 Reranker 模型文件夹（例如：Qwen3-Reranker-0.6B 或 bge-reranker-v2-m3）")
        rerank_path = select_folder("选择 Reranker 模型目录")
        validate_and_save_path("RERANKER_MODEL_PATH", rerank_path)

    # API_KEY 设置
    api_key = input("\n请输入 API_KEY（留空则禁用认证）: ").strip()
    set_key(ENV_PATH, "API_KEY", api_key if api_key else "")
    
    # 默认端口
    set_key(ENV_PATH, "PORT", "8080")

    print(f"\n 初始化完成！配置已保存到 {os.path.abspath(ENV_PATH)}")
    print("现在可以运行 `python main.py` 启动服务，或安装为 Windows 服务，服务端口 8080。")

def _has_cuda():
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n️ 用户取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n 初始化失败: {e}")
        input("\n按 Enter 退出...")
        sys.exit(1)