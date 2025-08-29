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

## AI agent Output

======================================================================================================================================================
질문: 이번에는 Json Web Token를 사용하여 세션 관리를 구현할 예정입니다
======================================================================================================================================================

llm select tool :  [{'name': 'search_softwareTerm', 'args': {'self': {}, 'query': 'Json Web Token (JWT)'}, 'id': 'call_YeGYbxTwcDlrDePZwHgcJehS', 'type': 'tool_call'}, {'name': 'search_softwareTerm', 'args': {'self': {}, 'query': '세션 관리'}, 'id': 'call_qHGIiJM9JJpWuIr8M6ioQiCG', 'type': 'tool_call'}]
search using this tool :  search_softwareTerm

전략: single_lookup
전략 선택 이유: {'reason': 'Json Web Token (JWT) 관련 개념과 세션 관리 구현 방법에 대해 현직 개발자에게 정확한 설명을 제공하기 위해 JWT의 기본 구조와 사용법을 한 번 검색하여 최신 표준과 모범 사례를 참고하는 것이 적절하다.'}

======================================================================================================================================================
최종 응답:
Json Web Token(JWT)을 사용하여 세션 관리를 구현한다는 것은 서버가 클라이언트의 인증 상태를 유지하기 위해 JWT를 활용한다는 의미입니다. JWT는 JSON 형식의 데이터를 안전하게 전송하습니다.

세션 관리에서 JWT를 사용하면 서버가 별도의 세션 저장소를 유지하지 않고도 클라이언트가 보낸 토큰을 검증하여 인증 상태를 확인할 수 있습니다. JWT는 보통 세 부분으로 구성되며, 헤더d), 서명(Signature)으로 나뉩니다. 페이로드에는 사용자 정보나 권한 같은 클레임(Claims)이 포함되고, 서명은 토큰의 무결성을 검증하는 데 사용됩니다.

JWT를 사용한 세션 관리는 다음과 같은 절차로 이루어집니다:
1. 사용자가 로그인하면 서버는 사용자 정보를 기반으로 JWT를 생성하여 클라이언트에 전달합니다.
2. 클라이언트는 이후 요청 시 이 JWT를 HTTP 헤더(예: Authorization 헤더)에 포함시켜 서버에 보냅니다.
3. 서버는 받은 JWT의 서명을 검증하고, 유효하면 토큰 내의 정보를 사용해 사용자를 인증합니다.
4. 토큰이 만료되거나 위조된 경우 인증이 실패합니다.

이 방식은 서버의 상태를 유지하지 않는(stateless) 인증 방식을 가능하게 하여 확장성과 성능 측면에서 이점이 있습니다. 다만, 토큰의 보안 관리와 만료 처리, 갱신 전략 등을 신중히 설계해야 합니다.

[출처: Json Web Token 공식 문서, JWT를 활용한 세션 관리 개념]

======================================================================================================================================================
