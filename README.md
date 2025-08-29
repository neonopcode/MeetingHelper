# Real-time Meeting Helper Demo

An advanced RAG agent with LangGraph + LangChain 
— a demo/production template where clicking a speech bubble in a WebRTC video/audio call triggers context-aware Retrieval → Generation, shown in a user-friendly UI.

**Notes:** 

- The overall structure and code framework of this repository were inspired by[OpenAI Real-time WebRTC Demo](https://github.com/gbaeke/realtime-webrtc.git).
  We would like to express our gratitude to the authors and the open source community for sharing their work.

Check .env.example for an example .env file.


## Features

- Real-time video/audio streaming
- Live transcription
- AI agent helps conferences run smoothly
- WebRTC communication
- FastAPI backend to get a STT response & agent answer

## Setup

1. Clone the repository
2. Create a virtual environment: `python -m venv .venv`
3. Activate it: 
   - Windows: `.venv\Scripts\activate`
   - Unix/macOS: `source .venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Create `.env` file based on `.env.example`
6. Create `.data/Dev` folder including Dev helper Documents (PDF)
7. Modify address to your localIP in `config.js` 



Notes: 

- This is 
- Go to https://openai.com and get your API key.
- Go to https://api.ncloud-docs.com/docs/ai-application-service-clovaspeech-grpc and get your API key.


## Running

1. Start server: `python app.py` (Local Server)
2. Open index.html in a browser or Open https://neonopcode.github.io/MeetingHelper/
3. Click Start and allow microphone & camera access
4. Click Script Button and See transcriptions in real time
5. Click a speech bubble to see the AI agent’s description


## Files

- app.py: FastAPI backend server
- agent.py: AI agent (DevChat helper)
- dataLoader.py : save DB
- index.html: Frontend interface
- config.js: Configuration for the frontend
- app.js: Frontend logic
- requirements.txt: Python dependencies
- .env: Environment variables (create this)