# api/api.py
import os
import sys
import numpy as np
import io
import re
from scipy.io.wavfile import write as write_wav
import uvicorn
from typing import List, Optional
import asyncio
import requests
from tqdm import tqdm # The robust downloader progress bar

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field, model_validator

from kokoro_onnx import Kokoro, Tokenizer

# --- Project Setup and Model Downloader ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(PROJECT_ROOT, 'models')
MODEL_FILE = "kokoro-v1.0.fp16.onnx"; VOICES_FILE = "voices-v1.0.bin"
model_path = os.path.join(MODELS_DIR, MODEL_FILE); voices_path = os.path.join(MODELS_DIR, VOICES_FILE)

# --- The Unbreakable Downloader ---
BASE_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
MODEL_URL = BASE_URL + MODEL_FILE; VOICES_URL = BASE_URL + VOICES_FILE
def download_file_robust(url: str, destination: str):
    print(f"Downloading {os.path.basename(destination)}...")
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            with open(destination, 'wb') as f, tqdm(
                total=total_size, unit='iB', unit_scale=True, desc=os.path.basename(destination)
            ) as bar:
                for chunk in r.iter_content(chunk_size=8192):
                    size = f.write(chunk); bar.update(size)
        if total_size != 0 and os.path.getsize(destination) != total_size:
            print(f"\nFATAL ERROR: Download failed. File is incomplete."); sys.exit(1)
        print("\nDownload verified and complete.")
    except Exception as e:
        print(f"\nFATAL ERROR: Failed to download model file. Error: {e}"); sys.exit(1)

def download_models_if_missing():
    os.makedirs(MODELS_DIR, exist_ok=True)
    if not os.path.exists(model_path): download_file_robust(MODEL_URL, model_path)
    if not os.path.exists(voices_path): download_file_robust(VOICES_URL, voices_path)
download_models_if_missing()

# --- Load Models on Startup ---
print("Loading model and tokenizer...")
tokenizer = Tokenizer()
kokoro = Kokoro(model_path, voices_path)
SAMPLE_RATE = 24000
print("Model and voices loaded successfully. API is ready.")

app = FastAPI(title="Kokoro TTS Service", version="FINAL-STABLE")

# --- Pydantic Models ---
class VoiceComponent(BaseModel): voice: str; weight: float = Field(..., ge=0.0, le=1.0)
class DialogueLine(BaseModel):
    text: str; voice: Optional[str] = None; blend_components: Optional[List[VoiceComponent]] = None
    delay: Optional[float] = 0.0; speed: float = Field(1.0, ge=0.25, le=2.0)
    @model_validator(mode='before')
    def check_voice_or_blend(cls, values):
        if not (bool(values.get('voice')) ^ bool(values.get('blend_components'))):
            raise ValueError('Each line must have "voice" or "blend_components", not both.')
        return values
class SynthesizeRequest(BaseModel): script: List[DialogueLine]

# --- Helper function for audio generation (English Only) ---
async def generate_full_audio(script: List[DialogueLine]):
    all_samples = []
    for line in script:
        voice_or_style = None
        if line.blend_components:
            final_style = np.zeros(256, dtype=np.float16)
            total_weight = sum(c.weight for c in line.blend_components)
            for c in line.blend_components:
                if c.voice in kokoro.get_voices():
                    final_style = np.add(final_style, kokoro.get_voice_style(c.voice) * c.weight)
            if total_weight > 0: final_style /= total_weight
            voice_or_style = final_style
        elif line.voice and line.voice in kokoro.get_voices():
            voice_or_style = line.voice
        if voice_or_style is None: continue
        if line.delay and line.delay > 0:
            all_samples.append(np.zeros(int(line.delay * SAMPLE_RATE), dtype=np.float32))
        phonemes = tokenizer.phonemize(line.text, lang="en-us")
        if not phonemes: continue
        samples, _ = await asyncio.to_thread(kokoro.create, phonemes, voice=voice_or_style, speed=line.speed, is_phonemes=True)
        all_samples.append(samples.astype(np.float32))
    return np.concatenate(all_samples) if all_samples else np.array([], dtype=np.float32)

# --- API Endpoints ---
@app.get("/")
def read_root(): return {"status": "Kokoro TTS API is running."}
@app.get("/voices", response_model=List[str])
async def get_voices(): return sorted(kokoro.get_voices())

@app.post("/synthesize-stream")
async def synthesize_stream(request: SynthesizeRequest):
    q = asyncio.Queue(maxsize=20)
    async def producer():
        for line in request.script:
            voice_or_style = None
            if line.blend_components:
                final_style = np.zeros(256, dtype=np.float16)
                total_weight = sum(c.weight for c in line.blend_components)
                for c in line.blend_components:
                    if c.voice in kokoro.get_voices():
                        final_style = np.add(final_style, kokoro.get_voice_style(c.voice) * c.weight)
                if total_weight > 0: final_style /= total_weight
                voice_or_style = final_style
            elif line.voice and line.voice in kokoro.get_voices():
                voice_or_style = line.voice
            if voice_or_style is None: continue

            if line.delay and line.delay > 0:
                await q.put(np.zeros(int(line.delay * SAMPLE_RATE), dtype=np.float32))

            sentences = re.split(r'(?<=[.?!])\s*', line.text)
            sentences = [s.strip() for s in sentences if s.strip()]
            for sentence in sentences:
                phonemes = tokenizer.phonemize(sentence, lang="en-us")
                if not phonemes: continue
                samples, _ = await asyncio.to_thread(kokoro.create, phonemes, voice=voice_or_style, speed=line.speed, is_phonemes=True)
                await q.put(samples)
        await q.put(None)
    async def stream_generator():
        asyncio.create_task(producer())
        while True:
            samples = await q.get()
            if samples is None: break
            yield samples.astype(np.float32).tobytes()
    headers = {"X-Sample-Rate": str(SAMPLE_RATE)}
    return StreamingResponse(stream_generator(), media_type="application/octet-stream", headers=headers)

@app.post("/synthesize-wav")
async def synthesize_wav(request: SynthesizeRequest):
    try:
        full_audio = await generate_full_audio(request.script)
        if full_audio.size == 0: return Response(content=b"", media_type="audio/wav")
        max_val = np.max(np.abs(full_audio));
        if max_val > 0: full_audio /= max_val
        buffer = io.BytesIO(); write_wav(buffer, SAMPLE_RATE, full_audio); buffer.seek(0)
        return Response(content=buffer.getvalue(), media_type="audio/wav")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)