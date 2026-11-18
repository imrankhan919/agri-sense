import json
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Optional
from app.config import settings


@dataclass
class ToolCall:
    name: str
    args: dict
    id: Optional[str] = None


@dataclass
class LLMResult:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    raw: Any = None 



class GeminiClient:
    def __init__(self) -> None:
        from google import genai
        from google.genai import types
        self.model = settings.gemini_model
        self.client = genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(timeout=120_000), # 30 sec (milliseconds me)
        )
    @staticmethod
    def to_contents(messages: list[dict], types) -> list:
        contents, last_was_tool = [], False
        for m in messages:
            role = m["role"]
            if role == "tool":
                part = types.Part(function_response=types.FunctionResponse(
                    id=m.get("id"), name=m["name"], response={"result": m["result"]}))
                if last_was_tool: # ek saath kiye gaye tool calls ke jawab ek hi Content me jaate hain
                    contents[-1].parts.append(part)
                else:
                    contents.append(types.Content(role="user", parts=[part]))
                last_was_tool = True
                continue
            last_was_tool = False
            if role == "user":
                contents.append(types.Content(role="user", parts=[types.Part.from_text(text=m["content"])]))
            elif m.get("raw") is not None:
                contents.append(m["raw"]) # original model message (thought signatures samet)
            else:
                parts = [types.Part.from_text(text=m["content"])] if m.get("content") else []
                for c in m.get("tool_calls", []):
                    parts.append(types.Part(function_call=types.FunctionCall(
                        id=c.get("id"), name=c["name"], args=c["args"])))
                contents.append(types.Content(role="model", parts=parts))
        return contents

    def generate(self, system: str, messages: list[dict], tools: list) -> LLMResult:
        from google.genai import types
        declarations = [
        types.FunctionDeclaration(name=t.name, description=t.description, parameters=t.parameters)
        for t in tools
        ]
        config = types.GenerateContentConfig(
            system_instruction=system,
            tools=[types.Tool(function_declarations=declarations)] if declarations else None,
            temperature=0.2,
            )
        response = self.client.models.generate_content(
            model=self.model, contents=self.to_contents(messages, types), config=config)
        content = response.candidates[0].content
        text = "".join(p.text for p in (content.parts or []) if getattr(p, "text", None))
        calls = [ToolCall(name=fc.name, args=dict(fc.args or {}), id=getattr(fc, "id", None))
                for fc in (response.function_calls or [])]
        usage = response.usage_metadata
        return LLMResult(
            text=text, tool_calls=calls, raw=content,
            input_tokens=(usage.prompt_token_count or 0) if usage else 0,
            output_tokens=(usage.candidates_token_count or 0) if usage else 0,)


CROP_WORDS = {
 "wheat": "Wheat", "gehu": "Wheat", "gehun": "Wheat", "onion": "Onion", "pyaz": "Onion",
 "pyaaz": "Onion", "soybean": "Soybean", "soyabean": "Soybean", "tomato": "Tomato",
 "tamatar": "Tomato", "potato": "Potato", "aloo": "Potato", "maize": "Maize", "makka": "Maize",
 "chana": "Chana", "mustard": "Mustard", "sarson": "Mustard", "cotton": "Cotton", "rice": "Rice",
}

MARKET_WORDS = ["Indore", "Ujjain", "Mandsaur", "Bhopal", "Jaipur", "Nagpur", "Pune", "Nashik", "Lucknow"]



class FakeLLM:
    def generate(self, system: str, messages: list[dict], tools: list) -> LLMResult:
        last = messages[-1]
        if last["role"] == "tool":
            text = self._answer_from_tools(messages)
            return LLMResult(text=text, input_tokens=sum(len(str(m)) for m in messages) // 4,
                    output_tokens=len(text) // 4)
        q = last["content"].lower()
        crop = next((v for k, v in CROP_WORDS.items() if k in q), None)
        market = next((m for m in MARKET_WORDS if m.lower() in q), None)
        if any(w in q for w in ("my listing", "mera", "meri", "my produce", "apni")):
            call = ToolCall("list_my_produce", {})
        elif crop and any(w in q for w in ("trend", "badh", "ghat", "change", "month")):
            call = ToolCall("price_trend", {"crop": crop, "market": market or "Indore"})
        elif crop and any(w in q for w in ("best", "compare", "kahan", "sabse", "achha", "where", "top")):
            call = ToolCall("compare_markets", {"crop": crop})
        elif crop:
            args = {"crop": crop, **({"market": market} if market else {})}
            call = ToolCall("get_mandi_prices", args)
        else:
            text = ("Main mandi bhaav bata sakta hoon. Fasal ka naam batayein, "
        "jaise: 'Indore me gehu ka bhaav kya hai?'")
            return LLMResult(text=text, input_tokens=len(q) // 4, output_tokens=len(text) // 4)
        return LLMResult(tool_calls=[call], input_tokens=len(q) // 4, output_tokens=20)
        
    @staticmethod
    def _answer_from_tools(messages: list[dict]) -> str:
        result = messages[-1]["result"]
        if isinstance(result, dict) and "error" in result:
            return f"Maaf kijiye, {result['error']}."
        return "Mujhe ye data mila (offline demo model): " + json.dumps(result, ensure_ascii=False)[:500]



@lru_cache
def get_llm():
    if settings.llm_provider == "gemini":
        if not settings.gemini_api_key:
            raise RuntimeError(".env me GEMINI_API_KEY daalo, ya LLM_PROVIDER=fake rakho")
        return GeminiClient()
    return FakeLLM()
