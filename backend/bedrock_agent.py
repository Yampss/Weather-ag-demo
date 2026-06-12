import os
from typing import Any
from dotenv import load_dotenv

from langchain_aws import ChatBedrockConverse
from langchain_core.tools import StructuredTool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from weather_tools import get_current_weather as _get_current_weather
from weather_tools import get_weather_forecast as _get_weather_forecast

load_dotenv()


class WeatherInput(BaseModel):
    location: str = Field(description="City name, e.g. 'London', 'New York', 'Tokyo'")


class ForecastInput(BaseModel):
    location: str = Field(description="City name, e.g. 'Berlin', 'Sydney'")
    days: int = Field(default=5, ge=1, le=7, description="Number of forecast days, 1 to 7")


async def _current_weather_fn(location: str) -> dict:
    return await _get_current_weather(location)


async def _forecast_fn(location: str, days: int = 5) -> dict:
    return await _get_weather_forecast(location, days)


tools = [
    StructuredTool.from_function(
        coroutine=_current_weather_fn,
        name="get_current_weather",
        description=(
            "Retrieves real-time current weather conditions for a city. "
            "Use for questions about current temperature, humidity, wind, UV index, "
            "or any 'right now' / 'today' weather question."
        ),
        args_schema=WeatherInput,
    ),
    StructuredTool.from_function(
        coroutine=_forecast_fn,
        name="get_weather_forecast",
        description=(
            "Retrieves a daily weather forecast (1-7 days) for a city. "
            "Use for future weather, upcoming days, weekly forecast, or event planning questions."
        ),
        args_schema=ForecastInput,
    ),
]

llm = ChatBedrockConverse(
    model=os.getenv("BEDROCK_MODEL_ID", "amazon.nova-micro-v1:0"),
    region_name=os.getenv("AWS_REGION", "us-east-1"),
)

SYSTEM_PROMPT = """You are WeatherAI, a friendly and knowledgeable weather assistant.
You have access to real-time weather tools and always provide accurate, helpful weather information.

When answering weather questions:
1. Always use the provided tools to get real data — never guess or fabricate weather information.
2. Present data in a clear, engaging way with relevant emojis.
3. Include practical advice (e.g., "bring an umbrella", "great day for outdoor activities").
4. When comparing cities or giving multiple forecasts, call tools multiple times.
5. After receiving tool results, always summarize the data in a conversational, helpful manner.

Format your final response in a friendly, readable way. Include:
- Key temperature info (current / high / low)
- Weather conditions
- Practical recommendations based on the weather

Keep responses concise but complete."""

graph = create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)


async def run_agent(user_message: str, conversation_history: list[dict]) -> dict[str, Any]:
    messages = []
    for msg in conversation_history:
        if msg.get("role") == "human":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg.get("role") == "assistant":
            messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=user_message))

    result = await graph.ainvoke({"messages": messages})

    pending: dict[str, dict] = {}
    tool_calls_log: list[dict] = []

    for msg in result["messages"]:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                pending[tc["id"]] = {
                    "tool": tc["name"],
                    "input": tc["args"],
                    "result": None,
                    "error": None,
                }
        elif isinstance(msg, ToolMessage):
            if msg.tool_call_id in pending:
                entry = pending.pop(msg.tool_call_id)
                entry["result"] = msg.content
                tool_calls_log.append(entry)

    final_text = ""
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and not msg.tool_calls:
            content = msg.content
            if isinstance(content, str):
                final_text = content
            elif isinstance(content, list):
                final_text = " ".join(
                    block.get("text", "") for block in content
                    if isinstance(block, dict) and "text" in block
                )
            break

    updated_history = conversation_history + [
        {"role": "human", "content": user_message},
        {"role": "assistant", "content": final_text},
    ]

    return {
        "text": final_text,
        "tool_calls": tool_calls_log,
        "updated_history": updated_history,
    }
