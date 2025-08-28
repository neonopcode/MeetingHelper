// UI Management

class UI {
    static elements = {
        isOpenAgentPanel : false,
        startButton: document.getElementById('startButton'),
        stopButton: document.getElementById('stopButton'),
        panel : document.getElementById('scriptPanel'),
        panelButton : document.getElementById('togglePanel'),
        transcript: document.getElementById('transcript'),
        status: document.getElementById('status'),
        error: document.getElementById('error'),
        imageContainer: document.getElementById('imageContainer'),
        localView : document.getElementById('localView'),
        remoteView : document.getElementById('remoteView'),
        agentPanel : document.getElementById('agentPanel'),
        agentPanelContent : document.getElementById('panelContent'),
        answerText : document.getElementById('answerText'),
        // sourceLinks : document.getElementById('sources'),
        typing : document.getElementById('typingIndicator'),
        copyBtn : document.getElementById('copyBtn'),
        closeBtn : document.getElementById('closeBtn'),
        contentWrapper: document.querySelector('.content-wrapper')
    };

    static updateStatus(message) {
        this.elements.status.textContent = message;
    }

    static showError(message) {
        this.elements.error.style.display = 'block';
        this.elements.error.textContent = message;
    }

    static hideError() {
        this.elements.error.style.display = 'none';
    }


    static openAgentPanel() {
        this.elements.agentPanel.classList.add('open');
        this.elements.agentPanel.setAttribute('aria-hidden','false');
        this.elements.typing.style.display='flex';
    }

    static async sendQueryAgent(query){
        try {
            const agentResponse = await MessageHandler.handelAgentFunction(query);
            // console.log('agentResponse : ', agentResponse)
            if(agentResponse){
                this.elements.answerText.style.display='block';
                this.updateAgentPanel(agentResponse);
                // 복사 버튼
                this.elements.copyBtn.addEventListener('click', () => {
                    //@Todo copy answers
                });
            }
        } catch(err){
            this.elements.answerText.textContent = `에러 발생: 응답을 불러오지 못했습니다.${err}`;
            this.elements.answerText.style.display='block';
        } finally {
            this.elements.typing.style.display='none';
        }
    }

    static closeAgentPanel() {
        this.elements.agentPanel.classList.remove('open');
        this.elements.agentPanel.setAttribute('aria-hidden','true');
        this.elements.isOpenAgentPanel = false;
        //초기화
        this.elements.typing.style.display='none';
        this.elements.answerText.style.display='none';
    }

    static updateAgentPanel(res) {
        const bubble = document.createElement("div");
        bubble.classList.add("chat-bubble");
        const bubbleDirection = "remote";
        bubble.classList.add(bubbleDirection);

        const answerDiv = document.createElement("div");
        answerDiv.innerText = res.answer;
        bubble.appendChild(answerDiv);

        // 출처 렌더링
        if(res.sources && res.sources.length){
            function escapeHtml(s){
                return s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
            }

            const sourcesDiv = document.createElement("div");
            sourcesDiv.innerHTML = res.sources.map(s => `• <a href="${s.url}" style="color:#0b1220;text-decoration:underline">${escapeHtml(s.title)}</a>`).join('<br>');
            bubble.appendChild(sourcesDiv);
        }
        // console.log('updateAgentPanel: ',res)

        if (this.elements.answerText.firstChild) {
            this.elements.answerText.insertBefore(bubble, this.elements.answerText.firstChild);
        } else {
            this.elements.answerText.appendChild(bubble);
        }
    }

    static updateTranscript(message, isLocalRes) {
        const bubble = document.createElement("div");
        bubble.classList.add("chat-bubble");
        const bubbleDirection = isLocalRes ? "local" : "remote";
        bubble.classList.add(bubbleDirection);
        bubble.textContent = message;

        bubble.addEventListener("click", () => {
            console.log(`Clicked sentence: ${message}`);
            bubble.classList.toggle("active");
            //agent Panel open
            if(!this.elements.isOpenAgentPanel) {
                this.openAgentPanel();
                this.elements.isOpenAgentPanel = true;
            }
            //send query to AI agent
            this.sendQueryAgent(message);
        });

        if (this.elements.transcript.firstChild) {
            this.elements.transcript.insertBefore(bubble, this.elements.transcript.firstChild);
        } else {
            this.elements.transcript.appendChild(bubble);
        }
    }

