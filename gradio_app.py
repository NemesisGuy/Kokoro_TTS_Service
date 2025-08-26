import gradio as gr
import requests
import numpy as np
import io
import json
import time
import os
from scipy.io.wavfile import read as read_wav

API_BASE_URL = os.environ.get("API_URL", "http://localhost:8000")
VOICE_CHOICES = []
FALLBACK_MODELS = [
    "kokoro-v1.0.onnx",
    "kokoro-v1.0.fp16.onnx",
    "kokoro-v1.0.int8.onnx"
]

def fetch_voices_with_retry(max_retries=10, delay_seconds=5):
    global VOICE_CHOICES
    for attempt in range(max_retries):
        try:
            print(f"Attempting to connect to API (Attempt {attempt + 1}/{max_retries})...")
            response = requests.get(f"{API_BASE_URL}/voices", timeout=10)
            response.raise_for_status()
            VOICE_CHOICES = response.json()
            print("Successfully connected to API and fetched voices.")
            return VOICE_CHOICES
        except requests.exceptions.RequestException as e:
            print(f"API not ready yet ({e}). Waiting {delay_seconds} seconds...")
            time.sleep(delay_seconds)
    print("FATAL: Could not connect to API after multiple retries.")
    return ["Error: API is not running or unreachable"]

def call_api_and_play(script_payload: list, progress=gr.Progress()):
    if not script_payload:
        return None, "Error: Script is empty."
    payload = {"script": script_payload}
    try:
        start_time = time.time()
        progress(0, desc="Starting synthesis...")
        response = requests.post(f"{API_BASE_URL}/synthesize-wav", json=payload, timeout=600)
        progress(0.5, desc="Processing response...")
        response.raise_for_status()
        elapsed_time = time.time() - start_time
        wav_bytes = response.content
        wav_data_io = io.BytesIO(wav_bytes)
        sample_rate, audio_data = read_wav(wav_data_io)
        progress(1.0, desc="Synthesis complete!")
        return (sample_rate, audio_data), f"Success! Synthesis took {elapsed_time:.2f} seconds."
    except requests.exceptions.Timeout:
        return None, "Error: API request timed out after 600 seconds. Try splitting the chapter into smaller scripts or using /synthesize-stream."
    except requests.exceptions.RequestException as e:
        error_msg = f"API Error: {str(e)}"
        try:
            error_msg += f"\n\nServer Response:\n{response.json()}"
        except:
            pass
        return None, error_msg

def handle_simple_synthesis(text, voice, speed):
    return call_api_and_play([{"text": text, "voice": voice, "speed": speed}])

def handle_dialogue_synthesis(json_data, progress=gr.Progress()):
    try:
        script_data = json.loads(json_data)
        script = script_data.get("script", [])
        if not isinstance(script, list):
            return None, "Error: 'script' key must contain a list."
        return call_api_and_play(script, progress)
    except json.JSONDecodeError as e:
        return None, f"Error: Invalid JSON format. {str(e)}"
    except Exception as e:
        return None, f"Error: Failed to process dialogue script. {str(e)}"

def handle_blend_synthesis(text, speed, enable1, voice1, weight1, enable2, voice2, weight2, enable3, voice3, weight3):
    blend_components = []
    if enable1 and weight1 > 0:
        blend_components.append({"voice": voice1, "weight": weight1})
    if enable2 and weight2 > 0:
        blend_components.append({"voice": voice2, "weight": weight2})
    if enable3 and weight3 > 0:
        blend_components.append({"voice": voice3, "weight": weight3})
    if not blend_components:
        return None, "No voices enabled for blending."
    script = [{"text": text, "blend_components": blend_components, "speed": speed}]
    return call_api_and_play(script)

