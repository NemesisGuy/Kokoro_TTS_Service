# gradio_app.py
import gradio as gr
import requests
import numpy as np
import io
import json
from scipy.io.wavfile import read as read_wav

# --- CONFIGURATION ---
API_BASE_URL = "http://127.0.0.1:8111"
VOICE_CHOICES = []

# --- Helper Function to Get Voices from API ---
def fetch_voices():
    global VOICE_CHOICES
    try:
        response = requests.get(f"{API_BASE_URL}/voices")
        response.raise_for_status()
        VOICE_CHOICES = response.json()
        return VOICE_CHOICES
    except Exception as e:
        print(f"Could not connect to API to fetch voices: {e}")
        return ["Error: API is not running or unreachable"]

# --- Core Function to Call the API and Play Audio ---
def call_api_and_play(script_payload: list):
    if not script_payload: return None, "Error: Script is empty."
    payload = {"script": script_payload}
    try:
        # Use the WAV endpoint for Gradio for maximum compatibility
        response = requests.post(f"{API_BASE_URL}/synthesize-wav", json=payload)
        response.raise_for_status()
        wav_bytes = response.content
        wav_data_io = io.BytesIO(wav_bytes)
        sample_rate, audio_data = read_wav(wav_data_io)
        return (sample_rate, audio_data), "Success!"
    except requests.exceptions.RequestException as e:
        error_msg = f"API Error. Is the server running?\nDetails: {e}"
        try: error_msg += f"\n\nServer Response:\n{response.json()}"
        except: pass
        return None, error_msg

# --- Handler Functions for Each Tab ---
def handle_simple_synthesis(text, voice, speed):
    return call_api_and_play([{"text": text, "voice": voice, "speed": speed}])

# --- THIS IS THE CORRECTED DIALOGUE HANDLER ---
def handle_dialogue_synthesis(json_string):
    # The input is now a STRING from the textbox, so we must parse it.
    try:
        data = json.loads(json_string)
        script = data.get("script", [])
        if not isinstance(script, list):
             return None, "Error: The 'script' key must contain a list of dialogue lines."
        return call_api_and_play(script)
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON format: {e}"
# --- END OF FIX ---

def handle_blend_synthesis(text, speed, enable1, voice1, weight1, enable2, voice2, weight2, enable3, voice3, weight3):
    blend_components = []
    if enable1 and weight1 > 0: blend_components.append({"voice": voice1, "weight": weight1})
    if enable2 and weight2 > 0: blend_components.append({"voice": voice2, "weight": weight2})
    if enable3 and weight3 > 0: blend_components.append({"voice": voice3, "weight": weight3})
    if not blend_components: return None, "No voices enabled for blending."
    script = [{"text": text, "blend_components": blend_components, "speed": speed}]
    return call_api_and_play(script)

# --- Gradio Interface ---
def create_gradio_app():
    voice_list = fetch_voices()
    
    # --- This is the example script for the editable textbox ---
    example_script_dict = {
        "script": [
            {"text": "This is a scripted conversation that you can edit.", "voice": "am_eric", "speed": 0.9},
            {"text": "Each line can have its own voice and timing.", "voice": "af_sky", "delay": 0.5},
            {"text": "This final line is spoken by a custom-blended character.", "blend_components": [{"voice": "am_adam", "weight": 0.7}, {"voice": "af_nova", "weight": 0.3}], "delay": 1.0, "speed": 1.1}
        ]
    }
    # We convert it to a nicely formatted string for the textbox
    example_script_str = json.dumps(example_script_dict, indent=2)

    with gr.Blocks(theme=gr.themes.Soft(font=[gr.themes.GoogleFont("Roboto")])) as app:
        gr.Markdown("# 🎤 Kokoro TTS API Showcase")
        gr.Markdown("A comprehensive interface to test all features of the running API server.")

        with gr.Tabs():
            with gr.TabItem("Simple Synthesis"):
                # (This tab is unchanged)
                gr.Markdown("### Test a single voice with speed control.")
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

            # --- THIS IS THE CORRECTED DIALOGUE TAB ---
            with gr.TabItem("Dialogue & Scripting"):
                gr.Markdown("### Test a full conversation. You can edit the JSON script below.")
                # We now use a Textbox, which is fully editable.
                dialogue_textbox = gr.Textbox(
                    label="Dialogue Script (JSON)",
                    value=example_script_str,
                    lines=15, # Give it plenty of space
                    elem_id="dialogue_json_editor" # for custom styling if needed
                )
                dialogue_btn = gr.Button("Synthesize Dialogue")
                dialogue_audio = gr.Audio(label="Output Audio", type="numpy")
                dialogue_status = gr.Textbox(label="Status", interactive=False)
                dialogue_btn.click(handle_dialogue_synthesis, [dialogue_textbox], [dialogue_audio, dialogue_status])
            # --- END OF FIX ---

            with gr.TabItem("Voice Blender"):
                # (This tab is unchanged)
                gr.Markdown("### Create a new, custom voice by blending multiple voices with specific weights.")
                with gr.Row():
                    with gr.Column(scale=3):
                        blend_text = gr.Textbox(label="Text to Speak", value="This is a unique voice created by blending several others.")
                        blend_speed = gr.Slider(label="Speed", minimum=0.5, maximum=2.0, step=0.1, value=1.0)
                        with gr.Group(): gr.Markdown("#### Voice Component 1"); blend1_enable = gr.Checkbox(label="Enabled", value=True); blend1_voice = gr.Dropdown(label="Voice 1", choices=voice_list, value="am_adam"); blend1_weight = gr.Slider(label="Weight 1", minimum=0.0, maximum=1.0, step=0.05, value=0.6)
                        with gr.Group(): gr.Markdown("#### Voice Component 2"); blend2_enable = gr.Checkbox(label="Enabled", value=True); blend2_voice = gr.Dropdown(label="Voice 2", choices=voice_list, value="af_nova"); blend2_weight = gr.Slider(label="Weight 2", minimum=0.0, maximum=1.0, step=0.05, value=0.4)
                        with gr.Group(): gr.Markdown("#### Voice Component 3"); blend3_enable = gr.Checkbox(label="Enabled", value=False); blend3_voice = gr.Dropdown(label="Voice 3", choices=voice_list, value="am_onyx"); blend3_weight = gr.Slider(label="Weight 3", minimum=0.0, maximum=1.0, step=0.05, value=0.0)
                        blend_btn = gr.Button("Synthesize Blended Voice")
                    with gr.Column(scale=2):
                        blend_audio = gr.Audio(label="Output Audio", type="numpy"); blend_status = gr.Textbox(label="Status", interactive=False)
                blend_inputs = [blend_text, blend_speed, blend1_enable, blend1_voice, blend1_weight, blend2_enable, blend2_voice, blend2_weight, blend3_enable, blend3_voice, blend3_weight]
                blend_btn.click(handle_blend_synthesis, blend_inputs, [blend_audio, blend_status])
    return app

if __name__ == "__main__":
    app = create_gradio_app()
    app.launch(inbrowser=True)