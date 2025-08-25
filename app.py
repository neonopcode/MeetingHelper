from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
import random
import json
import grpc
import nest_pb2
import nest_pb2_grpc
from queue import Queue
import logging
import asyncio
from threading import Thread


# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Example usage of logger
logger.info("Logging is set up.")


app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load environment variables
load_dotenv(override=True)


# Get API key from environment variable
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
REALTIME_SESSION_URL = os.getenv("REALTIME_SESSION_URL")
API_HOST = os.getenv("CLOVA_SPEECH_HOST", "clovaspeech-gw.ncloud.com:50051")
CLOVA_API_KEY = os.getenv("CLOVA_API_KEY")

# this is the openai url: https://api.openai.com/v1/realtime/sessions
logger.info(f"REALTIME_SESSION_URL: {REALTIME_SESSION_URL}")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables")
# if not SERPER_API_KEY:
#     raise ValueError("SERPER_API_KEY not found in environment variables")
if not REALTIME_SESSION_URL:
    raise ValueError("REALTIME_SESSION_URL not found in environment variables")

class SessionResponse(BaseModel):
    session_id: str
    token: str

class WeatherResponse(BaseModel):
    temperature: float
    humidity: float
    precipitation: float
    wind_speed: float
    unit_temperature: str = "celsius"
    unit_precipitation: str = "mm"
    unit_wind: str = "km/h"
    forecast_daily: list
    current_time: str
    latitude: float
    longitude: float
    location_name: str
    weather_code: int

class SearchResponse(BaseModel):
    title: str
    snippet: str
    source: str
    image_url: str | None = None
    image_source: str | None = None

CHUNK_SIZE = 32000
AUDIO_QUEUE_MAXSIZE = 100  # optional

# gRPC 요청 생성기 (동기)
def grpc_request_iter(sync_queue: Queue):
    buffer = bytearray()
    # 초기 설정
    yield nest_pb2.NestRequest(
        type=nest_pb2.RequestType.CONFIG,
        config=nest_pb2.NestConfig(
            config=json.dumps({"transcription": {"language": "ko"}})
        )
    )

    while True:
        data = sync_queue.get()
        if data is None:
            if buffer:
                print("no more data  : ",len(buffer))
                yield nest_pb2.NestRequest(
                    type=nest_pb2.RequestType.DATA,
                    data=nest_pb2.NestData(
                        chunk=bytes(buffer),
                        extra_contents=json.dumps({"seqId": 0, "epFlag": True})
                    )
                )
            break

        buffer.extend(data)
        # print("add data : ",len(buffer)) #+ 32768
        while len(buffer) >= CHUNK_SIZE:
            chunk = buffer[:CHUNK_SIZE]
            buffer = buffer[CHUNK_SIZE:]
            yield nest_pb2.NestRequest(
                type=nest_pb2.RequestType.DATA,
                data=nest_pb2.NestData(
                    chunk=bytes(chunk),
                    extra_contents=json.dumps({"seqId": 0, "epFlag": False})
                )
            )

# Thread 내에서 실행될 gRPC 호출 함수
def grpc_stream(sync_queue: Queue, websocket: WebSocket):
    channel = grpc.secure_channel(
        API_HOST,
        grpc.ssl_channel_credentials()
    )
    stub = nest_pb2_grpc.NestServiceStub(channel)
    metadata = (("authorization", f"Bearer {CLOVA_API_KEY}"),)
    responses = stub.recognize(grpc_request_iter(sync_queue), metadata=metadata)

    try:
        for response in responses:
            # print("stt Response:", response.contents)
            asyncio.run(websocket.send_text(response.contents))  # send to frontend
    except Exception as e:
        print("gRPC Error:", e)
    finally:
        print("channel close")
        channel.close()

# FastAPI WebSocket
@app.websocket("/ws/stt")
async def stt_ws(websocket: WebSocket):
    await websocket.accept()

    async_audio_queue = asyncio.Queue()
    sync_audio_queue = Queue(maxsize=AUDIO_QUEUE_MAXSIZE)

    # 🧵 gRPC thread 실행
    grpc_thread = Thread(target=grpc_stream, args=(sync_audio_queue, websocket))
    grpc_thread.start()

    # 두 큐를 이어주는 비동기 → 동기 브릿지
    async def bridge_async_to_sync():
        while True:
            item = await async_audio_queue.get()
            sync_audio_queue.put(item)
            if item is None:
                break

    bridge_task = asyncio.create_task(bridge_async_to_sync())

    try:
        while True:
            msg = await websocket.receive()
            if "bytes" in msg:
                await async_audio_queue.put(msg["bytes"])
            elif msg["type"] == 'websocket.disconnect':
                print("Non-binary message:", msg)
                break
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    finally:
        await async_audio_queue.put(None)
        await bridge_task
        grpc_thread.join()


