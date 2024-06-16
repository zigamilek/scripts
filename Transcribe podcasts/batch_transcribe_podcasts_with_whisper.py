import os
import argparse
import whisper

def load_transcribed_files(input_folder):
    transcribed_file_path = os.path.join(input_folder, 'already_transcribed.txt')
    if os.path.exists(transcribed_file_path):
        with open(transcribed_file_path, 'r') as f:
            return set(f.read().splitlines())
    return set()

def save_transcribed_file(input_folder, file_path):
    transcribed_file_path = os.path.join(input_folder, 'already_transcribed.txt')
    relative_path = os.path.relpath(file_path, input_folder)
    with open(transcribed_file_path, 'a') as f:
        f.write(relative_path + '\n')

def transcribe_audio_files_local(input_folder, model='base.en'):
    # Load Whisper model
    print(f"Loading Whisper model: {model}\n")
    model = whisper.load_model(model)

    # Load already transcribed files
    transcribed_files = load_transcribed_files(input_folder)

    # Iterate over all files in the input folder and subfolders
    for root, _, files in os.walk(input_folder):
        for filename in files:
            if filename.endswith('.mp3'):
                file_path = os.path.join(root, filename)
                relative_file_path = os.path.relpath(file_path, input_folder)
                
                print(f"Transcribing {file_path}...")

                if relative_file_path in transcribed_files:
                    print(f"    Already transcribed. Skipping {file_path}...\n")
                    continue

                # Transcribe audio file
                result = model.transcribe(file_path, verbose=False, fp16=False, language='English')
                transcription = result['text']

                # Create output folder in the same directory as the MP3 file
                output_folder = os.path.join(root, 'transcriptions')
                os.makedirs(output_folder, exist_ok=True)
                print(f"Output folder created at: {output_folder}\n")

                # Save transcription to a text file with UTF-8 encoding
                output_filename = f"{os.path.splitext(filename)[0]}-transcription.txt"
                output_file_path = os.path.join(output_folder, output_filename)
                with open(output_file_path, 'w', encoding='utf-8') as f:
                    f.write(transcription)

                print(f"    Finished {output_file_path}\n")

                # Save the file path to already_transcribed.txt file
                save_transcribed_file(input_folder, file_path)

def main():
    parser = argparse.ArgumentParser(description='Batch transcribe MP3 files using Whisper.')
    parser.add_argument('input_folder', type=str, help='Path to the input folder containing MP3 files.')
    parser.add_argument('--model', type=str, default='medium.en', help='Whisper model to use (default: medium.en)')

    args = parser.parse_args()

    transcribe_audio_files_local(args.input_folder, args.model)

if __name__ == '__main__':
    main()