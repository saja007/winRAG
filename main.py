# main.py
import os
import sys
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import JSONResponse  # ← 新增：用于返回结构化 JSON
from pydantic import BaseModel
from typing import Union, List
import logging  # ← 新增：用于日志记录

load_dotenv()

def _validate_env_for_service():
    required_keys = ["DEPLOY_EMBEDDING", "DEPLOY_RERANKER", "EMBEDDING_DEVICE", "RERANKER_DEVICE"]
    for key in required_keys:
        if not os.getenv(key, "").strip():
            print(f"错误: .env 缺少必要字段 '{key}'", file=sys.stderr)
            sys.exit(1)
    if os.getenv("DEPLOY_EMBEDDING", "false").lower() == "true":
        path = os.getenv("EMBEDDING_MODEL_PATH", "").strip()
        if not path or not os.path.isdir(path):
            print(f"错误: EMBEDDING_MODEL_PATH 无效: '{path}'", file=sys.stderr)
            sys.exit(1)
    if os.getenv("DEPLOY_RERANKER", "false").lower() == "true":
        path = os.getenv("RERANKER_MODEL_PATH", "").strip()
        if not path or not os.path.isdir(path):
            print(f"错误: RERANKER_MODEL_PATH 无效: '{path}'", file=sys.stderr)
            sys.exit(1)

_validate_env_for_service()

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import List, Union, Optional
from contextlib import asynccontextmanager

PORT = int(os.getenv("PORT", "8080"))
API_KEY = os.getenv("API_KEY", "")

from models import load_models, unload_models, get_embedding, rerank, DEPLOY_EMBEDDING, DEPLOY_RERANKER

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up...")
    load_models()
    yield
    print("Shutting down...")
    unload_models()

app = FastAPI(title="Text Embedding & Reranker Server", lifespan=lifespan)

class EmbeddingRequest(BaseModel):
    model: str
    input: Union[str, List[str]]  # ← 只支持文本！

class RerankRequest(BaseModel):
    query: str
    documents: List[str]  # ← 只支持文本！

def verify_api_key(auth_header: Optional[str]):
    if API_KEY and (not auth_header or not auth_header.startswith("Bearer ")):
        raise HTTPException(status_code=401, detail="Missing or invalid API key")

@app.post("/v1/embeddings")
async def embeddings(request: EmbeddingRequest, authorization: str = Header(None)):
    # 验证 API Key（如果配置了）
    if API_KEY and (not authorization or not authorization.startswith("Bearer ")):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    if API_KEY and authorization.split(" ")[1] != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    inputs = request.input
    if isinstance(inputs, str):
        inputs = [inputs]

    try:
        embeddings_list = get_embedding(inputs)
        
        # === 计算 token 数量（估算）===
        # 注意：这是近似值，精确计数需用 tokenizer，但为简单起见用字符数/4
        total_tokens = sum(len(text) // 4 for text in inputs)  # 粗略估算
        
        # === 构造符合 OpenAI 格式的响应 ===
        response = {
            "object": "list",
            "data": [
                {
                    "object": "embedding",
                    "embedding": emb,
                    "index": i
                }
                for i, emb in enumerate(embeddings_list)
            ],
            "model": request.model,
            "usage": {
                "prompt_tokens": total_tokens,
                "total_tokens": total_tokens
            }
        }
        return JSONResponse(content=response)

    except Exception as e:
        logger.error(f"Embedding error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Embedding failed: {str(e)}")

@app.post("/v1/rerank")
async def rerank_endpoint(request: RerankRequest, authorization: Optional[str] = Header(None)):
    if not DEPLOY_RERANKER:
        raise HTTPException(status_code=404, detail="Reranker model is not deployed.")
    verify_api_key(authorization)
    
    scores = rerank(request.query, request.documents)
    results = [
        {"index": i, "relevance_score": score, "document": {"text": doc}}
        for i, (score, doc) in enumerate(zip(scores, request.documents))
    ]
    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    return {"results": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)