def fetch_benchmark_results():
    try:
        start_time = time.time()
        response = requests.get(f"{API_BASE_URL}/benchmark", timeout=120)
        response.raise_for_status()
        elapsed_time = time.time() - start_time
        data = response.json()
        results = data.get("results", [])
        system_info = data.get("system_info", {})
        recommendation = data.get("recommendation", {})
        
        if not results:
            raise ValueError("No benchmark results returned from API.")
        
        system_text = f"""
        **System Information**
        - CPU: {system_info.get('cpu', 'Unknown')}
        - Physical Cores: {system_info.get('physical_cores', 'Unknown')}
        - Logical Cores: {system_info.get('logical_cores', 'Unknown')}
        - Total RAM: {system_info.get('total_ram_gb', 'Unknown'):.2f} GB
        """
        
        table = "| Model | Description | Size (MB) | Load Time (s) | Inference Time (s) | RTF | Memory Usage (MB) |\n"
        table += "|-------|-------------|-----------|---------------|--------------------|-----|------------------|\n"
        for res in sorted(results, key=lambda x: x["rtf"]):
            table += f"| {res['model_name']} | {res['description']} | {res['size_mb']:.2f} | {res['load_time']:.4f} | {res['inference_time']:.4f} | {res['rtf']:.4f} | {res['mem_usage']:.2f} |\n"
        
        rec_text = f"""
        **Recommendations**
        - **Best Balanced**: {recommendation.get('best_balanced', {}).get('model_name', 'None')} ({recommendation.get('best_balanced', {}).get('description', 'None')})
          - Reason: {recommendation.get('best_balanced', {}).get('reason', 'None')}
        - **Fastest**: {recommendation.get('fastest', {}).get('model_name', 'None')} ({recommendation.get('fastest', {}).get('description', 'None')})
          - Reason: {recommendation.get('fastest', {}).get('reason', 'None')}
        """
        if recommendation.get('highest_quality', {}).get('model_name'):
            rec_text += f"""
        - **Highest Quality**: {recommendation['highest_quality']['model_name']} ({recommendation['highest_quality']['description']})
          - Reason: {recommendation['highest_quality']['reason']}
        """
        
        optimal_model = recommendation.get("best_balanced", {}).get("model_name", "")
        model_choices = [f"{r['model_name']} (optimal)" if r['model_name'] == optimal_model else r['model_name'] for r in results]
        default_model = f"{optimal_model} (optimal)" if optimal_model else None
        
        return system_text + "\n\n" + table + "\n\n" + rec_text, model_choices, default_model, f"Benchmark completed successfully in {elapsed_time:.2f} seconds."
    except requests.exceptions.Timeout:
        error_msg = "Error: Benchmark request timed out after 120 seconds. Try using the INT8 model or increasing server resources."
        model_choices = FALLBACK_MODELS
        default_model = FALLBACK_MODELS[1] if FALLBACK_MODELS else None
        return error_msg, model_choices, default_model, error_msg
    except requests.exceptions.RequestException as e:
        error_msg = f"Error: Failed to fetch benchmark results. {str(e)}"
        model_choices = FALLBACK_MODELS
        default_model = FALLBACK_MODELS[1] if FALLBACK_MODELS else None
        return error_msg, model_choices, default_model, error_msg
    except ValueError as e:
        error_msg = f"Error: Invalid benchmark response. {str(e)}"
        model_choices = FALLBACK_MODELS
        default_model = FALLBACK_MODELS[1] if FALLBACK_MODELS else None
        return error_msg, model_choices, default_model, error_msg

def set_model(model_name):
    if not model_name:
        return "Error: No model selected."
    model_name = model_name.replace(" (optimal)", "")
    try:
        response = requests.post(f"{API_BASE_URL}/set-model", json={"model_name": model_name}, timeout=10)
        response.raise_for_status()
        return f"Successfully switched to model: {model_name}"
    except requests.exceptions.RequestException as e:
        error_msg = f"Error: Failed to set model. {str(e)}"
        try:
            error_msg += f"\n\nServer Response:\n{response.json()}"
        except:
            pass
        return error_msg

