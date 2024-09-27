import os
import nltk
import speech_recognition as sr
from moviepy.editor import VideoFileClip
import PyPDF2
import tkinter as tk
from tkinter import filedialog
from pydub import AudioSegment
from openai import OpenAI

# Download necessary NLTK data
nltk.download('punkt')

# Set the correct path for ffmpeg in pydub
AudioSegment.converter = r"C:\Users\rutvi\OneDrive - CloudJune (OPC) Private Limited\ffmpeg-7.0.2-full_build\ffmpeg-7.0.2-full_build\bin\ffmpeg.exe"

# Initialize the OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Functions to process files

def process_text_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as file:
        return file.read()

def process_pdf_file(filepath):
    with open(filepath, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ''
        for page in reader.pages:
            text += page.extract_text() or ""
    return text

def process_audio_file(filepath):
    recognizer = sr.Recognizer()
    
    if filepath.endswith('.mp3'):
        audio = AudioSegment.from_mp3(filepath)
        wav_path = filepath.replace('.mp3', '.wav')
        audio.export(wav_path, format='wav')
        filepath = wav_path
    
    audio_segment = AudioSegment.from_wav(filepath)
    duration_ms = len(audio_segment)
    
    if duration_ms > 60000:  # If audio is longer than 60 seconds
        chunk_length_ms = 60 * 1000
        chunks = [audio_segment[i:i + chunk_length_ms] for i in range(0, duration_ms, chunk_length_ms)]
        
        transcriptions = []
        for chunk in chunks:
            with sr.AudioFile(chunk.export(format="wav")) as source:
                audio_data = recognizer.record(source)
                try:
                    transcription = recognizer.recognize_google(audio_data)
                    transcriptions.append(transcription)
                except sr.UnknownValueError:
                    transcriptions.append("Audio not clear enough to transcribe")
                except sr.RequestError:
                    return "API request failed"
        
        return ' '.join(transcriptions)

    with sr.AudioFile(filepath) as source:
        audio_data = recognizer.record(source)
        try:
            return recognizer.recognize_google(audio_data)
        except sr.UnknownValueError:
            return "Audio not clear enough to transcribe"
        except sr.RequestError:
            return "API request failed"

def process_video_file(filepath):
    video = VideoFileClip(filepath)
    audio_path = 'extracted_audio.wav'
    video.audio.write_audiofile(audio_path)
    return process_audio_file(audio_path)

def extract_transcript_from_media(filepaths):
    transcripts = []
    
    for filepath in filepaths:
        if filepath.endswith('.txt'):
            print(f"Processing text file: {filepath}")
            transcript = process_text_file(filepath)
        elif filepath.endswith('.pdf'):
            print(f"Processing PDF file: {filepath}")
            transcript = process_pdf_file(filepath)
        elif filepath.endswith('.wav') or filepath.endswith('.mp3'):
            print(f"Processing audio file: {filepath}")
            transcript = process_audio_file(filepath)
        elif filepath.endswith('.mp4'):
            print(f"Processing video file: {filepath}")
            transcript = process_video_file(filepath)
        else:
            print(f"Unsupported file format: {filepath}")
            continue
        
        if transcript:
            transcripts.append(transcript)
    
    return '\n\n'.join(transcripts)

def get_file_paths():
    root = tk.Tk()
    root.withdraw()
    file_paths = filedialog.askopenfilenames(title="Select Files", 
                                             filetypes=(("All Supported Files", "*.txt;*.pdf;*.wav;*.mp3;*.mp4"),
                                                        ("Text files", "*.txt"),
                                                        ("PDF files", "*.pdf"),
                                                        ("Audio files", "*.wav;*.mp3"),
                                                        ("Video files", "*.mp4"),
                                                        ("All files", "*.*")))
    root.update()
    return list(file_paths)

def get_prompt(transcript):
    prompt_template = """You are an AI assistant specialized in analyzing transcripts and extracting key information. Your task is to read the following transcript and perform these steps:

1. Extract the most important keywords or phrases from the transcript.
2. Rank these keywords based on their importance to the overall context of the transcript.
3. For each keyword, provide a brief explanation of why it's important in the context of the transcript.

Please format your response as follows:

1. **Keyword 1** - Brief explanation of its importance
2. **Keyword 2** - Brief explanation of its importance
3. **Keyword 3** - Brief explanation of its importance
...and so on.

Aim to provide 10-15 keywords, unless the transcript is particularly short or lacks sufficient content.

Here's the transcript:

{transcript}

Please analyze this transcript and provide the ranked list of keywords with explanations."""

    return prompt_template.format(transcript=transcript)

def extract_keywords(transcript):
    prompt = get_prompt(transcript)
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that extracts and ranks keywords from transcripts."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000
    )
    
    return response.choices[0].message.content

def main():
    # Get file paths using tkinter file dialog
    file_list = get_file_paths()

    if not file_list:
        print("No files were selected.")
        return

    # Extract transcript from media files
    transcript = extract_transcript_from_media(file_list)

    # Save extracted transcript to a file
    with open('extracted_transcript.txt', 'w', encoding='utf-8') as output_file:
        output_file.write(transcript)

    print("Transcript saved to extracted_transcript.txt")

    # Extract and rank keywords
    keywords = extract_keywords(transcript)
    
    print("\nExtracted and Ranked Keywords:")
    print(keywords)
    
    # Save the keywords to a file
    with open('ranked_keywords.txt', 'w', encoding='utf-8') as file:
        file.write(keywords)
    
    print("\nKeywords have been saved to 'ranked_keywords.txt'")

if __name__ == "__main__":
    main()