@app.get("/session")
async def get_session(voice: str = "echo"):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                REALTIME_SESSION_URL,
                headers={
                    'Authorization': f'Bearer {OPENAI_API_KEY}',
                    'Content-Type': 'application/json'
                },
                json={
                    "model": "gpt-4o-realtime-preview",
                    "voice": voice,
                    "instructions": """
                    You are a helpful assistant that can answer questions and help with tasks.
                    You have access to real-time weather data and web search capabilities.
                    When asked about the weather, provide the current temperature and humidity. Provide more information when asked.
                    When asked about a forecast, provide it but say ranging from x to y degrees over the days.
                    Never answer in markdown format. Plain text only with no markdown.
                    """
                }
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error occurred: {e.response.status_code}")
        return JSONResponse(status_code=e.response.status_code, content={"error": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "Internal Server Error", "details": str(e)})

@app.get("/weather/{location}")
async def get_weather(location: str):
    try:
        async with httpx.AsyncClient() as client:
            # Get coordinates for location
            geocoding_response = await client.get(
                f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1"
            )
            geocoding_data = geocoding_response.json()
            
            if not geocoding_data.get("results"):
                return {"error": f"Could not find coordinates for {location}"}
                
            lat = geocoding_data["results"][0]["latitude"]
            lon = geocoding_data["results"][0]["longitude"]
            location_name = geocoding_data["results"][0]["name"]
            
            # Get weather data with more parameters
            weather_response = await client.get(
                f"https://api.open-meteo.com/v1/forecast"
                f"?latitude={lat}&longitude={lon}"
                f"&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code"
                f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code"
                f"&timezone=auto"
                f"&forecast_days=7"
            )
            weather_data = weather_response.json()
            
            # Extract current weather
            current = weather_data["current"]
            daily = weather_data["daily"]
            
            # Create daily forecast array
            forecast = []
            for i in range(len(daily["time"])):
                forecast.append({
                    "date": daily["time"][i],
                    "max_temp": daily["temperature_2m_max"][i],
                    "min_temp": daily["temperature_2m_min"][i],
                    "precipitation": daily["precipitation_sum"][i],
                    "weather_code": daily["weather_code"][i]
                })
            
            return WeatherResponse(
                temperature=current["temperature_2m"],
                humidity=current["relative_humidity_2m"],
                precipitation=current["precipitation"],
                wind_speed=current["wind_speed_10m"],
                forecast_daily=forecast,
                current_time=current["time"],
                latitude=lat,
                longitude=lon,
                location_name=location_name,
                weather_code=current["weather_code"]
            )
            
    except Exception as e:
        logger.error(f"Error getting weather data: {str(e)}")
        return JSONResponse(status_code=500, content={"error": f"Could not get weather data: {str(e)}"})


@app.get("/agent/{query}")
async def agent_answer(query:str):
    async with httpx.AsyncClient() as client:
            response = await client.post(
                REALTIME_SESSION_URL,
                headers={
                    'Authorization': f'Bearer {OPENAI_API_KEY}',
                    'Content-Type': 'application/json'
                },
                json={
                    "model": "gpt-4o-mini",
                    "voice": voice,
                    "instructions": """
                        You are a helpful assistant that can answer questions and help with tasks.
                        You have access to real-time weather data and web search capabilities.
                        When asked about the weather, provide the current temperature and humidity. Provide more information when asked.
                        When asked about a forecast, provide it but say ranging from x to y degrees over the days.
                        Never answer in markdown format. Plain text only with no markdown.
                        """
                }
            )
            response.raise_for_status()
            return response.json()
    # except httpx.HTTPStatusError as e:
    #     logger.error(f"HTTP error occurred: {e.response.status_code}")
    #     return JSONResponse(status_code=e.response.status_code, content={"error": str(e)})
    # except Exception as e:
    #     return JSONResponse(status_code=500, content={"error": "Internal Server Error", "details": str(e)})

@app.get("/search/{query}")
async def search_web(query: str):
    try:
        async with httpx.AsyncClient() as client:
            # Get regular search results
            response = await client.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": SERPER_API_KEY},
                json={"q": query}
            )
            
            data = response.json()
            
            # Get image search results with larger size
            image_response = await client.post(
                "https://google.serper.dev/images",
                headers={"X-API-KEY": SERPER_API_KEY},
                json={
                    "q": query,
                    "gl": "us",
                    "hl": "en",
                    "autocorrect": True
                }
            )
            
            image_data = image_response.json()
            
            if "organic" in data and len(data["organic"]) > 0:
                result = data["organic"][0]  # Get the first result
                image_result = None
                
                # Find first valid image
                if "images" in image_data:
                    for img in image_data["images"]:
                        if img.get("imageUrl") and (
                            img["imageUrl"].endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')) or 
                            'images' in img["imageUrl"].lower()
                        ):
                            image_result = img
                            break
                
                return SearchResponse(
                    title=result.get("title", ""),
                    snippet=result.get("snippet", ""),
                    source=result.get("link", ""),
                    image_url=image_result["imageUrl"] if image_result else None,
                    image_source=image_result["source"] if image_result else None
                )
            else:
                return {"error": "No results found"}
                
    except Exception as e:
        logger.error(f"Error performing search: {str(e)}")
        return JSONResponse(status_code=500, content={"error": f"Could not perform search: {str(e)}"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)
