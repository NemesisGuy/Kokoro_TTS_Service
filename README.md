# Kokoro TTS Service - A High-Performance Text-to-Speech API

This project provides a self-contained, high-performance FastAPI server for the Kokoro text-to-speech engine. It is designed for professional use, featuring a rich API that supports dynamic voice generation, multi-character dialogues, custom voice blending, and randomized voice generation. The service is self-configuring, automatically downloading required model files (~600MB for FP32, FP16, INT8, and voices) from GitHub Releases on its first run.

This repository also includes a powerful command-line client, a benchmark tool to optimize performance, and a rich Gradio UI for visual testing and demonstration.

## Setup

### 1. Prerequisites

- **Python 3.8 or newer**: Developed on Python 3.13, compatible with 3.8+.
- **Git**: Required to clone the repository.
- **Docker and Docker Compose**: Use Docker Compose v2.x. Ensure Docker Desktop is configured for WSL2 if using Windows Subsystem for Linux (WSL).
- **Docker Hub Account**: Needed for pushing images to Docker Hub.
- **Portainer (optional)**: For managing Docker containers via a web interface.

### 2. Clone the Repository

```bash
git clone https://github.com/NemesisGuy/Kokoro_TTS_Service.git
cd Kokoro_TTS_Service
```

### 3. Verify Requirements File

Ensure `requirements.txt` contains:
```
fastapi[all]
uvicorn
requests
tqdm
numpy
scipy
kokoro-onnx
gradio
sounddevice
psutil
```
If missing, create or update `requirements.txt`.

### 4. Install Dependencies (Local Setup)

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```
2. Activate the environment:
   - **Windows**:
     ```powershell
     .\.venv\Scripts\Activate.ps1
     ```
   - **macOS/Linux**:
     ```bash
     source .venv/bin/activate
     ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

**Note**: The first time the server runs, it downloads model files (~600MB) from GitHub Releases.

### 5. Running with Docker (Local Setup)

1. Ensure Docker and Docker Compose v2.x are installed:
   ```bash
   docker compose version
   ```
   Upgrade if needed:
   ```bash
   sudo apt-get update
   sudo apt-get install -y docker-compose-plugin
   ```

2. Verify `requirements.txt` exists (see step 3).
3. Build and start services:
   ```bash
   docker compose build --no-cache
   docker compose up -d
   ```
4. Access services:
   - **API**: `http://localhost:8111`
   - **Gradio UI**: `http://localhost:8112`

**Note for WSL Users**: If Gradio UI is inaccessible at `http://localhost:8112`:
   - Check WSL2 IP:
     ```bash
     ip addr show eth0 | grep inet
     ```
     Access `http://<WSL2-IP>:8112`.
   - Set up port forwarding (Windows PowerShell, run as Administrator):
     ```powershell
     netsh interface portproxy add v4tov4 listenport=8112 listenaddress=0.0.0.0 connectport=8112 connectaddress=<WSL2-IP>
     ```

5. Stop services:
   ```bash
   docker compose down -v
   ```

### 6. Pushing Images to Docker Hub

