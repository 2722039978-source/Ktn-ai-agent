from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import engine, get_db
from models import Base, ChatMemory
import datetime
import requests
from bs4 import BeautifulSoup
from openai import OpenAI # type: ignore

# ===================== DeepSeek V4 配置 =====================
client = OpenAI(
    api_key="sk-1b7383851ed643d283de6bd1154c41eb",
    base_url="https://api.deepseek.com"
)

# 自动建表
Base.metadata.create_all(bind=engine)

app = FastAPI(title="DeepSeek V4 AI Agent", version="4.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    text: str

# ===================== 工具库 =====================
def tool_calculate(expr: str) -> str:
    try:
        return f"计算器执行结果：{eval(expr)}"
    except:
        return "计算失败，请输入正确数学表达式"

def tool_get_time() -> str:
    return f"当前时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

def tool_web_search(keyword: str) -> str:
    try:
        url = f"https://cn.bing.com/search?q={keyword}"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=8)
        soup = BeautifulSoup(res.text, "html.parser")
        ans = soup.find_all("p", limit=3)
        res_text = "\n".join([a.text for a in ans if a.text])
        return f"联网搜索结果：\n{res_text[:400]}" if res_text else "未搜索到有效信息"
    except:
        return "搜索失败"

TOOLS = {
    "calc": tool_calculate,
    "time": tool_get_time,
    "search": tool_web_search
}

# ===================== 核心调度 =====================
def llm_agent_run(user_input: str) -> tuple[str, str]:
    prompt = f"""
你是AI Agent调度器，根据用户问题只输出一个单词：
calc=计算  time=时间  search=联网搜索  chat=直接回答
用户问题：{user_input}
只输出单词，不要多余解释：
"""
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role":"user","content":prompt}],
        temperature=0
    )
    choose = resp.choices[0].message.content.strip()

    if choose in TOOLS:
        return TOOLS[choose](user_input), choose
    else:
        resp2 = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role":"user","content":user_input}],
            temperature=0.7
        )
        return resp2.choices[0].message.content.strip(), "DeepSeekV4回答"

# ===================== 接口 =====================
@app.post("/api/agent/chat")
def agent_chat(req: QueryRequest, db: Session = Depends(get_db)):
    reply, tool = llm_agent_run(req.text)
    record = ChatMemory(user_input=req.text, agent_reply=reply, tool_used=tool)
    db.add(record)
    db.commit()
    return {"code":200,"reply":reply,"tool":tool}

@app.get("/api/agent/memory")
def get_memory(db: Session = Depends(get_db)):
    data = db.query(ChatMemory).order_by(ChatMemory.id.desc()).limit(10).all()
    return {
        "code":200,
        "data":[{"user":d.user_input,"agent":d.agent_reply,"tool":d.tool_used} for d in data]
    }