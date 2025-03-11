from flask import Flask, request, jsonify
import speech_recognition as sr
import requests

app = Flask(__name__)

def interact_with_rasa(user_input):
    """Send user input to Rasa and get the response."""
    rasa_url = "http://localhost:5005/webhooks/rest/webhook"
    payload = {"sender": "user", "message": user_input}
    print(f"Sending to Rasa: {user_input}")  # Debugging step
    try:
        response = requests.post(rasa_url, json=payload)
        if response.status_code == 200:
            responses = response.json()
            print(f"Rasa Response: {responses}")  # Debugging step
            return responses
        return "I'm sorry, I didn't understand that."
    except Exception as e:
        print(f"Error interacting with Rasa: {e}")
        return "I couldn't connect to the assistant."


@app.route('/voice', methods=['POST'])
def voice_assistant():
    """Endpoint for the voice assistant."""
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files['audio']
    recognizer = sr.Recognizer()

    try:
        audio_data = sr.AudioFile(audio_file)
        with audio_data as source:
            audio = recognizer.record(source)
            user_input = recognizer.recognize_google(audio)
            print(f"You: {user_input}")

            if "exit" in user_input.lower() or "quit" in user_input.lower():
                response_text = "Goodbye! Have a nice day!"
            else:
                response_text = interact_with_rasa(user_input)
    except sr.UnknownValueError:
        response_text = "Sorry, I couldn't understand that."
    except sr.RequestError as e:
        response_text = f"Error with the speech recognition service: {e}"

    return jsonify({"response": response_text})

if __name__ == "__main__":
    app.run(debug=True)
