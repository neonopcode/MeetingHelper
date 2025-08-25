// UI Management

let audioCtx, ws, processor, source;

class UI {
    static elements = {
        startButton: document.getElementById('startButton'),
        stopButton: document.getElementById('stopButton'),
        clearButton: document.getElementById('clearButton'),
        panel : document.getElementById('scriptPanel'),
        panelButton : document.getElementById('togglePanel'),
        transcript: document.getElementById('transcript'),
        status: document.getElementById('status'),
        error: document.getElementById('error'),
        imageContainer: document.getElementById('imageContainer'),
        localView : document.getElementById('localView'),
        remoteView : document.getElementById('remoteView'),
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

    static updateTranscript(message, isLocalRes) {
        const bubble = document.createElement("div");
        bubble.classList.add("chat-bubble");
        const bubbleDirection = isLocalRes ? "local" : "remote";
        bubble.classList.add(bubbleDirection);
        bubble.textContent = message;

        // 클릭 이벤트
        bubble.addEventListener("click", () => {
            console.log(`Clicked sentence: ${message}`);
            bubble.classList.toggle("active"); // 선택 상태 토글
        });

        if (this.elements.transcript.firstChild) {
            this.elements.transcript.insertBefore(bubble, this.elements.transcript.firstChild);
        } else {
            this.elements.transcript.appendChild(bubble);
        }
    }

    static renderTranscript() {
        //const transcriptDiv = document.getElementById("transcript");
        const text = this.elements.transcript.innerText ||this.elements.transcript.textContent;
        this.elements.transcript.innerHTML = ""; // 기존 내용 비우기
        // 단어별로 쪼개기
        const words = text.split(" ");

        words.forEach(word => {
            const span = document.createElement("span");
            span.textContent = word + " ";
            span.classList.add("word");

            // 클릭 이벤트
            span.addEventListener("click", () => {
                alert(`Clicked: ${word}`);

            });

            this.elements.transcript.appendChild(span);
        });
    }

    static clearConversation() {
        this.elements.transcript.innerHTML = '';
        this.elements.imageContainer.innerHTML = '';
        this.elements.contentWrapper.classList.remove('with-image');
        this.hideError();
        this.updateStatus('Ready to start');
        if (map) {
            map.remove();
            map = null;
        }
    }

    static updateButtons(isConnected) {
        this.elements.startButton.disabled = isConnected;
        this.elements.stopButton.disabled = !isConnected;
    }

    static displayImage(imageUrl, imageSource, query) {
        const sideContainer = document.querySelector('.side-container');
        const imageContainer = this.elements.imageContainer;
        
        if (!imageUrl) {
            imageContainer.innerHTML = '';
            this.elements.contentWrapper.classList.remove('with-image');
            // Recenter map after layout changes
            if (map) {
                setTimeout(() => {
                    map.invalidateSize();
                    const center = map.getCenter();
                    map.setView(center, map.getZoom());
                }, 100);
            }
            return;
        }

        this.elements.contentWrapper.classList.add('with-image');
        const imageWrapper = document.createElement('div');
        imageWrapper.className = 'image-wrapper';
        
        const img = document.createElement('img');
        img.className = 'search-image';
        img.alt = query;
        
        const loadingDiv = document.createElement('div');
        loadingDiv.textContent = 'Loading image...';
        loadingDiv.className = 'image-loading';
        imageWrapper.appendChild(loadingDiv);
        
        img.onload = () => {
            loadingDiv.remove();
            imageWrapper.appendChild(img);
            const caption = document.createElement('div');
            caption.className = 'image-caption';
            caption.innerHTML = `
                Image related to: ${query}<br>
                <a href="${imageSource}" target="_blank">Image source</a>
            `;
            imageWrapper.appendChild(caption);
        };
        
        img.onerror = () => {
            loadingDiv.textContent = 'Failed to load image';
            loadingDiv.className = 'image-error';
        };
        
        img.src = imageUrl;
        imageContainer.innerHTML = '';
        imageContainer.appendChild(imageWrapper);
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
        if (transcript) {
            UI.updateTranscript(transcript, isLocalRes);
        }
    }

    static async handelDeveloperFunction(output){
        try {
            const args = JSON.parse(output.arguments);
            const response = await fetch(`${CONFIG.API_ENDPOINTS.weather}/${encodeURIComponent(args.location)}`);
            const data = await response.json();
        }catch (e) {
            
        }
    }

    static async handleWeatherFunction(output) {
        try {
            const args = JSON.parse(output.arguments);
            const response = await fetch(`${CONFIG.API_ENDPOINTS.weather}/${encodeURIComponent(args.location)}`);
            const data = await response.json();
            
            // Format the current weather information
            const currentWeather = `Current Weather in ${args.location}:
${CONFIG.WEATHER_ICONS[data.weather_code] || '🌡️'} ${data.temperature}°${data.unit_temperature}
• Humidity: ${data.humidity}%
• Precipitation: ${data.precipitation}${data.unit_precipitation}
• Wind Speed: ${data.wind_speed}${data.unit_wind}`.trim();

            // Format the forecast information
            const forecast = data.forecast_daily.map(day => 
                `${new Date(day.date).toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })}:
${CONFIG.WEATHER_ICONS[day.weather_code] || '🌡️'} High: ${day.max_temp}°${data.unit_temperature}
• Low: ${day.min_temp}°${data.unit_temperature}
• Precipitation: ${day.precipitation}${data.unit_precipitation}`.trim()
            ).join('\n\n');
            
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message function-result weather';
            
            // Add current weather
            const currentWeatherDiv = document.createElement('div');
            currentWeatherDiv.textContent = currentWeather;
            messageDiv.appendChild(currentWeatherDiv);
            
            // Add forecast toggle button
            const toggleButton = document.createElement('button');
            toggleButton.className = 'forecast-toggle';
            toggleButton.textContent = '7-Day Forecast';
            messageDiv.appendChild(toggleButton);
            
            // Add forecast content (hidden by default)
            const forecastDiv = document.createElement('div');
            forecastDiv.className = 'forecast-content';
            forecastDiv.textContent = forecast;
            messageDiv.appendChild(forecastDiv);
            
            // Add click handler for toggle
            toggleButton.addEventListener('click', () => {
                toggleButton.classList.toggle('expanded');
                forecastDiv.classList.toggle('expanded');
            });
            
            if (UI.elements.transcript.firstChild) {
                UI.elements.transcript.insertBefore(messageDiv, UI.elements.transcript.firstChild);
            } else {
                UI.elements.transcript.appendChild(messageDiv);
            }
            
            if (data.latitude && data.longitude) {
                updateMap(data.latitude, data.longitude, data.location_name);
            }
            
            return {
                temperature: data.temperature,
                humidity: data.humidity,
                precipitation: data.precipitation,
                wind_speed: data.wind_speed,
                forecast_daily: data.forecast_daily,
                current_time: data.current_time,
                location: args.location,
                latitude: data.latitude,
                longitude: data.longitude,
                location_name: data.location_name
            };
        } catch (error) {
            ErrorHandler.handle(error, 'Weather Function');
            return "Could not get weather data";
        }
    }

    static async handleSearchFunction(output) {
        try {
            const args = JSON.parse(output.arguments);
            const response = await fetch(`${CONFIG.API_ENDPOINTS.search}/${encodeURIComponent(args.query)}`);
            const data = await response.json();
            
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message function-result search';
            
            const titleDiv = document.createElement('div');
            titleDiv.className = 'result-title';
            const titleLink = document.createElement('a');
            titleLink.href = data.source;
            titleLink.target = '_blank';
            titleLink.rel = 'noopener noreferrer';
            titleLink.textContent = data.title;
            titleDiv.appendChild(titleLink);
            
            const snippetDiv = document.createElement('div');
            snippetDiv.className = 'result-snippet';
            snippetDiv.textContent = data.snippet;
            
            const sourceDiv = document.createElement('div');
            sourceDiv.className = 'result-source';
            const sourceLink = document.createElement('a');
            sourceLink.href = data.source;
            sourceLink.target = '_blank';
            sourceLink.rel = 'noopener noreferrer';
            sourceLink.textContent = data.source;
            sourceDiv.appendChild(sourceLink);
            
            messageDiv.appendChild(titleDiv);
            messageDiv.appendChild(snippetDiv);
            messageDiv.appendChild(sourceDiv);
            
            if (UI.elements.transcript.firstChild) {
                UI.elements.transcript.insertBefore(messageDiv, UI.elements.transcript.firstChild);
            } else {
                UI.elements.transcript.appendChild(messageDiv);
            }
            
            UI.displayImage(data.image_url, data.image_source, args.query);
            
            return {
                title: data.title,
                snippet: data.snippet,
                source: data.source,
                image_url: data.image_url,
                image_source: data.image_source
            };
        } catch (error) {
            ErrorHandler.handle(error, 'Search Function');
            return "Could not perform search";
        }
    }
}

// WebRTC Manager
class WebRTCManager {
    constructor(app) {
        this.peerConnection = null;
        this.localStream = null;
        this.remoteStream = null;
        this.localSTT = new STTHandler(true);
        //this.remoteSTT = new STTHandler(this, false);
        //Basic Channel
        this.signaling = new BroadcastChannel('webrtc');
        this.signaling.onmessage = e => {
            console.log("☎️ signalMessage : ", e.data)
            if (!this.localStream) {
                console.log('not ready yet');
                return;
            }
            switch (e.data.type) {
                case 'offer':
                    this.handleOffer(e.data);
                    break;
                case 'answer':
                    this.handleAnswer(e.data);
                    break;
                case 'candidate':
                    this.handleCandidate(e.data);
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
        //this.peerConnection.addTrack(this.localStream()[0]);
        if (this.localStream) {
            STTHandler.handleTranscript(this.localStream, true);
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
                this.signaling.postMessage(message);
            }else{
                console.log("☎️ candidates? ",e)
            }
        };
        this.peerConnection.ontrack = async e => {
            this.remoteStream = e.streams[0];
            console.log("remote stream!")
            if(this.remoteStream) {
                STTHandler.handleTranscript(this.remoteStream, false);
                UI.elements.remoteView.srcObject = this.remoteStream;
            }
        }

        if(this.localStream)
            this.localStream.getTracks().forEach(track => this.peerConnection.addTrack(track, this.localStream));
    }

    start(){
        this.signaling.postMessage({type: 'ready'});
    }

    stop(){
        this.signaling.postMessage({type: 'bye'});
    }

    async makeCall() {
        console.log("☎️ makeCall")
        await this.createPeerConnection();
        console.log("☎️ createOffer")
        const offer = await this.peerConnection.createOffer();
        this.signaling.postMessage({type: 'offer', sdp: offer.sdp});
        await this.peerConnection.setLocalDescription(offer);
    }

    async hangup() {
        if (this.peerConnection) {
            this.peerConnection.close();
            this.peerConnection = null;
        }
        this.localStream.getTracks().forEach(track => track.stop());
        this.localStream = null;
        STTHandler.stop();
    };

    async handleOffer(offer) {
        if (this.peerConnection) {
            console.error('existing peerconnection');
            return;
        }
        await this.createPeerConnection();
        console.log("☎️ handleAnswer")
        await this.peerConnection.setRemoteDescription(offer);

        const answer = await this.peerConnection.createAnswer();
        this.signaling.postMessage({type: 'answer', sdp: answer.sdp});
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
        STTHandler.stop();
    }
}


class STTHandler {
    constructor() {
        //import websocket
        ws = new WebSocket(`ws://localhost:8888/ws/stt`);
        ws.binaryType = 'arraybuffer';
        ws.onopen = () => {
            // 첫 메시지: 설정 전송
            // ws.send(JSON.stringify({
            //     language: 'ko-KR',
            //     sample_rate: 16000,
            //     interim_results: true
            // }));
        }
        ws.onmessage = async (ev) => {
            try {
                const data = JSON.parse(ev.data);
                //const isLocalRes = data.islocal;
                const res_type = data.responseType[0];
                if (res_type == "transcription") {
                    // 기본 정보 출력
                    const text = data.transcription.text
                    if(text != "")
                        console.log('stt text: ', text, 'isLocal? : ')//,isLocalRes)
                        await MessageHandler.handleTranscript(data,true);
                }
            } catch {
                // 텍스트 외 바이너리 응답은 없음
            }
        };
        ws.onclose = () => {
            document.getElementById('status').textContent = 'Status: closed';
        };
    }

