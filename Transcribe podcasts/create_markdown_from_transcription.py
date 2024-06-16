import os
import argparse
import openai

def generate_markdown_from_transcriptions(input_folder):
    for root, _, files in os.walk(input_folder):
        if 'transcriptions' in root:
            for filename in files:
                if filename.endswith('-transcription.txt'):
                    file_path = os.path.join(root, filename)
                    print(f"Processing transcription file: {file_path}")

                    with open(file_path, 'r', encoding='utf-8') as f:
                        transcription = f.read()

                    base_filename = os.path.splitext(filename)[0]
                    output_folder = root

                    client = openai.OpenAI(
                        api_key='REMOVED_OPENAI_API_KEY'
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

                    #print(completion)

                    md_content = completion.choices[0].message.content

                    md_output_path = os.path.join(output_folder, f"{base_filename}-formatted.md")
                    with open(md_output_path, 'w', encoding='utf-8') as f:
                        f.write(md_content)

                    print(f"    Markdown file created at: {md_output_path}\n")

def main():
    parser = argparse.ArgumentParser(description='Generate Markdown files from transcriptions.')
    parser.add_argument('input_folder', type=str, help='Path to the input folder containing transcriptions.')

    args = parser.parse_args()

    generate_markdown_from_transcriptions(args.input_folder)

if __name__ == '__main__':
    main()