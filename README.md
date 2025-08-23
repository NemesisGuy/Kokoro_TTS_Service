# Kokoro TTS Service - A High-Performance Text-to-Speech API

This project provides a self-contained, high-performance FastAPI server for the Kokoro text-to-speech engine. It is designed for professional use, featuring a rich API that supports dynamic voice generation, multi-character dialogues, and custom voice blending. The service is self-configuring, automatically downloading the required model files (~200MB) from GitHub Releases on its first run.

This repository also includes a powerful command-line client for interaction, a comprehensive benchmark tool to optimize performance, and a rich Gradio UI for visual testing and demonstration.

## Setup

### 1. Prerequisites

* **Python 3.8 or newer:** This project was developed on Python 3.13 and is expected to be compatible with Python 3.8+.
* **Git:** You will need Git to clone the repository.

### 2. Clone the Repository

First, clone the repository to your local machine. This will download all the necessary code and configuration files.

```bash
git clone https://github.com/NemesisGuy/Kokoro_TTS_Service.git
cd Kokoro_TTS_Service
```

### 3. Install Dependencies

1. Create a Python virtual environment:
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
3. Install all required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

**Note**: The first time the server runs, it will automatically download the necessary model files (~200MB) from GitHub Releases.

---

## Running the Server and Tools

### 1. API Server (`api/api.py`)

To start the API server for development (with auto-reload), run:
```bash
uvicorn api.api:app --reload
```
The server will be available at `http://127.0.0.1:8000`.  
Interactive API documentation (Swagger UI) is available at `http://127.0.0.1:8000/docs`.

### 2. Gradio Showcase (`gradio_app.py`)

This provides a rich, tabbed web interface for testing all API features. The API server must be running first.
```bash
python gradio_app.py
```

### 3. Benchmark Tool (`benchmark.py`)

Test the performance of different model versions (`FP32`, `FP16`, `INT8`) on your hardware.
```bash
python benchmark.py
```
After running, the tool will recommend the best model for your setup. You can then update the `MODEL_TO_USE` variable in `api/api.py` to optimize the server for your deployment environment.

### 4. Using the Command-Line Client (`client.py`)

The `client.py` script is a powerful tool for scripting and testing all API features from the command line.

#### Basic Modes of Operation

1. **Speak a Single Line**:  
   Provide the text directly as an argument. Use quotes for sentences with punctuation.
   ```bash
   python client.py "Hello, this is a simple test."
   ```

2. **Run in Interactive Mode**:  
   Use the `-i` or `--interactive` flag to start a session where you can type multiple lines.
   ```bash
   python client.py -i
   ```
   Commands inside Interactive Mode:
   - `/voice <voice_name>`: Changes the voice for the rest of the session.
   - `/save <filename.wav>`: Prompts you for text and saves the next line to a file.
   - `quit` or `exit`: Stops the client.

3. **Run a Script from a JSON File**:  
   The most powerful feature for complex scenes. Use the `-f` or `--file` flag.
   ```bash
   python client.py --file script.json
   ```

#### Combining Flags for More Power

- **Change the Voice**:  
  Use the `-v` or `--voice` flag. You can get a full list of names from the `/voices` endpoint or the `list_voices.py` script.
  ```bash
  python client.py -v "am_adam" "This sentence will be spoken by Adam's voice."
  ```

- **Save Audio to a WAV File**:  
  Use the `-o` or `--output` flag. This will save the result instead of playing it.
  ```bash
  python client.py "Save this line to a file." -o my_audio.wav
  ```

- **Combine Voice and Save**:  
  ```bash
  python client.py -v "af_nova" -o nova_line.wav "This is Nova's voice, saved to a file."
  ```

- **Start Interactive Mode with a Different Voice**:  
  ```bash
  python client.py -i -v "am_eric"
  ```

- **Save an Entire JSON Script to a Single WAV File**:  
  ```bash
  python client.py --file script.json -o full_conversation.wav
  ```

---

## API Endpoint Reference

The main synthesis endpoint (`/synthesize`) accepts a `POST` request with a JSON body in the following format:
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
Each item in the `script` list must have either a `voice` or `blend_components`. `speed` and `delay` are optional.

### 1. POST /synthesize-stream & POST /synthesize-wav
- **Description**: The API provides two endpoints for synthesis. `/synthesize-stream` is for real-time applications, and `/synthesize-wav` is for generating complete audio files. The `client.py` script intelligently handles which endpoint to use based on whether you are saving the output.
- **Success Response (200 OK)**: A raw audio stream (`/synthesize-stream`) or a complete WAV file (`/synthesize-wav`).

### 2. GET /voices
- **Description**: Returns a sorted list of all available voice names.
- **Success Response (200 OK)**: A JSON array of strings, e.g., `["af_alloy", "af_aoede", ...]`.

---

## Core Features

* **Automatic Model Downloader:** No manual setup required. The server fetches the correct model files from GitHub Releases on first launch.
* **High-Performance Streaming:** A `/synthesize-stream` endpoint uses `asyncio` to provide raw audio data with minimal latency, perfect for custom real-time applications.
* **Universal WAV File Generation:** A `/synthesize-wav` endpoint generates a complete, universally playable `.wav` file, ideal for simple integrations or saving audio.
* **Unified Dialogue Engine:** A single `/synthesize` endpoint can handle everything from single lines to complex, multi-character scripts with custom voice blends.
* **Dynamic Voice Blending:** Create entirely new, unique voices on the fly by blending multiple existing voices with specific weights *within a dialogue script*.
* **Full Conversation Control:** Orchestrate dialogues with custom delays between lines and control the speaking speed of each character independently.
* **Complete Test Suite:** Includes a powerful command-line client (`client.py`), a comprehensive benchmark tool (`benchmark.py`), and a rich visual testing interface (`gradio_app.py`).