    static updateButtons(isConnected) {
        this.elements.startButton.disabled = isConnected;
        this.elements.stopButton.disabled = !isConnected;
    }
}

// Error Handler
class ErrorHandler {
    static handle(error, context) {
        console.error(`Error in ${context}:`, error);
        UI.showError(`Error ${context}: ${error.message}`);
    }
}

// Message Handler
class MessageHandler {
    static async handleTranscript(message, isLocalRes) {
        const transcript = message.transcription.text//message.response?.output?.[0]?.content?.[0]?.transcript;
        if (transcript != " ") {
            UI.updateTranscript(transcript, isLocalRes);
        }
    }

    static async handelAgentFunction(query){
        try {
            const response = await fetch(`${CONFIG.API_ENDPOINTS.agent}/${query}`);
            const data = await response.json();
            return data;
        }catch (e) {
            console.error("No AI agent Response");
        }
    }
}

// WebRTC Manager
class WebRTCManager {
    constructor(app) {
        this.peerConnection = null;
        this.localStream = null;
        this.remoteStream = null;
        function generateUserId(isLocal) {
            if(isLocal)
                return 'user_local' + crypto.randomUUID();
            return 'user_remote' + crypto.randomUUID();
        }

        this.peerId = crypto.randomUUID();

        this.localSTT = new STTHandler(generateUserId(true),true);
        this.remoteSTT = new STTHandler(generateUserId(false),false);

        this.signaling = new WebSocket(`${CONFIG.API_ENDPOINTS.signaling}/${this.peerId}`)//new BroadcastChannel('webrtc');
        this.signaling.onopen = () => {
        }
        this.signaling.onmessage = async (e) => {
            const data = JSON.parse(e.data);
            console.log("☎️ signalMessage : ", data)
            if (!this.localStream) {
                console.log('not ready yet');
                return;
            }
            switch (data.type) {
                case 'offer':
                    this.handleOffer(data);
                    break;
                case 'answer':
                    this.handleAnswer(data);
                    break;
                case 'candidate':
                    this.handleCandidate(data);
                    break;
                case 'ready':
                    // A second tab joined. This tab will initiate a call unless in a call already.
                    if (this.peerConnection) {
                        console.log('already in call, ignoring');
                        return;
                    }
                    this.makeCall();
                    break;
                case 'bye':
                    if (this.peerConnection) {
                        this.hangup();
                    }
                    break;
                default:
                    console.log('unhandled', e);
                    break;
            }
        };
        this.app = app;  // Store reference to the app
    }

    async setupLocal() {
        this.localStream = await navigator.mediaDevices.getUserMedia({ audio: {
            echoCancellation: false,
            noiseSuppression: true,
            voiceIsolation: false,
            autoGainControl: false
        }, video: true});
        if (this.localStream) {
            if(this.localSTT)
                this.localSTT.handleTranscript(this.localStream);
            UI.elements.localView.srcObject = this.localStream;
        }
    }

    async createPeerConnection(){
        this.peerConnection = new RTCPeerConnection();
        this.peerConnection.onicecandidate = e => {
            if (e.candidate) {
                const message = {
                    type: 'candidate',
                    candidate: e.candidate.candidate,
                    sdpMid: e.candidate.sdpMid,
                    sdpMLineIndex: e.candidate.sdpMLineIndex
                };
                this.signaling.send(JSON.stringify(message));
            }else{
                console.log("☎️ candidates? ",e)
            }
        };
        this.peerConnection.ontrack = async e => {
            this.remoteStream = e.streams[0];
            // console.log("remote stream!")
            if(this.remoteStream) {
                if(this.remoteSTT)
                    this.remoteSTT.handleTranscript(this.remoteStream);
                UI.elements.remoteView.srcObject = this.remoteStream;
            }
        }

        if(this.localStream)
            this.localStream.getTracks().forEach(track =>
                this.peerConnection.addTrack(track, this.localStream)
            );
    }

