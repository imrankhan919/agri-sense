from app.agent.llm import get_llm
llm = get_llm()
result = llm.generate(
    system="You are a helpful assistant. Reply in one short line.",
    messages=[{"role": "user", "content": "Namaste! Gehu ka bhaav kya hai?"}],
    tools=[],
)
print("Provider :", type(llm).__name__)
print("Text :", result.text or "(koi text nahi)")
print("ToolCalls:", [(c.name, c.args) for c in result.tool_calls] or "(koi nahi)")
print("Tokens :", result.input_tokens, "in /", result.output_tokens, "out")