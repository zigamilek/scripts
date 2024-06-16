import os
import argparse
import whisper
import openai

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

                # Save transcription to a text file
                output_filename = f"{os.path.splitext(filename)[0]}-transcription.txt"
                output_file_path = os.path.join(output_folder, output_filename)
                with open(output_file_path, 'w') as f:
                    f.write(transcription)

                print(f"    Finished {output_file_path}\n")

                # Save the file path to already_transcribed.txt file
                save_transcribed_file(input_folder, file_path)

            # Generate Markdown files from transcription
            generate_markdown_from_transcription(transcription, output_folder, os.path.splitext(filename)[0])

def generate_markdown_from_transcription(transcription, output_folder, base_filename):
    client = openai.OpenAI(
        api_key = 'REMOVED_OPENAI_API_KEY'
    )

    system_message = {
        "role": "system",
        "content": "You are a helpful assistant that precisely follows the instructions. Your job is taking the content you are provided with and making it more readable and organized, without changing any of the words and sentences."
    }
    user_message = {
        "role": "user",
        "content": f"Please transform this podcast episode transcription into a nice Markdown document with headings, subheadings, etc. \n\nIt's of the utmost importance to keep the transcription text intact in its entirety! Just split it up into logical sections to make it more readable!\n\nMake absolutely sure to follow the instructions! Don't create a summary or Cliffsnotes! Don't leave any of the original text out. All of the original text must be kept! It needs to just be split into logical sections to make it more readable!\n\nEach section should have a H3 heading (### Markdown tag) and should be split into MULTIPLE paragraphs. Here it's important that you make the paragraphs in the sections SUPER SHORT! 3 to 5 sentences in each paragraph is the maximum!\n\nAgain, make absolutely sure to follow ALL of the above instructions!\n\n{transcription}"
    }

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[system_message, user_message]
    )

    md_content = completion.choices[0].message['content']

    md_output_path = os.path.join(output_folder, f"{base_filename}-transcription-formatted.md")
    with open(md_output_path, 'w') as f:
        f.write(md_content)

    print(f"    Markdown file created at: {md_output_path}\n")

def main():
    parser = argparse.ArgumentParser(description='Batch transcribe MP3 files using Whisper.')
    parser.add_argument('input_folder', type=str, help='Path to the input folder containing MP3 files.')
    parser.add_argument('--model', type=str, default='medium.en', help='Whisper model to use (default: medium.en)')

    args = parser.parse_args()

    transcribe_audio_files_local(args.input_folder, args.model)

if __name__ == '__main__':
    main()