    start(){
        // this.signaling.postMessage({type: 'ready'});
        this.signaling.send(JSON.stringify({type: 'ready'}));
    }

    stop(){
        // this.signaling.postMessage({type: 'bye'});
        this.signaling.send(JSON.stringify({type: 'bye'}));
    }

    async makeCall() {
        console.log("☎️ makeCall")
        await this.createPeerConnection();
        console.log("☎️ createOffer")
        const offer = await this.peerConnection.createOffer();
        this.signaling.send(JSON.stringify({type: 'offer', sdp: offer.sdp}));
        await this.peerConnection.setLocalDescription(offer);
    }

    async hangup() {
        if (this.peerConnection) {
            this.peerConnection.close();
            this.peerConnection = null;
        }
        this.localStream.getTracks().forEach(track => track.stop());
        this.localStream = null;
        if(this.localSTT)
            this.localSTT.stop();
        if(this.remoteSTT)
            this.remoteSTT.stop();
    };

    async handleOffer(offer) {
        // if (this.peerConnection) {
        //     console.error('existing peerconnection');
        //     return;
        // }
        if (!this.peerConnection)
            await this.createPeerConnection();
        console.log("☎️ handleOffer")
        await this.peerConnection.setRemoteDescription(offer);

        const answer = await this.peerConnection.createAnswer();
        this.signaling.send(JSON.stringify({type: 'answer', sdp: answer.sdp}));
        await this.peerConnection.setLocalDescription(answer);
    }

    async handleAnswer(answer) {
        if (!this.peerConnection) {
            console.error('no peerconnection');
            return;
        }
        console.log("☎️ handleAnswer")
        await this.peerConnection.setRemoteDescription(answer);
    }

    async handleCandidate(candidate) {
        if (!this.peerConnection) {
            console.error('no peerconnection');
            return;
        }
        if (!candidate.candidate) {
            await this.peerConnection.addIceCandidate(null);
        } else {
            await this.peerConnection.addIceCandidate(candidate);
        }
    }

    cleanup() {
        if (this.peerConnection) {
            this.peerConnection.close();
            this.peerConnection = null;
        }
        if (this.audioStream) {
            this.audioStream.getTracks().forEach(track => track.stop());
            this.audioStream = null;
        }
        if (this.dataChannel) {
            this.dataChannel.close();
            this.dataChannel = null;
        }
        if(this.localSTT)
            this.localSTT.stop();
        if(this.remoteSTT)
            this.remoteSTT.stop();
    }
}


class STTHandler {
    constructor(user_id, isLocal) {
        //import websocket
        this.ws = new WebSocket(`${CONFIG.API_ENDPOINTS.transcribe}/${user_id}`);
        this.ws.binaryType = 'arraybuffer';
        this.ws.onopen = () => {
        }
        this.ws.onmessage = async (ev) => {
            try {
                const data = JSON.parse(ev.data);
                const res_type = data.responseType[0];
                if (res_type == "transcription") {
                    // 기본 정보 출력
                    const text = data.transcription.text
                    const position = data.transcription.position
                    const seqId = data.transcription.seqId
                    const epdType = data.transcription.epdType

                    if(text) {
                        await MessageHandler.handleTranscript(data, this.isLocalRes);
                    }
                }
            } catch {
                // 텍스트 외 바이너리 응답은 없음
            }
        };
        this.ws.onclose = () => {
        };
        this.userId = 0;
        this.audioCtx = null;
        this.processor = null;
        this.source = null;
        this.isLocalRes = isLocal
        this.processedBuffers = [];
    }

