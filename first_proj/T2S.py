import pyttsx3

def text_to_wav(text, output_file="output.wav"):
    """
    Converts the given text to speech and saves it as a WAV file.

    Args:
        text (str): The text to be converted to speech.
        output_file (str, optional): The filename for the output WAV file.
                                     Defaults to "output.wav".
    """
    engine = pyttsx3.init()

    try:
        # Save speech to a WAV file
        engine.save_to_file(text, output_file)

        # Wait for the saving to complete
        engine.runAndWait()

        print(f"Successfully saved speech to: {output_file}")

    except Exception as e:
        print(f"Error during text-to-speech and saving: {e}")

if __name__ == "__main__":
    text_to_convert = "Staff Attendance"
    output_wav_filename = "staff_attendance.wav"

    text_to_wav(text_to_convert, output_wav_filename)
    print(f"Text converted: '{text_to_convert}'")
    print(f"WAV file saved as: '{output_wav_filename}'")