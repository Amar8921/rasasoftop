import speech_recognition as sr
import pyttsx3
import requests

# Initialize TTS engine
engine = pyttsx3.init()

def speak(text):
    """Convert text to speech."""
    engine.say(text)
    engine.runAndWait()

def listen():
    """Capture voice input and convert it to text."""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        # print("Listening...")
        audio = recognizer.listen(source)

        try:
            text = recognizer.recognize_google(audio)
            print(f"You: {text}")
            return text
        except sr.UnknownValueError:
            # print("Sorry, I couldn't understand. Could you repeat?")
            return None
        except sr.RequestError as e:
            print(f"Error with the speech recognition service: {e}")
            return None

def interact_with_rasa(user_input):
    """Send user input to Rasa and get the response."""
    rasa_url = "http://localhost:5005/webhooks/rest/webhook"
    payload = {"sender": "user", "message": user_input}
    try:
        response = requests.post(rasa_url, json=payload)
        print(f"Rasa response: {response.json()}")  # Add this line to debug
        if response.status_code == 200:
            responses = response.json()
            return responses
        return "I'm sorry, I didn't understand that."
    except Exception as e:
        print(f"Error interacting with Rasa: {e}")
        return "I couldn't connect to the assistant."

def main():
    """Main loop for the voice assistant."""
    speak("Hello! I am your voice assistant. How can I help you?")
    while True:
        # print("Listening...")  # Print "Listening..." *before* calling listen()
        user_input = listen()
        if user_input:
            if "exit" in user_input.lower() or "quit" in user_input.lower():
                speak("Goodbye! Have a nice day!")
                break

            # Send the input to Rasa
            response = interact_with_rasa(user_input)
            print(response)
            # speak(response)

if __name__ == "__main__":
    main()