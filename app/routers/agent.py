import json
import time

from fastapi import APIRouter, Depends , HTTPException
from sqlmodel import Session, SQLModel , select
from app.agent.quota import add_usage, check_quota, tokens_used_today
from app.config import settings
from app.agent.loop import run_agent
from app.database import get_session
from app.deps import get_current_user
from app.models import User , AgentRun
from app.ratelimit import rate_limit

router = APIRouter(prefix="/agent", tags=["agent"])

chat_limit = rate_limit(10, 60, "bucket") # chat mehngi hai: kam requests allow

MAX_QUESTION_CHARS = 500


class ChatRequest(SQLModel):
     question: str

class ChatResponse(SQLModel):
    answer: str
    tools_used: list[str]
    tokens_used: int

class UsageRead(SQLModel):
    tokens_used_today: int
    daily_quota: int

class RunRead(SQLModel):
    id: int
    question: str
    answer: str
    status: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


def _log_run(session: Session, user: User, question: str, answer: str, steps: list,
    tin: int, tout: int, started: float, status: str) -> None:
    session.add(AgentRun(
    user_id=user.id, question=question, answer=answer, steps_json=json.dumps(steps, default=str),
    input_tokens=tin, output_tokens=tout, status=status,
    latency_ms=int((time.perf_counter() - started) * 1000),
    ))
    session.commit()



@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(chat_limit)])
def chat(
 body: ChatRequest,
 user: User = Depends(get_current_user),
 session: Session = Depends(get_session),
):
    question = body.question.strip()
    if not question or len(question) > MAX_QUESTION_CHARS:
        raise HTTPException(400, f"Sawal 1 se {MAX_QUESTION_CHARS} characters ke beech hona chahiye")
    check_quota(user.id) # LLM call se pehle
    started = time.perf_counter()
    try:
        result = run_agent(session, user, question)
    except Exception:
        session.rollback()
        _log_run(session, user, question, "", [], 0, 0, started, "error")
        raise HTTPException(502, "AI service abhi available nahi hai. Thodi der baad try karo.")
    
    add_usage(user.id, result.total_tokens)
    _log_run(session, user, question, result.answer, result.steps,
    result.input_tokens, result.output_tokens, started, "ok")
    return ChatResponse(answer=result.answer, tools_used=[s["tool"] for s in result.steps],
            tokens_used=result.total_tokens)



@router.get("/usage", response_model=UsageRead)
def usage(user: User = Depends(get_current_user)):
    return UsageRead(tokens_used_today=tokens_used_today(user.id),
    daily_quota=settings.agent_daily_token_quota)


@router.get("/runs", response_model=list[RunRead])
def my_runs(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    stmt = select(AgentRun).where(AgentRun.user_id == user.id).order_by(AgentRun.id.desc()).limit(20)
    return session.exec(stmt).all()
