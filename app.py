from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import random
import json
import grpc
from starlette.websockets import WebSocketDisconnect

import nest_pb2
import nest_pb2_grpc
from queue import Queue
import logging
import asyncio
from threading import Thread
from typing import List
from agent import Agent



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
agent = Agent()

# Get API key from environment variable
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY","")
CLOVA_API_HOST = os.getenv("CLOVA_SPEECH_HOST", "clovaspeech-gw.ncloud.com:50051")
CLOVA_API_KEY = os.getenv("CLOVA_API_KEY")


if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables")
if not CLOVA_API_KEY:
    raise ValueError("CLOVA_API_KEY not found in environment variables")

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_personal_message(self, user_id: str, message: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(message)

    async def send_signal_message(self, peer_id: str, message: str):
        if peer_id in self.active_connections:
            await self.active_connections[peer_id].send_json(message)

    async def broadcast_except_mine(self, peer_id:str, message: str):
        # 전송 주체를 제외한 모든 연결된 클라이언트에게 메시지 전송
        for pId, connection in self.active_connections.items():
            #print("broadCast : ",pId, " send from : " ,peer_id, '/ ','user' not in pId,' / ', pId != peer_id)
            if('user' not in pId and pId != peer_id):
                # print("broadCast : ",pId, " send from : " ,peer_id)
                await connection.send_json(message)

    async def broadcast(self, message: str):
        # 모든 연결된 클라이언트에게 메시지 전송
        for pId, connection in self.active_connections.items():
            await connection.send_text(message)

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
AUDIO_QUEUE_MAXSIZE = 100

connectionManager = ConnectionManager()
global_channel = grpc.secure_channel(
    CLOVA_API_HOST,
    grpc.ssl_channel_credentials()
)
global_stub = nest_pb2_grpc.NestServiceStub(global_channel)
global_metadata = (("authorization", f"Bearer {CLOVA_API_KEY}"),)

# gRPC 요청 생성기 (동기)
def grpc_request_iter(sync_queue: Queue,user_id:str):
    buffer = bytearray()
    # 초기 설정
    yield nest_pb2.NestRequest(
        type=nest_pb2.RequestType.CONFIG,
        config=nest_pb2.NestConfig(
            config=json.dumps({
                "transcription": {"language": "ko"},
                "semanticEpd":{
                    "skipEmptyText":True,
                    "usePeriodEpd":True,
                    "useWordEpd":False
                }
            })
        )
    )
    # with open(f"pcm/{user_id}_audio.pcm", "wb") as f:
    while True:
        data = sync_queue.get()
        if data is None:
            break

        # f.write(data)

        yield nest_pb2.NestRequest(
            type=nest_pb2.RequestType.DATA,
            data=nest_pb2.NestData(
                chunk=bytes(data),
                extra_contents=json.dumps({"seqId": 0, "epFlag": False})
            )
        )

# Thread 내에서 실행될 gRPC 호출 함수
def grpc_stream(sync_queue: Queue, user_id: str):
    global global_stub, global_metadata
    responses = global_stub.recognize(grpc_request_iter(sync_queue,user_id), metadata=global_metadata)

    try:
        for response in responses:
            #print("user_id :", user_id," / response : ",response.contents)
            # send to frontend
            asyncio.run(connectionManager.send_personal_message(user_id,response.contents))
    except Exception as e:
        print("gRPC Error:", e)

# FastAPI WebSocket
@app.websocket("/signal/{peerId}")
async def signal(websocket: WebSocket,peerId:str):
    await connectionManager.connect(peerId, websocket)

    try:
        while True:
            msg = await websocket.receive()
            if("text" in msg):
                data = json.loads(msg["text"])
                if(data["type"] == 'ready' or data["type"] == 'bye'):
                    await connectionManager.send_signal_message(peerId, data)
                else:
                    await connectionManager.broadcast_except_mine(peerId, data)
    except WebSocketDisconnect:
        print("WebSocket disconnected")
        connectionManager.disconnect(peerId)


@app.websocket("/ws/stt/{user_id}")
async def stt_ws(websocket: WebSocket, user_id: str):
    await connectionManager.connect(user_id, websocket)
    global global_channel

    async_audio_queue = asyncio.Queue()
    sync_audio_queue = Queue(maxsize=AUDIO_QUEUE_MAXSIZE)

    print("userID: ", user_id)
    grpc_thread = Thread(target=grpc_stream, args=(sync_audio_queue, user_id))
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
        global_channel.close()
        connectionManager.disconnect(user_id)

@app.get("/agent/{query}")
async def agent_answer(query:str):
    # 1
    # query에 대한 Lang Graph 기반 에이전트
    # 상태 기반 워크플로우 구현
    # 도구 연계 및 의사결정 로직
    # Human-in-the-loop 또는 적응형 처리

    # 2
    # query에 대한 고도화된 RAG agent
    # Adaptive RAG, Self-RAG, CRAG 중 하나 이상
    # 검색 전략 최적화
    # 동적 정보 처리
    try:
        print('agent query: ',query)
        global agent
        response = agent.getAnswer(query)
        print('agent response: ',response)
        return JSONResponse(
            status_code=200,
            content={
                "answer": response.get('final_response'),
                "sources": [
                    {
                        "url": doc.metadata.get("url", ""),
                        "title": doc.metadata.get("source", "")
                    }
                    for doc in response.get("retrieved_documents", [])
                ]
            }
        )
    # except httpx.HTTPStatusError as e:
    #     return JSONResponse(status_code=e.response.status_code, content={"error": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "Internal Server Error", "details": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888, ssl_keyfile="key.pem", ssl_certfile="cert.pem")
