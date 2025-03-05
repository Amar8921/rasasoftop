from flask import Flask, request, jsonify
import speech_recognition as sr
import requests
import os
import tempfile  # For handling temporary files

app = Flask(__name__)

# --- Rasa Bot Configuration ---
RASA_API_URL = "http://localhost:5005/webhooks/rest/webhook"  # Replace if your Rasa server is different

# --- Speech Recognition Setup (Initially using speech_recognition - Google Web Speech API) ---
recognizer = sr.Recognizer()

def recognize_speech_from_audio_file(audio_file_path):
    """Transcribes speech from an audio file using speech_recognition (Google Web Speech API).
       **Replace this function later to use Google Cloud Speech-to-Text for backend processing.**
    """
    try:
        with sr.AudioFile(audio_file_path) as source:
            audio_data = recognizer.record(source)  # Read the entire audio file
        text = recognizer.recognize_google(audio_data) # Using Google Web Speech API - replace with cloud STT later
        return text
    except sr.UnknownValueError:
        return "Speech Recognition could not understand audio"
    except sr.RequestError as e:
        return f"Could not request results from Speech Recognition service; {e}"
    except Exception as e: # Catch other potential errors
        return f"Error during speech recognition: {e}"


def send_message_to_rasa(message):
    """Sends a message to the Rasa bot API and returns the bot's response."""
    payload = {"message": message}
    headers = {'Content-type': 'application/json'}
    try:
        response = requests.post(RASA_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        rasa_response_data = response.json()
        if rasa_response_data:
            return rasa_response_data
        else:
            return "Sorry, I didn't get a response from the bot."
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with Rasa API: {e}")
        return "Error communicating with the bot. Please check the Rasa server."


@app.route('/voice_input', methods=['POST'])
def voice_input():
    """API endpoint to receive a WAV audio file and return Rasa bot's text response."""
    if 'audio_file' not in request.files:
        return jsonify({"error": "No audio_file part"}), 400

    audio_file = request.files['audio_file']

    if audio_file.filename == '':
        return jsonify({"error": "No selected audio_file"}), 400

    if audio_file: # You might want to add more robust file type checking here (e.g., check MIME type)
        try:
            # Save the uploaded file temporarily
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav") # Create a temporary file
            audio_file.save(temp_file.name) # Save uploaded file to temp file path
            temp_file_path = temp_file.name
            temp_file.close() # Close the temp file object

            transcribed_text = recognize_speech_from_audio_file(temp_file_path) # Recognize speech from the temp file
            print(f"Transcribed Text from Audio File: {transcribed_text}")

            # Clean up the temporary file
            os.remove(temp_file_path)

            if transcribed_text.startswith("Error"): # Check if speech recognition returned an error string
                return jsonify({"bot_response": "Sorry, I couldn't understand your speech.", "stt_error": transcribed_text}), 200 # Return error to UI

            rasa_response = send_message_to_rasa(transcribed_text)
            print(f"Rasa Bot Response: {rasa_response}")

            return jsonify({"bot_response": rasa_response, "user_text": transcribed_text}), 200 # Include user_text for UI to display

        except Exception as e:
            print(f"API Endpoint Error: {e}")
            return jsonify({"error": "Internal server error", "details": str(e)}), 500
    else:
        return jsonify({"error": "Allowed audio file types are wav"}), 400 # More specific error message for file type if you implement checks


if __name__ == '__main__':
    print("Backend API for Voice Rasa Bot started (WAV file upload version)...")
    app.run(debug=True, host='0.0.0.0', port=5001)