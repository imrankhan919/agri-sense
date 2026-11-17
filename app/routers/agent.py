from fastapi import APIRouter, Depends
from sqlmodel import Session, SQLModel
from app.agent.loop import run_agent
from app.database import get_session
from app.deps import get_current_user
from app.models import User
from app.ratelimit import rate_limit

router = APIRouter(prefix="/agent", tags=["agent"])

chat_limit = rate_limit(10, 60, "bucket") # chat mehngi hai: kam requests allow

class ChatRequest(SQLModel):
     question: str

class ChatResponse(SQLModel):
    answer: str
    tools_used: list[str]
    tokens_used: int

@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(chat_limit)])
def chat(
 body: ChatRequest,
 user: User = Depends(get_current_user),
 session: Session = Depends(get_session),
):
    result = run_agent(session, user, body.question)
    return ChatResponse(answer=result.answer, tools_used=[s["tool"] for s in result.steps],tokens_used=result.total_tokens)