    static async handleTranscript(stream, isLocal) {
        try {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)({sampleRate: 16000});

            // 마이크 스트림을 AudioContext에 연결
            source = audioCtx.createMediaStreamSource(stream);

            // ScriptProcessorNode 생성 (buffer size: 16384, mono: 1) 32000 Byte
            processor = audioCtx.createScriptProcessor(16384, 1, 1);

            // 오디오 데이터가 들어올 때마다 호출됨
            processor.onaudioprocess = (e) => {
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

                if (ws && ws.readyState === WebSocket.OPEN) {
                    // ws.send(JSON.stringify({
                    //     isLocal: isLocal})
                    // )
                    ws.send(int16Data); //4096 samples, 16K, 16-int pcm  / 320 KB
                    //console.log("pcm input byteLen : ", int16Data.byteLength)
                }
            };
            // Audio Graph 연결
            source.connect(processor);
            processor.connect(audioCtx.destination); // 출력 연결 (필수)
        } catch (e) {
            console.log('🚨', e)
        }
    }

    async handleMessage(event) {
        try {
            const message = JSON.parse(event.data);
            console.log('Received message:', message);

            // if (message.type === 'response.done') {
            //     await MessageHandler.handleTranscript(message, this.isLocalRes);
            //     const output = message.response?.output?.[0];
            //     if (output?.type === 'function_call' && output?.call_id) {
            //         let result;
            //         if (output.name === 'get_weather') {
            //             result = await MessageHandler.handleWeatherFunction(output);
            //         } else if (output.name === 'search_web') {
            //             result = await MessageHandler.handleSearchFunction(output);
            //         } else if (output.name === 'get_developInfo'){
            //             result = await MessageHandler.handelDeveloperFunction(output);
            //         }
            //     }
            // }
        } catch (error) {
            ErrorHandler.handle(error, 'Message Processing');
        }
    }

