# winRAG
Windows Native Deploy Tool for Rerank &amp; Embedding
# 🚀 FastAPI Text Embedding & Reranker Server (Windows Native)

在 **Windows 原生环境**（无需 WSL）下，一键部署兼容 OpenAI API 的**纯文本向量服务**，支持主流开源 Embedding 与 Reranker 模型，提供 `/v1/embeddings` 和 `/v1/rerank` 接口，可直接接入 **Dify**、LangChain 等应用。

> ⚠️ **本版本仅支持纯文本，不处理图像输入**

✅ 单进程 · 单端口 · 双模型可选 · GPU/CPU 自定义 · 离线部署  
🔧 支持安装为 Windows 系统服务（开机自启）

---

## 🔧 功能特性

- **OpenAI 兼容 API**：无缝对接 Dify、LangChain、LlamaIndex 等生态
- **纯文本支持**：仅处理字符串，无图像依赖（PIL/base64 已移除）
- **双模型支持**：如 Qwen3 Embedding 和 Reranker 系列
  - `Qwen/Qwen3-Embedding-0.6B` → 生成向量嵌入
  - `Qwen/Qwen3-Reranker-0.6B` 或 `BAAI/bge-reranker-v2-m3` → 计算相关性排序
- **Windows 原生部署**：无需 WSL、Docker 或 Linux
- **离线运行**：模型本地加载，不依赖 Hugging Face 在线请求
- **图形化配置**：通过对话框选择模型目录（`setup.py`）
- **Windows 服务支持**：可安装为系统服务，后台运行、开机自启

---

## 📦 快速开始

### 环境要求

| 组件        | 要求                    |
| ----------- | ----------------------- |
| 操作系统    | Windows 10/11（64位）   |
| Python      | ≥ 3.10（推荐 3.11）     |
| GPU（可选） | NVIDIA 显卡 + CUDA 12.x |
| 磁盘空间    | ≥ 10 GB                 |

### 安装步骤

```powershell
# 创建虚拟环境
python -m venv fastapi_env

# 激活环境（PowerShell）
.\fastapi_env\Scripts\Activate.ps1

# 安装 PyTorch（CUDA 12.6 示例）
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126

# 安装依赖
pip install transformers accelerate einops uvicorn fastapi python-dotenv
```

### **下载模型（离线）**

从 Hugging Face 手动下载以下**纯文本模型**并解压至本地目录（如 `D:\models\`）：

- [Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
- [Qwen3-Reranker-0.6B](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B)
- [bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3)（可选）

> ✅ 每个模型目录必须包含 `config.json`、`tokenizer.json`、`pytorch_model.bin`（或 `.safetensors`）

### **初始化配置（图形化）**

```powershell
python setup.py
```

脚本将引导你：

- 选择是否部署 Embedding / Reranker
- **弹出窗口选择模型文件夹**
- 设置 API Key（可选）
- 自动生成 `.env` 配置文件

### **启动服务**

```powershell
python main.py
```

访问 http://localhost:8080/docs 查看 API 文档。

------

## **🖥️ 安装为 Windows 服务（可选）**

使用内置脚本将服务注册为系统后台进程：

```powershell
# 以管理员身份运行 PowerShell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
# 安装 Windows 服务，带参数定制服务名和服务端口
.\install_service.ps1 -ServiceName "TextRAG-Service" -Port 8081
```

✅ 支持：

- 自动日志记录（`logs/stdout.log`）
- 开机自启
- 无需用户登录即可运行
- 自动添加防火墙规则

管理命令：

```powershell
net start TextRAG-Service    # 启动
net stop TextRAG-Service     # 停止
.\uninstall_service.ps1 -ServiceName "TextRAG-Service"  # 卸载
```

------

## **🔄 在 Dify 中使用**

1. 进入 **Dify → 知识库 → Embedding Model → + Add Model Provider**
2. 选择 **OpenAI Compatible**
3. 填写：
   - **Model Name**: `text-embedding`（任意名称）
   - **API Base URL**: `http://<你的内网IP>:8080/v1`
     （若 Dify 运行在 Docker，建议用 `http://host.docker.internal:8080/v1`）
   - **API Key**: 与 `.env` 中 `API_KEY` 一致（如 `fastapi8888`）
4. 保存并选择该模型
5. （可选）在知识库设置中启用 **Rerank Model**，选择同一 Provider

------

## **📄 示例请求**

### **获取 Embedding**

```bash
curl http://localhost:8080/v1/embeddings \
  -H "Authorization: Bearer sk-local-qwen" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "text-embedding",
    "input": ["Hello world", "人工智能"]
  }'
```

### **执行 Rerank**

```bash
curl http://localhost:8080/v1/rerank \
  -H "Authorization: Bearer sk-local-qwen" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "猫是什么？",
    "documents": [
      "猫是一种常见的宠物。",
      "苹果是一种水果。"
    ]
  }'
```

------

## **📝 注意事项**

- 首次加载模型需 1–5 分钟，请耐心等待。
- 若显存不足，可在 `models.py` 中改用 `torch.float16`。
- Windows 防火墙可能阻止访问，请确保放行对应端口。
- 服务模式下，**必须先运行 `setup.py` 生成 `.env`**，否则启动失败。

------

## **🙌 致谢**

本项目基于以下开源模型，感谢社区贡献！

- [Qwen 系列模型](https://huggingface.co/Qwen) — Alibaba Tongyi Lab
- [BGE 系列模型](https://huggingface.co/BAAI) — Beijing Academy of Artificial Intelligence

------

## **💡 未来展望**

随着 Dify 原生支持 Hugging Face 模型，部署将更简单。目前此方案是 **Windows 用户运行纯文本 Embedding/Reranker 服务的最佳实践**。
