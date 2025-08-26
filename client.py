import requests
import sounddevice as sd
import numpy as np
import argparse
import sys
import json
from scipy.io.wavfile import write as write_wav
import time

API_BASE_URL = "http://localhost:8111"
SAMPLE_RATE = 24000  # Matches API's default sample rate

def get_available_voices():
    try:
        response = requests.get(f"{API_BASE_URL}/voices", timeout=10)
        response.raise_for_status()
        return sorted(response.json())
    except requests.exceptions.RequestException as e:
        print(f"Error fetching voices: {e}")
        return []

def get_current_model():
    try:
        response = requests.get(f"{API_BASE_URL}/benchmark", timeout=120)
        response.raise_for_status()
        data = response.json()
        recommendation = data.get("recommendation", {})
        optimal_model = recommendation.get("best_balanced", {}).get("model_name", "Unknown")
        return optimal_model
    except requests.exceptions.RequestException as e:
        print(f"Error fetching current model: {e}")
        return "Unknown"

def handle_synthesis_request(dialogue_script: list, output_file: str = None):
    if not dialogue_script:
        print("Error: Script is empty.")
        return

    payload = {"script": dialogue_script}
    print(f"\n--- Sending Request (Script Lines: {len(dialogue_script)}) ---")
    print(json.dumps(payload, indent=2))
    print("="*50 + "\n")

    try:
        if output_file:
            endpoint_url = f"{API_BASE_URL}/synthesize-wav"
            print(f"Using WAV endpoint: {endpoint_url}")
            start_time = time.time()
            with requests.post(endpoint_url, json=payload, timeout=600) as response:
                response.raise_for_status()
                with open(output_file, 'wb') as f:
                    f.write(response.content)
                elapsed_time = time.time() - start_time
                print(f"Success! Audio saved to '{output_file}' in {elapsed_time:.2f} seconds")
        else:
            endpoint_url = f"{API_BASE_URL}/synthesize-stream"
            print(f"Using Streaming endpoint: {endpoint_url}")
            print("Playing audio stream...")
            buffer = bytearray()
            with requests.post(endpoint_url, json=payload, stream=True, timeout=600) as response:
                response.raise_for_status()
                sample_rate = int(response.headers.get("X-Sample-Rate", SAMPLE_RATE))
                with sd.OutputStream(samplerate=sample_rate, channels=1, dtype='float32') as stream:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            buffer.extend(chunk)
                            # Ensure buffer is a multiple of 4 bytes (float32)
                            remainder = len(buffer) % 4
                            if remainder == 0:
                                audio_data = np.frombuffer(buffer, dtype=np.float32)
                                if audio_data.size > 0:
                                    stream.write(audio_data)
                                buffer = bytearray()  # Clear buffer after writing
                            # Keep incomplete chunks in buffer for next iteration
            print("Playback finished.")

    except requests.exceptions.Timeout:
        print(f"Error: Request timed out after 600 seconds. Try splitting the script or using a faster model (e.g., INT8).")
    except requests.exceptions.RequestException as e:
        print(f"Error: API request failed: {e}")
        try:
            print(f"Server response: {response.json()}")
        except:
            pass
    except Exception as e:
        print(f"Error during audio processing: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ultimate client for the Kokoro TTS API.")
    parser.add_argument('text', nargs='?', help="Text to speak.")
    parser.add_argument('-f', '--file', help="Path to a JSON script file.")
    parser.add_argument('-v', '--voice', default='af_sky', help="Default voice.")
    parser.add_argument('-i', '--interactive', action='store_true', help="Enter interactive mode.")
    parser.add_argument('-o', '--output', help="Path to save the output as a WAV file.")
    args = parser.parse_args()

    # Fetch available voices
    available_voices = get_available_voices()
    if not available_voices:
        print("Warning: Could not fetch voices from API. Using default voice.")
    elif args.voice not in available_voices:
        print(f"Warning: Voice '{args.voice}' not available. Available voices: {available_voices}")
        args.voice = available_voices[0] if available_voices else 'af_sky'

    # Check current model
    current_model = get_current_model()
    print(f"Current API model: {current_model}")

    if args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                script_to_send = json_data.get('script')
            if script_to_send:
                handle_synthesis_request(script_to_send, args.output)
            else:
                print("Error: No 'script' key in JSON file.")
                sys.exit(1)
        except Exception as e:
            print(f"Error loading file: {e}")
            sys.exit(1)
            
    elif args.interactive:
        current_voice = args.voice
        print(f"\n--- Interactive Mode (Voice: {current_voice}) ---")
        print(f"Available voices: {available_voices}")
        print("Commands: /voice <name>, /save <file.wav>, /model, quit")
        while True:
            user_input = input(f"({current_voice}) > ")
            if user_input.lower() in ['quit', 'exit']:
                break
                
            if user_input.strip().startswith('/'):
                parts = user_input.strip().split()
                command = parts[0].lower()
                if command == '/save':
                    if len(parts) > 1:
                        text_to_save = input("   Text to save > ")
                        if text_to_save:
                            handle_synthesis_request([{"text": text_to_save, "voice": current_voice}], parts[1])
                    else:
                        print("Usage: /save <filename.wav>")
                elif command == '/voice':
                    if len(parts) > 1:
                        new_voice = parts[1]
                        if new_voice in available_voices:
                            current_voice = new_voice
                            print(f"Voice set to {current_voice}")
                        else:
                            print(f"Voice '{new_voice}' not available. Available: {available_voices}")
                    else:
                        print("Usage: /voice <voice_name>")
                elif command == '/model':
                    current_model = get_current_model()
                    print(f"Current API model: {current_model}")
                else:
                    print("Unknown command.")
                continue
                
            if user_input:
                handle_synthesis_request([{"text": user_input, "voice": current_voice}])
        print("Exiting.")
        
    elif args.text:
        handle_synthesis_request([{"text": args.text, "voice": args.voice}], args.output)
    
    else:
        handle_synthesis_request([{"text": "Hello, world!", "voice": args.voice}])

    print("\n--- Client Finished ---")