    handleTranscript(stream) {
        try {
            this.audioCtx = new (window.AudioContext || window.webkitAudioContext)({sampleRate: 16000});

            // 오디오 스트림을 AudioContext에 연결
            this.source = this.audioCtx.createMediaStreamSource(stream);

            // ScriptProcessorNode 생성 (buffer size: 16384, mono: 1) 32000 Byte
            this.processor = this.audioCtx.createScriptProcessor(16384, 1, 1);

            // 오디오 데이터가 들어올 때마다 호출됨
            this.processor.onaudioprocess = (e) => {
                const inputData = e.inputBuffer.getChannelData(0); // float32 PCM

                //Float32Array -> Int16Array 변환 (STT 서버용)
                const int16Data = floatTo16BitPCM(inputData);

                function floatTo16BitPCM(float32Array) {
                    const buffer = new ArrayBuffer(float32Array.length * 2);
                    const view = new DataView(buffer);
                    let offset = 0;
                    for (let i = 0; i < float32Array.length; i++, offset += 2) {
                        let s = Math.max(-1, Math.min(1, float32Array[i]));
                        view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
                    }
                    return buffer;
                }

                this.processedBuffers.push(int16Data);

                if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                    this.ws.send(int16Data);
                }
            };
            this.source.connect(this.processor);
            this.processor.connect(this.audioCtx.destination);
        } catch (e) {
            console.log('🚨', e)
        }
    }

    downloadProcessedWav() {
        const merged = this.mergeBuffers(this.processedBuffers);
        const wavBlob = this.encodeWav(merged, 16000);
        const url = URL.createObjectURL(wavBlob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `local_${this.isLocalRes}_processed.wav`;
        a.click();
    }

    mergeBuffers(buffers) {
        let length =0;
        let offset =0;
        for (const b of buffers) {
            length += b.length;
        }
        let merged = new Int16Array(length);
        for (const b of buffers) {
            merged.set(b, offset);
            offset += b.length;
        }
        return merged;
    }

    encodeWav(samples, sampleRate) {
        const buffer = new ArrayBuffer(44 + samples.length * 2);
        const view = new DataView(buffer);

        function writeString(view, offset, str) {
            for (let i = 0; i < str.length; i++) {
                view.setUint8(offset + i, str.charCodeAt(i));
            }
        }

        writeString(view, 0, "RIFF");
        view.setUint32(4, 36 + samples.length * 2, true);
        writeString(view, 8, "WAVE");
        writeString(view, 12, "fmt ");
        view.setUint32(16, 16, true); // Subchunk1Size
        view.setUint16(20, 1, true);  // AudioFormat = PCM
        view.setUint16(22, 1, true);  // NumChannels
        view.setUint32(24, sampleRate, true);
        view.setUint32(28, sampleRate * 2, true); // byte rate
        view.setUint16(32, 2, true); // block align
        view.setUint16(34, 16, true); // bits/sample
        writeString(view, 36, "data");
        view.setUint32(40, samples.length * 2, true);

        for (let i = 0; i < samples.length; i++) {
            view.setInt16(44 + i * 2, samples[i], true);
        }

        return new Blob([view], {type: "audio/wav"});
    }


    stop(){
        //this.downloadProcessedWav();
        this.ws.close(1000, "user stopped streaming");
        this.processor.disconnect();
        this.source.disconnect();
        this.processor = null;
        this.source = null;
    }
}

// Main Application
class App {
    constructor() {
        //this.webrtc = null;
        this.bindEvents();
        this.webrtc = new WebRTCManager(this);
    }

    bindEvents() {
        //Call start
        UI.elements.startButton.addEventListener('click', () => this.init());
        //Call stop
        UI.elements.stopButton.addEventListener('click', () => this.stop());
        //Open Script Panel
        UI.elements.panelButton.addEventListener('click', () => UI.elements.panel.classList.toggle("open"));
        //Close AI agent Panel
        UI.elements.closeBtn.addEventListener('click',()=> UI.closeAgentPanel());
        document.addEventListener('DOMContentLoaded', () => {
            UI.updateStatus('Ready to start');
        });
    }

    async init() {
        UI.elements.startButton.disabled = true;
        
        try {
            UI.updateStatus('Initializing...');
            await this.webrtc.setupLocal();
            this.webrtc.start();
            UI.updateStatus('Connected');
            UI.updateButtons(true);
            UI.hideError();

        } catch (error) {
            UI.updateButtons(false);
            ErrorHandler.handle(error, 'Initialization');
            UI.updateStatus('Failed to connect');
        }
    }

    stop() {
        if (this.webrtc) {
            this.webrtc.stop();
            this.webrtc.cleanup();
            this.webrtc = null;
        }
        UI.updateButtons(false);
        UI.updateStatus('Ready to start');
    }
}

// Initialize the application
const app = new App(); 