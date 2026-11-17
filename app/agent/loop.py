from dataclasses import dataclass, field
from sqlmodel import Session
from app.agent.llm import get_llm
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import run_tool, tool_specs
from app.models import User

MAX_STEPS = 5


@dataclass
class AgentResult:
    answer: str
    steps: list[dict] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


def run_agent(session: Session, user: User, question: str, llm=None) -> AgentResult:
    llm = llm or get_llm()
    messages: list[dict] = [{"role": "user", "content": question}]
    result = AgentResult(answer="")
    for _ in range(MAX_STEPS):
        reply = llm.generate(system=SYSTEM_PROMPT, messages=messages, tools=tool_specs())
        result.input_tokens += reply.input_tokens
        result.output_tokens += reply.output_tokens
        if not reply.tool_calls: # LLM ne final jawab de diya -> loop khatam
            result.answer = reply.text
            return result
        messages.append({
            "role": "assistant", "content": reply.text, "raw": reply.raw,
            "tool_calls": [{"id": c.id, "name": c.name, "args": c.args} for c in reply.tool_calls],
            })
        for call in reply.tool_calls:
                output = run_tool(call.name, call.args, session, user)
                failed = isinstance(output, dict) and "error" in output
                result.steps.append({"tool": call.name, "args": call.args, "ok": not failed})
                messages.append({"role": "tool", "id": call.id, "name": call.name, "result": output})
    result.answer = ("Maaf kijiye, is sawal ka jawab banane me bahut steps lag gaye. "
    "Kripya sawal chhota karke poochiye.")
    return result
