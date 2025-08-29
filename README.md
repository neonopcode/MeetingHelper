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
질문: 사내 패키지를 메이븐이랑 npm으로 구축해야 OSS 종속성 안정성을 확보할 수 있을 것 같습니다. W3C 표준 API 가이드라인에 맞춰야 장기적인 호환성도 담보되겠죠
======================================================================================================================================================

llm select tool :  [{'name': 'search_softwareTerm', 'args': {'self': {}, 'query': 'Json Web Token (JWT)'}, 'id': 'call_YeGYbxTwcDlrDePZwHgcJehS', 'type': 'tool_call'}, {'name': 'search_softwareTerm', 'args': {'self': {}, 'query': '세션 관리'}, 'id': 'call_qHGIiJM9JJpWuIr8M6ioQiCG', 'type': 'tool_call'}]
search using this tool :  search_softwareTerm

전략: single_lookup
전략 선택 이유: {'reason': '사내 패키지를 메이븐과 npm으로 구축하는 것은 각각 Java와 JavaScript 생태계에서의 패키지 관리 방법에 관한 내용이며, W3C 표준 API 가이드라인과의 연관성기 때문입니다.'}

======================================================================================================================================================
최종 응답:
질문에서 제시한 내용은 사내 패키지 관리 시스템을 Maven과 npm으로 구축하여 오픈소스 소프트웨어(OSS) 종속성의 안정성을 확보하고, W3C 표준 API 가이드라인을 준수함으로써 장기적인 호환성을 보장하려는 의도로 보입니다.

컨텍스트에 따르면, npm과 Maven은 각각의 언어 및 생태계에 맞는 패키지 기반 시스템으로, 중앙의 패키징 권한자(예: npmjs.org, Maven 중앙 저장소)를 통해 패키지의 버전 관리와 배포가  패키지를 설치하고 관리할 수 있도록 돕습니다. 다만, Maven과 같은 시스템은 여러 호스팅 사이트가 존재할 수 있어, 특정 뷰에서는 전체 패키지의 일부만 볼 수 있는 경우도 있습니다.

또한, 패키지 기반 시스템은 버전 지정과 요구사항 명세를 정의하는 규칙을 포함하며, 이를 통해 패키지의 상태를 관리합니다. 따라서 사내에서 Maven과 npm을 활용해 패키지 관리 체계를 구축하면, 각각의 생태계에 맞는 중앙 권한자를 통해 패키지의 안정적인 배포와 버전 관리를 할 수 있습니다.

W3C 표준 API 가이드라인을 따른다는 것은, 패키지나 API 설계 시 웹 표준을 준수하여 향후 웹 기술 변화에도 호환성을 유지할 수 있도록 하는 것을 의미합니다. 이는 장기적인 유지보수와 상호운용성 측면에서 긍정적인 영향을 줄 수 있습니다.

요약하면, Maven과 npm을 활용한 패키지 관리 시스템 구축은 OSS 종속성의 안정성 확보에 도움이 되며, W3C 표준 API 가이드라인 준수는 장기적인 호환성 보장에 기여할 수 있다는 점을 컨텍스트에서 확인할 수 있습니다.

[출처: Glossary | Open Source Insights / data/Dev/Glossary_OpenSourceInsights.pdf]

======================================================================================================================================================
