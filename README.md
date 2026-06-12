# WeatherAI — AWS Bedrock Tool-Calling Agent

A full-stack weather chatbot powered by **AWS Bedrock (Amazon Nova Micro)** with real tool-calling capabilities.

## Architecture

```
Frontend (HTML/CSS/JS)  ──►  FastAPI Backend  ──►  AWS Bedrock (Nova Micro)
                                                         │
                                           ┌─────────────┴──────────────┐
                                           │  get_current_weather        │
                                           │  get_weather_forecast       │
                                           └─────────────┬──────────────┘
                                                         │
                                                   Open-Meteo API (free)
```

## Project Structure

```
demo-ai/
├── backend/
│   ├── main.py           # FastAPI app + /chat endpoint
│   ├── bedrock_agent.py  # Bedrock converse loop + tool schemas
│   ├── weather_tools.py  # get_current_weather + get_weather_forecast
│   ├── requirements.txt
│   └── .env.example      # Copy to .env and fill credentials
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── start.bat             # Windows quick-start script
└── README.md
```

## Setup

### 1. AWS Credentials

You need AWS credentials with Bedrock access (`bedrock:InvokeModel` permission).

**Option A — AWS CLI (recommended)**
```bash
aws configure
# Enter your Access Key ID, Secret Access Key, region (e.g. us-east-1)
```

**Option B — .env file**
```bash
cd backend
copy .env.example .env
# Edit .env with your credentials
```

### 2. Enable Bedrock Model Access

1. Go to [AWS Bedrock Console](https://console.aws.amazon.com/bedrock)
2. Navigate to **Model access**
3. Enable **Amazon Nova Micro** (Amazon)

### 3. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 4. Run the Backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Or simply double-click **`start.bat`** in the project root.

### 5. Open the Frontend

Open `frontend/index.html` in your browser.

> ℹ️ No build step needed — it's plain HTML/JS!

## Tools

| Tool | Description |
|------|-------------|
| `get_current_weather` | Real-time weather: temp, humidity, wind, UV, pressure |
| `get_weather_forecast` | 1–7 day daily forecast with rain probability |

## Example Queries

- *"What's the weather in Paris right now?"*
- *"Give me a 7-day forecast for Tokyo"*
- *"Compare weather in London and New York"*
- *"Is it going to rain in Berlin this week?"*
- *"What's the UV index in Sydney and do I need sunscreen?"*

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/health` | Health check |
| `POST` | `/chat` | Send message to agent |
| `DELETE` | `/chat/{session_id}` | Clear session |
| `GET`  | `/docs` | Swagger UI |

## Notes

- Weather data from [Open-Meteo](https://open-meteo.com/) — free, no API key required
- Nova decides which tool(s) to call based on your question
- Multiple tool calls supported (e.g., comparing two cities)
