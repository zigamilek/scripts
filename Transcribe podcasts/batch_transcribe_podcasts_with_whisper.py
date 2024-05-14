import os
import argparse
import whisper
from openai import OpenAI
from pydub import AudioSegment

## todo:
    # print messages to show progress: which folder, which file
    # keep a txt file with filepaths that have already been transcribed
    # add timestamps, segments, whatever?

def transcribe_audio_files_local(input_folder, model_name='base.en'):
    # Load Whisper model
    model = whisper.load_model(model_name)

    # Create output folder if it doesn't exist
    output_folder = os.path.join(input_folder, 'transcriptions')
    os.makedirs(output_folder, exist_ok=True)

    # Iterate over all files in the input folder
    for filename in os.listdir(input_folder):
        if filename.endswith('.mp3'):
            file_path = os.path.join(input_folder, filename)
            
            # Transcribe audio file
            result = model.transcribe(file_path, verbose=False, fp16=False, language='English')
            transcription = result['text']

            # Save transcription to a text file
            output_filename = f"{os.path.splitext(filename)[0]}-transcription.txt"
            output_file_path = os.path.join(output_folder, output_filename)
            with open(output_file_path, 'w') as f:
                f.write(transcription)

            print(f"Transcribed {filename} and saved to {output_filename}")

def split_audio_file(file_path, segment_length=10*60*1000):
    song = AudioSegment.from_mp3(file_path)
    segments = []
    
    for i in range(0, len(song), segment_length):
        segment = song[i:i+segment_length]
        segment_path = f"{os.path.splitext(file_path)[0]}_part{i//segment_length}.mp3"
        segment.export(segment_path, format="mp3")
        segments.append(segment_path)
    
    return segments

def transcribe_audio_files_api(input_folder):
    # Initialize OpenAI client
    client = OpenAI(
        api_key="REMOVED_OPENAI_API_KEY"
    )

    # Create output folder if it doesn't exist
    output_folder = os.path.join(input_folder, 'transcriptions')
    os.makedirs(output_folder, exist_ok=True)

    # Iterate over all files in the input folder
    for filename in os.listdir(input_folder):
        if filename.endswith('.mp3'):
            file_path = os.path.join(input_folder, filename)
            
            # Split the audio file into 10-minute segments
            segments = split_audio_file(file_path)
            
            transcription = ""
            for segment_path in segments:
                # Open audio file segment
                with open(segment_path, 'rb') as audio_file:
                    # Transcribe audio file using Whisper API
                    response = client.audio.transcriptions.create(
                        model="whisper-1", 
                        file=audio_file, 
                        response_format="text"
                    )
                    transcription += response + "\n"

                # Remove the segment file after transcribing
                os.remove(segment_path)

            # Save transcription to a text file
            output_filename = f"{os.path.splitext(filename)[0]}-transcription.txt"
            output_file_path = os.path.join(output_folder, output_filename)
            with open(output_file_path, 'w') as f:
                f.write(transcription)

            print(f"Transcribed {filename} and saved to {output_filename}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Batch transcribe MP3 files using Whisper.')
    parser.add_argument('input_folder', type=str, help='Path to the input folder containing MP3 files.')
    parser.add_argument('--mode', type=str, choices=['local', 'api'], default='local', help='Choose between local Whisper or Whisper API.')
    parser.add_argument('--model_name', type=str, default='base', help='Whisper model name to use (only for local mode).')

    args = parser.parse_args()

    if args.mode == 'local':
        transcribe_audio_files_local(args.input_folder, args.model_name)
    elif args.mode == 'api':
        transcribe_audio_files_api(args.input_folder)