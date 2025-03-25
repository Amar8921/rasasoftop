import pyttsx3

def text_to_wav(text, output_file="output.wav", rate=150, volume=1.0):
    """
    Converts the given text to speech and saves it as a WAV file with improved clarity.

    Args:
        text (str): The text to be converted to speech.
        output_file (str, optional): The filename for the output WAV file. Defaults to "output.wav".
        rate (int, optional): Speech rate (words per minute). Lower values make it slower.
        volume (float, optional): Volume level (0.0 to 1.0). Defaults to 1.0.
    """
    engine = pyttsx3.init()

    try:
        # Adjust speech rate (default ~200, reduce for clarity)
        engine.setProperty('rate', rate)

        # Adjust volume (default is 1.0)
        engine.setProperty('volume', volume)

        # Save speech to a WAV file
        engine.save_to_file(text, output_file)

        # Wait for the saving to complete
        engine.runAndWait()

        print(f"Successfully saved speech to: {output_file}")

    except Exception as e:
        print(f"Error during text-to-speech and saving: {e}")

if __name__ == "__main__":
    text_to_convert = "create."
    output_wav_filename = "create.wav"

    # Adjust the rate for slower speech (default ~200, reducing to 150)
    text_to_wav(text_to_convert, output_wav_filename, rate=130, volume=1.0)

    print(f"Text converted: '{text_to_convert}'")
    print(f"WAV file saved as: '{output_wav_filename}'")
