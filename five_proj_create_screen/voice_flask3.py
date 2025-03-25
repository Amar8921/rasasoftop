from flask import Flask
import requests
from vosk import Model, KaldiRecognizer
import wave
import json
from flask import Flask, request, jsonify

vosk_model = Model("vosk-model-small-en-us-0.15")  # Load Vosk Model

app = Flask(__name__)

def transcribe_with_vosk(audio_file):
    """Use Vosk for speech-to-text"""
    audio_path = "temp_audio.wav"
    audio_file.save(audio_path)  # Save the file temporarily

    wf = wave.open(audio_path, "rb")
    rec = KaldiRecognizer(vosk_model, wf.getframerate())

    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        rec.AcceptWaveform(data)

    result = json.loads(rec.FinalResult())
    return result.get("text", "")  # Extract text

def interact_with_rasa(user_input):
    """Send user input to Rasa and get the response."""
    rasa_url = "http://localhost:5005/webhooks/rest/webhook"
    payload = {"sender": "user", "message": user_input}
    try:
        response = requests.post(rasa_url, json=payload)
        if response.status_code == 200:
            return response.json()
        return "I'm sorry, I didn't understand that."
    except Exception as e:
        return f"Error connecting to Rasa: {e}"

@app.route('/voice', methods=['POST'])
def voice_assistant():
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files['audio']

    try:
        user_input = transcribe_with_vosk(audio_file)  # Use Vosk
        print(f"Recognized (Vosk): {user_input}")

        if not user_input:
            return jsonify({"response": "Sorry, I couldn't understand that."})

        response_text = interact_with_rasa(user_input)
    except Exception as e:
        response_text = f"Error processing audio: {e}"

    return jsonify({"response": response_text})

if __name__ == "__main__":
    app.run(debug=True)
