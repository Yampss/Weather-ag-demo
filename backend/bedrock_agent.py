import os
import boto3
from typing import Any
from dotenv import load_dotenv
from weather_tools import get_current_weather, get_weather_forecast

load_dotenv()


def _get_bedrock_client():
    kwargs: dict[str, Any] = {
        "region_name": os.getenv("AWS_REGION", "us-east-1"),
    }
    key = os.getenv("AWS_ACCESS_KEY_ID")
    secret = os.getenv("AWS_SECRET_ACCESS_KEY")
    if key and secret:
        kwargs["aws_access_key_id"] = key
        kwargs["aws_secret_access_key"] = secret
    return boto3.client("bedrock-runtime", **kwargs)


MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "amazon.nova-micro-v1:0")

TOOL_CONFIG = {
    "tools": [
        {
            "toolSpec": {
                "name": "get_current_weather",
                "description": (
                    "Retrieves the current real-time weather conditions for a given city or location. "
                    "Use this when the user asks about current weather, temperature, humidity, wind, "
                    "UV index, or any 'right now' / 'today' weather question."
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": (
                                    "The city or location name to get weather for. "
                                    "Examples: 'London', 'New York', 'Tokyo', 'Mumbai', 'Paris, France'."
                                ),
                            }
                        },
                        "required": ["location"],
                    }
                },
            }
        },
        {
            "toolSpec": {
                "name": "get_weather_forecast",
                "description": (
                    "Retrieves a multi-day weather forecast (1 to 7 days) for a given city or location. "
                    "Use this when the user asks about future weather, upcoming days, weekly forecast, "
                    "planning for an event, or compares multiple future days."
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": (
                                    "The city or location name to get forecast for. "
                                    "Examples: 'Berlin', 'Sydney', 'São Paulo'."
                                ),
                            },
                            "days": {
                                "type": "integer",
                                "description": (
                                    "Number of days to forecast, between 1 and 7. Defaults to 5 if not specified."
                                ),
                                "minimum": 1,
                                "maximum": 7,
                            },
                        },
                        "required": ["location"],
                    }
                },
            }
        },
    ]
}

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


async def _dispatch_tool(tool_name: str, tool_input: dict[str, Any]) -> Any:
    if tool_name == "get_current_weather":
        return await get_current_weather(tool_input["location"])
    elif tool_name == "get_weather_forecast":
        days = tool_input.get("days", 5)
        return await get_weather_forecast(tool_input["location"], days)
    else:
        return {"error": f"Unknown tool: {tool_name}"}


async def run_agent(user_message: str, conversation_history: list[dict]) -> dict[str, Any]:
    client = _get_bedrock_client()

    messages = list(conversation_history)
    messages.append({"role": "user", "content": [{"text": user_message}]})

    tool_calls_log: list[dict] = []
    max_iterations = 10

    for iteration in range(max_iterations):
        response = client.converse(
            modelId=MODEL_ID,
            system=[{"text": SYSTEM_PROMPT}],
            messages=messages,
            toolConfig=TOOL_CONFIG,
            inferenceConfig={
                "maxTokens": 5000,
                "temperature": 0.3,
            },
        )

        stop_reason = response.get("stopReason", "end_turn")
        assistant_message = response["output"]["message"]
        messages.append(assistant_message)

        if stop_reason == "end_turn":
            final_text = ""
            for block in assistant_message.get("content", []):
                if "text" in block:
                    final_text += block["text"]
            return {
                "text": final_text,
                "tool_calls": tool_calls_log,
                "updated_history": messages,
            }

        elif stop_reason == "tool_use":
            tool_results = []

            for block in assistant_message.get("content", []):
                if "toolUse" not in block:
                    continue

                tool_use = block["toolUse"]
                tool_use_id = tool_use["toolUseId"]
                tool_name = tool_use["name"]
                tool_input = tool_use.get("input", {})

                try:
                    result = await _dispatch_tool(tool_name, tool_input)
                    tool_calls_log.append({
                        "tool": tool_name,
                        "input": tool_input,
                        "result": result,
                        "error": None,
                    })
                    tool_results.append({
                        "toolResult": {
                            "toolUseId": tool_use_id,
                            "content": [{"json": result}],
                        }
                    })
                except Exception as exc:
                    error_msg = str(exc)
                    tool_calls_log.append({
                        "tool": tool_name,
                        "input": tool_input,
                        "result": None,
                        "error": error_msg,
                    })
                    tool_results.append({
                        "toolResult": {
                            "toolUseId": tool_use_id,
                            "content": [{"text": f"Error: {error_msg}"}],
                            "status": "error",
                        }
                    })

            messages.append({"role": "user", "content": tool_results})

        else:
            final_text = ""
            for block in assistant_message.get("content", []):
                if "text" in block:
                    final_text += block["text"]
            return {
                "text": final_text or f"[Agent stopped: {stop_reason}]",
                "tool_calls": tool_calls_log,
                "updated_history": messages,
            }

    return {
        "text": "I reached the maximum number of tool calls. Please try a simpler question.",
        "tool_calls": tool_calls_log,
        "updated_history": messages,
    }