def create_gradio_app():
    voice_list = fetch_voices_with_retry()
    example_script_dict = {"script": [{"text": "This is an editable script.", "voice": "am_eric", "speed": 0.9}, {"text": "Each line has its own timing and voice.", "voice": "af_sky", "delay": 0.5}]}
    example_script_str = json.dumps(example_script_dict, indent=2)

    with gr.Blocks(theme=gr.themes.Soft(font=[gr.themes.GoogleFont("Roboto")])) as app:
        gr.Markdown("# 🎤 Kokoro TTS Service")
        with gr.Tabs():
            with gr.TabItem("Simple Synthesis"):
                with gr.Row():
                    with gr.Column(scale=3):
                        simple_text = gr.Textbox(label="Text", lines=3, value="Hello, this is a test of a single voice.")
                        simple_voice = gr.Dropdown(label="Voice", choices=voice_list, value=voice_list[0] if voice_list else None)
                        simple_speed = gr.Slider(label="Speed", minimum=0.5, maximum=2.0, step=0.1, value=1.0)
                        simple_btn = gr.Button("Synthesize")
                    with gr.Column(scale=2):
                        simple_audio = gr.Audio(label="Output Audio", type="numpy")
                        simple_status = gr.Textbox(label="Status", interactive=False)
                simple_btn.click(handle_simple_synthesis, [simple_text, simple_voice, simple_speed], [simple_audio, simple_status])
            
            with gr.TabItem("Dialogue & Scripting"):
                dialogue_textbox = gr.Textbox(label="Dialogue Script (JSON)", value=example_script_str, lines=15)
                dialogue_btn = gr.Button("Synthesize Dialogue")
                dialogue_audio = gr.Audio(label="Output Audio", type="numpy")
                dialogue_status = gr.Textbox(label="Status", interactive=False)
                dialogue_btn.click(handle_dialogue_synthesis, [dialogue_textbox], [dialogue_audio, dialogue_status])
            
            with gr.TabItem("Voice Blender"):
                with gr.Row():
                    with gr.Column(scale=3):
                        blend_text = gr.Textbox(label="Text to Speak", value="This is a unique voice created by blending several others.")
                        blend_speed = gr.Slider(label="Speed", minimum=0.5, maximum=2.0, step=0.1, value=1.0)
                        with gr.Group():
                            gr.Markdown("#### Voice Component 1")
                            blend1_enable = gr.Checkbox(label="Enabled", value=True)
                            blend1_voice = gr.Dropdown(label="Voice 1", choices=voice_list, value="am_adam")
                            blend1_weight = gr.Slider(label="Weight 1", minimum=0.0, maximum=1.0, step=0.05, value=0.6)
                        with gr.Group():
                            gr.Markdown("#### Voice Component 2")
                            blend2_enable = gr.Checkbox(label="Enabled", value=True)
                            blend2_voice = gr.Dropdown(label="Voice 2", choices=voice_list, value="af_nova")
                            blend2_weight = gr.Slider(label="Weight 2", minimum=0.0, maximum=1.0, step=0.05, value=0.4)
                        with gr.Group():
                            gr.Markdown("#### Voice Component 3")
                            blend3_enable = gr.Checkbox(label="Enabled", value=False)
                            blend3_voice = gr.Dropdown(label="Voice 3", choices=voice_list, value="am_onyx")
                            blend3_weight = gr.Slider(label="Weight 3", minimum=0.0, maximum=1.0, step=0.05, value=0.0)
                        blend_btn = gr.Button("Synthesize Blended Voice")
                    with gr.Column(scale=2):
                        blend_audio = gr.Audio(label="Output Audio", type="numpy")
                        blend_status = gr.Textbox(label="Status", interactive=False)
                blend_inputs = [blend_text, blend_speed, blend1_enable, blend1_voice, blend1_weight, blend2_enable, blend2_voice, blend2_weight, blend3_enable, blend3_voice, blend3_weight]
                blend_btn.click(handle_blend_synthesis, blend_inputs, [blend_audio, blend_status])
            
            with gr.TabItem("Benchmark"):
                with gr.Row():
                    with gr.Column(scale=3):
                        benchmark_btn = gr.Button("Run Benchmark")
                        model_select = gr.Dropdown(label="Select Model", choices=FALLBACK_MODELS, value=FALLBACK_MODELS[1] if FALLBACK_MODELS else None)
                        set_model_btn = gr.Button("Set Model")
                    with gr.Column(scale=2):
                        benchmark_output = gr.Textbox(label="Benchmark Results", lines=20, interactive=False)
                        benchmark_status = gr.Textbox(label="Status", interactive=False)
                benchmark_btn.click(fetch_benchmark_results, [], [benchmark_output, model_select, model_select, benchmark_status])
                set_model_btn.click(set_model, [model_select], [benchmark_status])

    return app

if __name__ == "__main__":
    app = create_gradio_app()
    app.launch(server_name="0.0.0.0", server_port=7860)