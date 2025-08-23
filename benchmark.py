# benchmark.py
import os
import sys
import time
import numpy as np
import requests
import platform
import psutil

from kokoro_onnx import Kokoro
from kokoro_onnx.tokenizer import Tokenizer

# --- Configuration (Unchanged) ---
MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')
BENCHMARK_TEXT = "This is a standard sentence for benchmarking the performance of different models."
BASE_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
MODELS_TO_BENCHMARK = [
    {"filename": "kokoro-v1.0.onnx", "url": BASE_URL + "kokoro-v1.0.onnx", "description": "Full Precision (FP32)"},
    {"filename": "kokoro-v1.0.fp16.onnx", "url": BASE_URL + "kokoro-v1.0.fp16.onnx", "description": "Half Precision (FP16)"},
    {"filename": "kokoro-v1.0.int8.onnx", "url": BASE_URL + "kokoro-v1.0.int8.onnx", "description": "Quantized (INT8)"}
]

# (The download_file_if_missing and print_recommendations functions are unchanged)
def download_file_if_missing(filename, url):
    file_path = os.path.join(MODELS_DIR, filename)
    if not os.path.exists(file_path):
        print(f"'{filename}' not found. Downloading from GitHub...")
        try:
            with requests.get(url, stream=True) as r:
                r.raise_for_status();
                with open(file_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
            print("Download complete.")
        except Exception as e: print(f"FATAL ERROR: Failed to download '{filename}'. Error: {e}"); sys.exit(1)
    return file_path

def print_recommendations(results):
    if not results: return
    fastest_inference = min(results, key=lambda x: x['rtf']); highest_quality = next((r for r in results if r['name'].endswith('.onnx') and 'fp' not in r['name'] and 'int' not in r['name']), None); best_balanced = next((r for r in results if r['name'].endswith('fp16.onnx')), fastest_inference)
    print("\n\n" + "="*70); print("--- Recommendations ---"); print("="*70)
    print(f"\n RECOMMENDED FOR YOUR API (Best Balance):"); print(f"   -> {best_balanced['name']}"); print(f"      Reason: Offers a good balance of speed (RTF: {best_balanced['rtf']:.2f}) and memory usage ({best_balanced['mem_usage']:.0f} MB). Ideal for a server.")
    print(f"\n FOR ABSOLUTE FASTEST PERFORMANCE:"); print(f"   -> {fastest_inference['name']}"); print(f"      Reason: Lowest Real-Time Factor (RTF: {fastest_inference['rtf']:.2f}), generates audio fastest.")
    int8_model = next((r for r in results if 'int8' in r['name']), None)
    if int8_model and int8_model['rtf'] > fastest_inference['rtf']: print(f"      NOTE: The int8 model was surprisingly slower (RTF: {int8_model['rtf']:.2f}) in this test.")
    if highest_quality: print(f"\n FOR HIGHEST AUDIO QUALITY (Offline Tasks):"); print(f"   -> {highest_quality['name']}"); print(f"      Reason: Highest fidelity, but uses the most memory ({highest_quality['mem_usage']:.0f} MB).")
    print("\n" + "="*70); print("\n ACTION: To use the recommended model for your API, update the 'MODEL_FILE' variable"); print(f"          in your 'api/api.py' script to '{best_balanced['name']}'.")

def print_system_info():
    print("\n\n" + "="*70); print("--- System Information ---"); print("="*70)
    print(f"  CPU: {platform.processor()}"); print(f"  Cores: {psutil.cpu_count(logical=False)} Physical, {psutil.cpu_count(logical=True)} Logical"); total_ram_gb = psutil.virtual_memory().total / (1024**3); print(f"  Total RAM: {total_ram_gb:.2f} GB"); print("="*70)

if __name__ == "__main__":
    print("--- Kokoro ONNX Benchmark Tool ---")
    os.makedirs(MODELS_DIR, exist_ok=True)
    voices_path = download_file_if_missing("voices-v1.0.bin", BASE_URL + "voices-v1.0.bin")
    tokenizer = Tokenizer()
    phonemes = tokenizer.phonemize(BENCHMARK_TEXT, lang="en-us")
    results = []

    # --- NEW: Get the current process to monitor its memory ---
    process = psutil.Process(os.getpid())
    # Get baseline memory usage before any models are loaded
    mem_before_all = process.memory_info().rss / (1024 * 1024)

    for model_info in MODELS_TO_BENCHMARK:
        filename = model_info["filename"]
        print(f"\n--- Benchmarking: {filename} ({model_info['description']}) ---")
        model_path = download_file_if_missing(filename, model_info["url"])
        file_size_mb = os.path.getsize(model_path) / (1024 * 1024)
        
        # --- UPDATED: Measure memory at each step ---
        print("Loading model...")
        start_load_time = time.perf_counter()
        kokoro_instance = Kokoro(model_path, voices_path)
        end_load_time = time.perf_counter()
        load_time = end_load_time - start_load_time
        
        # Measure peak memory after loading the model
        mem_after_load = process.memory_info().rss / (1024 * 1024)
        
        print("Running inference...")
        start_infer_time = time.perf_counter()
        samples, sample_rate = kokoro_instance.create(phonemes, voice="am_adam", is_phonemes=True)
        end_infer_time = time.perf_counter()

        # Measure peak memory after inference (includes model and audio data)
        mem_after_infer = process.memory_info().rss / (1024 * 1024)
        # The model's memory usage is the increase from our baseline
        model_mem_usage = mem_after_infer - mem_before_all
        
        inference_time = end_infer_time - start_infer_time
        audio_duration = len(samples) / sample_rate
        rtf = inference_time / audio_duration
        
        results.append({
            "name": filename, "size": file_size_mb, "load_time": load_time,
            "infer_time": inference_time, "duration": audio_duration, "rtf": rtf,
            "mem_usage": model_mem_usage # Add the new metric to the results
        })
        print("Benchmark complete for this model.")
        # Clean up the instance to release memory before the next run
        del kokoro_instance

    print_system_info()

    # --- UPDATED: The final results table now includes memory usage ---
    print("\n\n" + "="*115)
    print("--- Benchmark Results ---")
    print("="*115)
    print(f"{'Model Name':<25} | {'Size (MB)':<12} | {'Load Time (s)':<15} | {'Inference Time (s)':<20} | {'Peak RAM Usage (MB)':<22} | {'Real-Time Factor':<20}")
    print("-" * 120)
    for res in sorted(results, key=lambda x: x['rtf']):
        print(f"{res['name']:<25} | {res['size']:<12.2f} | {res['load_time']:<15.4f} | {res['infer_time']:<20.4f} | {res['mem_usage']:<22.2f} | {res['rtf']:<20.4f}")
    print("="*115)
    print("\n* Peak RAM Usage: The additional memory used by the script after loading and running this model.")
    print("* Real-Time Factor (RTF): Time to generate 1s of audio (lower is better).")

    print_recommendations(results)
    
    print("\n--- Benchmark Finished ---")