1. **Create a Docker Hub Repository**:
   - Log in to [hub.docker.com](https://hub.docker.com/).
   - Go to **Repositories** > **Create Repository**.
   - Name it (e.g., `kokoro-tts-service`), set visibility to **Public** (or **Private** with a paid plan), and create.

2. **Log In to Docker Hub**:
   ```bash
   docker login
   ```

3. **Tag Images**:
   ```bash
   docker tag kokoro_tts_service-tts-api <your-username>/kokoro-tts-service:tts-api
   docker tag kokoro_tts_service-gradio-ui <your-username>/kokoro-tts-service:gradio-ui
   ```
   Replace `<your-username>` with your Docker Hub username.

4. **Push Images**:
   ```bash
   docker push <your-username>/kokoro-tts-service:tts-api
   docker push <your-username>/kokoro-tts-service:gradio-ui
   ```

5. **Verify**:
   Check your Docker Hub repository.

6. **Clean Up Unused Images**:
   ```bash
   docker image prune
   docker rmi $(docker images -f "dangling=true" -q)
   ```

### 7. Deploying via Portainer

1. **Update `docker-compose.yml`**:
   ```yaml
   services:
     tts-api:
       image: <your-username>/kokoro-tts-service:tts-api
       container_name: kokoro_tts_api
       volumes:
         - tts-models:/app/models
       ports:
         - "8111:8000"
       restart: always

     gradio-ui:
       image: <your-username>/kokoro-tts-service:gradio-ui
       container_name: kokoro_gradio_ui
       ports:
         - "8112:7860"
       environment:
         - API_URL=http://tts-api:8000
       volumes:
         - tts-models:/app/models
       command: ["python", "gradio_app.py", "--server-name", "0.0.0.0"]
       depends_on:
         - tts-api
       restart: always

   volumes:
     tts-models:
   ```
   Replace `<your-username>` with your Docker Hub username.

2. **Deploy in Portainer**:
   - Open Portainer at `http://localhost:9000` (or `http://<WSL2-IP>:9000`).
   - Go to **Stacks** > **Add Stack**.
   - Name the stack (e.g., `kokoro-tts-service`).
   - Paste `docker-compose.yml` into the **Web Editor**.
   - Click **Deploy the Stack**.
   - Verify containers in **Containers**.

3. **Test Deployment**:
   - API: `curl http://localhost:8111/voices`
   - Gradio UI: `http://localhost:8112` (or `http://<WSL2-IP>:8112`).

### 8. Testing the API via Browser

#### Using Postman Web
1. Go to [web.postman.co](https://web.postman.co/) and sign in.
2. Create a **POST** request to `https://kokoro-api.nemesisnet.co.za/synthesize-wav` (or `http://localhost:8111/synthesize-wav`).
3. Set **Body** to **raw** and **JSON**:
   ```json
   {
     "script": [
       {
         "text": "This is a test of the Kokoro TTS API.",
         "voice": "am_eric",
         "speed": 1.0
       }
     ]
   }
   ```
4. Click **Send** to download a WAV file.

#### Using a Browser-Based HTML Page
1. Create `test-api.html`:
   ```html
   <!DOCTYPE html>
   <html>
   <head>
     <title>Kokoro TTS API Test</title>
   </head>
   <body>
     <h1>Test Kokoro TTS API</h1>
     <textarea id="textInput" rows="4" cols="50">Hello, this is a test.</textarea><br>
     <select id="voiceSelect">
       <option value="am_eric">am_eric</option>
       <option value="af_sky">af_sky</option>
     </select><br>
     <input type="number" id="speedInput" value="1.0" step="0.1" min="0.5" max="2.0"><br>
     <button onclick="synthesize()">Synthesize</button><br>
     <audio id="audioOutput" controls></audio>
     <p id="status"></p>
     <script>
       async function synthesize() {
         const text = document.getElementById('textInput').value;
         const voice = document.getElementById('voiceSelect').value;
         const speed = parseFloat(document.getElementById('speedInput').value);
         const status = document.getElementById('status');
         const audio = document.getElementById('audioOutput');
         try {
           status.textContent = 'Sending request...';
           const response = await fetch('https://kokoro-api.nemesisnet.co.za/synthesize-wav', {
             method: 'POST',
             headers: { 'Content-Type': 'application/json' },
             body: JSON.stringify({ script: [{ text, voice, speed }] })
           });
           if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
           const blob = await response.blob();
           const url = window.URL.createObjectURL(blob);
           audio.src = url;
           audio.play();
           status.textContent = 'Success! Audio is playing.';
           const a = document.createElement('a');
           a.href = url;
           a.download = 'output.wav';
           a.click();
         } catch (error) {
           status.textContent = `Error: ${error.message}`;
         }
       }
       async function loadVoices() {
         try {
           const response = await fetch('https://kokoro-api.nemesisnet.co.za/voices');
           const voices = await response.json();
           const voiceSelect = document.getElementById('voiceSelect');
           voiceSelect.innerHTML = '';
           voices.forEach(voice => {
             const option = document.createElement('option');
             option.value = voice;
             option.textContent = voice;
             voiceSelect.appendChild(option);
           });
         } catch (error) {
           document.getElementById('status').textContent = `Error loading voices: ${error.message}`;
         }
       }
       window.onload = loadVoices;
     </script>
   </body>
   </html>
   ```
2. Serve locally:
   ```bash
   python -m http.server 8080
   ```
3. Open `http://localhost:8080/test-api.html`.

## Running the Server and Tools

### 1. API Server (`api/api.py`)

Start locally for development:
```bash
uvicorn api.api:app --reload
```
Access at `http://127.0.0.1:8000`. Swagger UI at `http://127.0.0.1:8000/docs`.

### 2. Gradio Showcase (`gradio_app.py`)

```bash
python gradio_app.py
```
Access at `http://localhost:7860`.

### 3. Benchmark Tool (`benchmark.py`)

Test model performance (FP32, FP16, INT8):
```bash
python benchmark.py
```

### 4. Using the Command-Line Client (`client.py`)

#### Basic Modes
1. **Single Line**:
   ```bash
   python client.py "Hello, this is a simple test."
   ```
2. **Interactive Mode**:
   ```bash
   python client.py -i
   ```
   Commands: `/voice <voice_name>`, `/save <filename.wav>`, `quit`.
3. **JSON Script**:
   ```bash
   python client.py --file script.json
   ```

#### Combining Flags
- Change voice:
  ```bash
  python client.py -v "am_adam" "This sentence will be spoken by Adam's voice."
  ```
- Save audio:
  ```bash
  python client.py "Save this line to a file." -o my_audio.wav
  ```
- Combine:
  ```bash
  python client.py -v "af_nova" -o nova_line.wav "This is Nova's voice, saved to a file."
  ```

## API Endpoint Reference

### 1. POST /synthesize-stream & POST /synthesize-wav
- **Description**: `/synthesize-stream` for real-time audio, `/synthesize-wav` for WAV files.
- **Request Body**:
  ```json
  {
    "script": [
      {
        "text": "The text to be spoken.",
        "voice": "af_sky",
        "speed": 1.0,
        "delay": 0.5
      },
      {
        "text": "This line uses a custom blended voice.",
        "blend_components": [
          { "voice": "am_adam", "weight": 0.7 },
          { "voice": "af_nova", "weight": 0.3 }
        ]
      }
    ]
  }
  ```
- **Response**: Audio stream or WAV file.

### 2. GET /voices
- **Description**: Returns available voice names.
- **Response**: `["af_alloy", "af_aoede", ...]`

### 3. GET /benchmark
- **Description**: Runs performance tests on FP32, FP16, and INT8 models. The recommended model (`best_balanced`) is labeled as `(optimal)` in the Gradio UI dropdown.
- **Response**:
  ```json
  {
    "results": [
      {
        "model_name": "kokoro-v1.0.fp16.onnx",
        "description": "Half Precision (FP16)",
        "size_mb": 200.5,
        "load_time": 1.234,
        "inference_time": 0.567,
        "duration": 2.0,
        "rtf": 0.283,
        "mem_usage": 512.3
      },
      ...
    ],
    "system_info": {
      "cpu": "Intel(R) Xeon(R) CPU E5620 @ 2.40GHz",
      "physical_cores": 4,
      "logical_cores": 8,
      "total_ram_gb": 16.0
    },
    "recommendation": {
      "best_balanced": {
        "model_name": "kokoro-v1.0.fp16.onnx",
        "description": "Half Precision (FP16)",
        "reason": "Offers a good balance of speed (RTF: 0.28) and memory usage (512 MB)."
      },
      "fastest": {
        "model_name": "kokoro-v1.0.int8.onnx",
        "description": "Quantized (INT8)",
        "reason": "Lowest Real-Time Factor (RTF: 0.25)."
      },
      "highest_quality": {
        "model_name": "kokoro-v1.0.onnx",
        "description": "Full Precision (FP32)",
        "reason": "Highest fidelity, but uses the most memory (768 MB)."
      }
    }
  }
  ```

### 4. POST /set-model
- **Description**: Switches the active model.
- **Request Body**:
  ```json
  {
    "model_name": "kokoro-v1.0.fp16.onnx"
  }
  ```
- **Response**:
  ```json
  {
    "status": "Successfully switched to model kokoro-v1.0.fp16.onnx"
  }
  ```

### 5. POST /random-speaker
- **Description**: Generates audio with a randomly selected voice.
- **Request Body**:
  ```json
  {
    "text": "This is a test with a random voice.",
    "speed": 1.0
  }
  ```
- **Response**: WAV audio file with `X-Selected-Voice` header indicating the chosen voice (e.g., `am_eric`).

### 6. POST /random-custom-voice
- **Description**: Generates audio with a custom voice blended from 2–3 randomly selected voices with random weights (summing to 1.0).
- **Request Body**:
  ```json
  {
    "text": "This is a test with a random custom voice.",
    "speed": 1.0,
    "num_voices": 2
  }
  ```
- **Response**: WAV audio file with `X-Blended-Voices` header listing the blended voices and weights (e.g., `[{"voice": "am_adam", "weight": 0.6}, {"voice": "af_nova", "weight": 0.4}]`).

## Core Features

- **Automatic Model Downloader**: Fetches model files (~600MB) from GitHub Releases.
- **High-Performance Streaming**: Low-latency audio via `/synthesize-stream`.
- **Universal WAV File Generation**: Playable `.wav` files via `/synthesize-wav`, `/random-speaker`, and `/random-custom-voice`.
- **Unified Dialogue Engine**: Supports single lines and complex scripts.
- **Dynamic Voice Blending**: Create new voices by blending existing ones.
- **Randomized Voice Generation**: Generate audio with random or custom blended voices.
- **Full Conversation Control**: Customize delays and speeds per character.
- **Benchmarking**: Evaluate model performance and select the optimal model via Gradio UI.
- **Complete Test Suite**: Includes `client.py`, `benchmark.py`, and `gradio_app.py`.

## Using the Gradio UI

- **Simple Synthesis**: Enter text, select a voice, adjust speed, and synthesize audio.
- **Dialogue & Scripting**: Input a JSON script for multi-line dialogues with different voices and timings.
- **Voice Blender**: Blend up to three voices with custom weights to create unique voices.
- **Benchmark**: Run performance tests to compare FP32, FP16, and INT8 models. The recommended model is labeled `(optimal)` in the **Select Model** dropdown. Select and set the model to optimize performance.

## Troubleshooting

### Docker Issues
- **Containers not running**:
  ```bash
  docker ps -a
  docker logs kokoro_tts_api
  docker logs kokoro_gradio_ui
  ```
  If missing modules:
  - Verify `requirements.txt`.
  - Check line endings:
    ```bash
    sudo apt-get install -y dos2unix
    dos2unix requirements.txt
    ```
  - Rebuild:
    ```bash
    docker compose build --no-cache
    docker compose up -d
    ```

- **Model download failures**:
  Verify URLs:
  ```bash
  curl -I https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.fp16.onnx
  ```
  Manually download if needed:
  ```bash
  mkdir -p models
  curl -L -o models/kokoro-v1.0.fp16.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.fp16.onnx
  ```

- **Port conflicts**:
  ```bash
  netstat -a -n -o | grep "811[12]"
  ```

### WSL-Specific Issues
- **Gradio UI inaccessible**:
  ```bash
  ip addr show eth0 | grep inet
  ```
  Set up port forwarding:
  ```powershell
  netsh interface portproxy add v4tov4 listenport=8112 listenaddress=0.0.0.0 connectport=8112 connectaddress=<WSL2-IP>
  ```

### Gradio UI Issues
- **Dialogue tab error**:
  - Ensure valid JSON:
    ```json
    {
      "script": [
        {
          "text": "This is an editable script.",
          "voice": "am_eric",
          "speed": 0.9
        },
        {
          "text": "Each line has its own timing and voice.",
          "voice": "af_sky",
          "delay": 0.5
        }
      ]
    }
    ```
  - Check logs:
    ```bash
    docker logs kokoro_gradio_ui
    ```

- **Benchmark dropdown empty**:
  - Verify `/benchmark` endpoint:
    ```bash
    curl http://localhost:8111/benchmark
    ```
  - Check logs:
    ```bash
    docker logs kokoro_tts_api
    ```
  - Ensure all model files exist in `/app/models`:
    ```bash
    docker exec kokoro_tts_api ls /app/models
    ```

