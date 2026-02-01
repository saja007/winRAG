# models.py
import os
import torch
from transformers import AutoTokenizer, AutoModel, AutoModelForSequenceClassification
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 从环境变量读取配置
LOCAL_EMBEDDING_PATH = os.getenv("EMBEDDING_MODEL_PATH", "").strip()
LOCAL_RERANKER_PATH = os.getenv("RERANKER_MODEL_PATH", "").strip()
DEPLOY_EMBEDDING = os.getenv("DEPLOY_EMBEDDING", "true").lower() in ("true", "1", "yes")
DEPLOY_RERANKER = os.getenv("DEPLOY_RERANKER", "true").lower() in ("true", "1", "yes")

def _resolve_device(device_str: str) -> str:
    if device_str.lower() == "cuda":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return "cpu"

EMBEDDING_DEVICE = _resolve_device(os.getenv("EMBEDDING_DEVICE", "cuda"))
RERANKER_DEVICE = _resolve_device(os.getenv("RERANKER_DEVICE", "cpu"))

print(f"[Config] Deploy Embedding: {DEPLOY_EMBEDDING} on {EMBEDDING_DEVICE}")
print(f"[Config] Deploy Reranker: {DEPLOY_RERANKER} on {RERANKER_DEVICE}")

# 全局模型变量
embedding_tokenizer = None
embedding_model = None
reranker_tokenizer = None
reranker_model = None

def load_models():
    global embedding_tokenizer, embedding_model, reranker_tokenizer, reranker_model
    
    # === 加载 Embedding 模型 ===
    if DEPLOY_EMBEDDING:
        if not LOCAL_EMBEDDING_PATH or not os.path.isdir(LOCAL_EMBEDDING_PATH):
            raise ValueError(" EMBEDDING_MODEL_PATH 未设置或路径不存在！")
        print(f"Loading Embedding Model to {EMBEDDING_DEVICE}...")
        
        embedding_tokenizer = AutoTokenizer.from_pretrained(
            LOCAL_EMBEDDING_PATH,
            trust_remote_code=True,
            local_files_only=True
        )
        
        # 使用 dtype 替代已弃用的 torch_dtype
        embedding_model = AutoModel.from_pretrained(
            LOCAL_EMBEDDING_PATH,
            trust_remote_code=True,
            local_files_only=True,
            dtype=torch.float32  # ← 关键：使用 dtype，且为 float32 保证稳定
        ).eval().to(EMBEDDING_DEVICE)
        print(" Embedding model loaded.")
    else:
        print("Skipping Embedding model (disabled in config).")

    # === 加载 Reranker 模型 ===
    if DEPLOY_RERANKER:
        if not LOCAL_RERANKER_PATH or not os.path.isdir(LOCAL_RERANKER_PATH):
            raise ValueError(" RERANKER_MODEL_PATH 未设置或路径不存在！")
        print(f"Loading Reranker Model to {RERANKER_DEVICE}...")
        
        reranker_tokenizer = AutoTokenizer.from_pretrained(
            LOCAL_RERANKER_PATH,
            trust_remote_code=True,
            local_files_only=True
        )
        
        reranker_model = AutoModelForSequenceClassification.from_pretrained(
            LOCAL_RERANKER_PATH,
            trust_remote_code=True,
            local_files_only=True,
            dtype=torch.float32  # ← 同样使用 dtype + float32
        ).eval().to(RERANKER_DEVICE)
        print(" Reranker model loaded.")
    else:
        print("Skipping Reranker model (disabled in config).")

def get_embedding(inputs):
    if embedding_model is None:
        raise RuntimeError("Embedding model is not deployed.")
    
    with torch.no_grad():
        encoded = embedding_tokenizer(
            inputs,
            padding=True,
            truncation=True,
            max_length=8192,
            return_tensors="pt"
        ).to(EMBEDDING_DEVICE)
        
        outputs = embedding_model(**encoded)
        embeddings = outputs.last_hidden_state.mean(dim=1)
        
        # 转为 float32 再转 numpy，确保兼容性
        embeddings = embeddings.to(torch.float32).cpu().numpy()
        return embeddings.tolist()

def rerank(query: str, documents: list):
    if reranker_model is None:
        raise RuntimeError("Reranker model is not deployed.")
    
    scores = []
    with torch.no_grad():
        for doc in documents:
            try:
                encoded = reranker_tokenizer(
                    query, doc,
                    padding=True,
                    truncation=True,
                    max_length=512,
                    return_tensors="pt"
                ).to(RERANKER_DEVICE)
                
                outputs = reranker_model(**encoded)
                if outputs.logits.shape[1] == 1:
                    score = outputs.logits[0, 0].item()
                else:
                    score = outputs.logits[0, 1].item()
                scores.append(score)
            except Exception as e:
                logger.error(f"Error processing document: {e}")
                scores.append(-1e9)  # 返回极小值，避免 JSON 错误
    return scores

def unload_models():
    global embedding_model, embedding_tokenizer, reranker_model, reranker_tokenizer
    del embedding_model, embedding_tokenizer, reranker_model, reranker_tokenizer
    if torch.cuda.is_available():
        torch.cuda.empty_cache()