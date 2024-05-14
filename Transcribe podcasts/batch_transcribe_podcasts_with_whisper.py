import os
import argparse
import whisper

## todo:
    # add timestamps, segments, whatever?

def load_transcribed_files(input_folder):
    transcribed_file_path = os.path.join(input_folder, 'transcribed.txt')
    if os.path.exists(transcribed_file_path):
        with open(transcribed_file_path, 'r') as f:
            return set(f.read().splitlines())
    return set()

def save_transcribed_file(input_folder, file_path):
    transcribed_file_path = os.path.join(input_folder, 'transcribed.txt')
    with open(transcribed_file_path, 'a') as f:
        f.write(file_path + '\n')

def transcribe_audio_files_local(input_folder, model='base.en'):
    # Load Whisper model
    print(f"Loading Whisper model: {model}\n")
    model = whisper.load_model(model)

    # Create output folder if it doesn't exist
    output_folder = os.path.join(input_folder, 'transcriptions')
    os.makedirs(output_folder, exist_ok=True)
    print(f"Output folder created at: {output_folder}\n")

    # Load already transcribed files
    transcribed_files = load_transcribed_files(input_folder)

    # Iterate over all files in the input folder
    for filename in os.listdir(input_folder):
        if filename.endswith('.mp3'):
            file_path = os.path.join(input_folder, filename)
            
            print(f"Transcribing {file_path}...")

            if file_path in transcribed_files:
                print(f"    Already transcribed. Skipping {file_path}...\n")
                continue

            # Transcribe audio file
            result = model.transcribe(file_path, verbose=False, fp16=False, language='English')
            transcription = result['text']

            # Save transcription to a text file
            output_filename = f"{os.path.splitext(filename)[0]}-transcription.txt"
            output_file_path = os.path.join(output_folder, output_filename)
            with open(output_file_path, 'w') as f:
                f.write(transcription)

            print(f"    Finished {output_file_path}\n")

            # Save the file path to transcribed.txt
            save_transcribed_file(input_folder, file_path)

def main():
    parser = argparse.ArgumentParser(description='Batch transcribe MP3 files using Whisper.')
    parser.add_argument('input_folder', type=str, help='Path to the input folder containing MP3 files.')
    parser.add_argument('--model', type=str, default='base', help='Whisper model name to use (only for local mode).')

    args = parser.parse_args()

    transcribe_audio_files_local(args.input_folder, args.model)

if __name__ == '__main__':
    main()