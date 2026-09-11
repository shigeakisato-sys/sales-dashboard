"""ダッシュボードのAIチャット用バックエンド(FastAPI)。

OpenAIのAPIキーは .env からのみ読み込み、フロントエンドには一切渡さない。
このサーバー自身が dashboard.html を配信するので、チャットは同一オリジンで動作する
(http://127.0.0.1:8000/ を開く)。
"""

import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DASHBOARD_FILE = BASE_DIR / "dashboard.html"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

app = FastAPI(title="Sales Dashboard Chat")

_client = None
if OPENAI_API_KEY:
    from openai import OpenAI

    _client = OpenAI(api_key=OPENAI_API_KEY)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = None


class ChatResponse(BaseModel):
    reply: str


SYSTEM_PROMPT = "あなたは親切なアシスタントです。日本語で簡潔に答えてください。"


@app.get("/")
def index():
    return FileResponse(DASHBOARD_FILE)


@app.get("/api/health")
def health():
    return {"ok": True, "hasKey": bool(OPENAI_API_KEY)}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if _client is None:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY が .env に設定されていません。.env.example を参考に .env を作成してください。",
        )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in req.history or []:
        if m.role in ("user", "assistant"):
            messages.append({"role": m.role, "content": m.content})
    messages.append({"role": "user", "content": req.message})

    try:
        completion = _client.chat.completions.create(model=OPENAI_MODEL, messages=messages)
    except Exception as e:  # OpenAI SDK例外をまとめて502として返す
        raise HTTPException(status_code=502, detail=f"OpenAI APIエラー: {e}")

    reply = completion.choices[0].message.content or ""
    return ChatResponse(reply=reply)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
