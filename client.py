# client.py
import requests
import sounddevice as sd
import numpy as np
import argparse
import sys
import json
from scipy.io.wavfile import write as write_wav

API_BASE_URL = "http://127.0.0.1:8111"

def handle_synthesis_request(dialogue_script: list, output_file: str = None):
    if not dialogue_script:
        print("Error: Script is empty.")
        return
        
    payload = {"script": dialogue_script}
    
    if output_file:
        endpoint_url = f"{API_BASE_URL}/synthesize-wav"
        print(f"\n--- Sending Request to WAV Endpoint ---")
    else:
        endpoint_url = f"{API_BASE_URL}/synthesize-stream"
        print(f"\n--- Sending Request to Streaming Endpoint ---")
    
    print(json.dumps(payload, indent=2))
    print("="*50 + "\n")

    try:
        with requests.post(endpoint_url, json=payload, stream=True) as response:
            response.raise_for_status()
            
            if output_file:
                with open(output_file, 'wb') as f:
                    f.write(response.content)
                print(f"Success! Audio saved to '{output_file}'")
            else:
                sample_rate = int(response.headers.get("X-Sample-Rate", 24000))
                print("Playing audio stream...")
                with sd.OutputStream(samplerate=sample_rate, channels=1, dtype='float32') as stream:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            stream.write(np.frombuffer(chunk, dtype=np.float32))
                print("Playback finished.")

    except requests.exceptions.RequestException as e:
        print(f"\n--- AN ERROR OCCURRED: {e} ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ultimate client for the Kokoro TTS API.")
    parser.add_argument('text', nargs='?', help="Text to speak.")
    
    # --- THIS IS THE FIX ---
    parser.add_argument('-f', '--file', help="Path to a JSON script file.")
    # --- END OF FIX ---
    
    parser.add_argument('-v', '--voice', default='af_sky', help="Default voice.")
    parser.add_argument('-i', '--interactive', action='store_true', help="Enter interactive mode.")
    parser.add_argument('-o', '--output', help="Path to save the output as a WAV file.")
    args = parser.parse_args()

    if args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                script_to_send = json_data.get('script')
            if script_to_send:
                handle_synthesis_request(script_to_send, args.output)
        except Exception as e:
            print(f"Error loading file: {e}"); sys.exit(1)
            
    elif args.interactive:
        current_voice = args.voice
        print(f"\n--- Interactive Mode (Voice: {current_voice}) ---")
        print("Commands: /voice <name>, /save <file.wav>, quit")
        while True:
            user_input = input(f"({current_voice}) > ");
            if user_input.lower() in ['quit', 'exit']: break
            
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
                    if len(parts) > 1: current_voice = parts[1]; print(f"Voice set to {current_voice}")
                    else: print("Usage: /voice <voice_name>")
                else:
                    print("Unknown command.")
                continue
                
            if user_input:
                handle_synthesis_request([{"text": user_input, "voice": current_voice}])
        print("Exiting.")
        
    elif args.text:
        handle_synthesis_request([{"text": args.text, "voice": args.voice}], args.output)
    
    else:
        handle_synthesis_request([{"text": "Hello, world!", "voice": "af_sky"}])

    print("\n--- Client Finished ---")