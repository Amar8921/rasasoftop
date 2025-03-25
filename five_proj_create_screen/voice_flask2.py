from flask import Flask, request, jsonify
import speech_recognition as sr
import requests
import os
import whisper
from vosk import Model, KaldiRecognizer
import wave

app = Flask(__name__)

# Load Whisper model (choose "tiny", "base", or "small" for speed)
whisper_model = whisper.load_model("base")

# Load Vosk model (download a model from https://alphacephei.com/vosk/models)
# vosk_model = Model("vosk-model-small-en-us-0.15")  # Adjust path if needed

def transcribe_audio(audio_file, method="whisper"):
    """Convert speech to text using Whisper, Vosk, or Google API."""
    recognizer = sr.Recognizer()
    
    if method == "whisper":
        audio_path = "temp_audio.wav"
        audio_file.save(audio_path)  # Save audio temporarily
        result = whisper_model.transcribe(audio_path)
        os.remove(audio_path)  # Cleanup
        return result["text"]
    
    # elif method == "vosk":
    #     audio_path = "temp_audio.wav"
    #     audio_file.save(audio_path)
    #     wf = wave.open(audio_path, "rb")
    #     rec = KaldiRecognizer(vosk_model, wf.getframerate())
        
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                pass
        
        result = rec.FinalResult()
        os.remove(audio_path)
        return result
    
    else:  # Default to Google Speech Recognition (Online)
        with sr.AudioFile(audio_file) as source:
            audio = recognizer.record(source)
            return recognizer.recognize_google(audio)

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
    """Endpoint for voice-based chatbot."""
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    
    audio_file = request.files['audio']

    try:
        user_input = transcribe_audio(audio_file, method="whisper")  # Change method: "whisper", "vosk", or "google"
        print(f"You: {user_input}")

        if "exit" in user_input.lower() or "quit" in user_input.lower():
            response_text = "Goodbye! Have a nice day!"
        else:
            response_text = interact_with_rasa(user_input)
    except Exception as e:
        response_text = f"Error processing audio: {e}"
    print(f"📥 Rasa Response: {response_text}")  # Debugging API Response


    return jsonify({"response": response_text})

if __name__ == "__main__":
    app.run(debug=True)