    static stop(){
        ws.close(1000, "user stopped streaming");
        // processor.disconnect();
        // source.disconnect();
        // processor = null;
        // source = null;
    }
}

// Main Application
class App {
    constructor() {
        this.webrtc = null;
        this.currentVoice = CONFIG.VOICE;
        this.bindEvents();
    }

    bindEvents() {
        UI.elements.startButton.addEventListener('click', () => this.init());
        UI.elements.stopButton.addEventListener('click', () => this.stop());
        UI.elements.clearButton.addEventListener('click', () => UI.clearConversation());
        UI.elements.panelButton.addEventListener('click', () => UI.elements.panel.classList.toggle("open"));
        document.addEventListener('DOMContentLoaded', () => {
            UI.updateStatus('Ready to start');
        });
    }

    async init() {
        UI.elements.startButton.disabled = true;
        
        try {
            UI.updateStatus('Initializing...');

            this.webrtc = new WebRTCManager(this);
            await this.webrtc.setupLocal();
            await this.webrtc.start();
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

let map = null;

function updateMap(latitude, longitude, locationName) {
    if (!map) {
        map = L.map('map').setView([latitude, longitude], 10);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(map);
    } else {
        map.setView([latitude, longitude], 10);
        map.eachLayer((layer) => {
            if (layer instanceof L.Marker) {
                map.removeLayer(layer);
            }
        });
    }
    
    L.marker([latitude, longitude])
        .addTo(map)
        .bindPopup(locationName)
        .openPopup();

    // Force map to recalculate its container size
    setTimeout(() => {
        map.invalidateSize();
        map.setView([latitude, longitude], 10);
    }, 100);
}

// Initialize the application
const app = new App(); 