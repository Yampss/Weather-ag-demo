import os
from typing import Any
from dotenv import load_dotenv

from langchain_aws import ChatBedrockConverse
from langchain_core.tools import StructuredTool
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_tool_calling_agent
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
            "Retrieves a daily weather forecast (1–7 days) for a city. "
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

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder("agent_scratchpad"),
])

agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, return_intermediate_steps=True)


async def run_agent(user_message: str, conversation_history: list[dict]) -> dict[str, Any]:
    lc_history = []
    for msg in conversation_history:
        if msg.get("role") == "human":
            lc_history.append(HumanMessage(content=msg["content"]))
        elif msg.get("role") == "assistant":
            lc_history.append(AIMessage(content=msg["content"]))

    result = await agent_executor.ainvoke({
        "input": user_message,
        "chat_history": lc_history,
    })

    tool_calls = []
    for action, observation in result.get("intermediate_steps", []):
        tool_calls.append({
            "tool": action.tool,
            "input": action.tool_input if isinstance(action.tool_input, dict) else {"input": action.tool_input},
            "result": observation,
            "error": None,
        })

    updated_history = conversation_history + [
        {"role": "human", "content": user_message},
        {"role": "assistant", "content": result["output"]},
    ]

    return {
        "text": result["output"],
        "tool_calls": tool_calls,
        "updated_history": updated_history,
    }
