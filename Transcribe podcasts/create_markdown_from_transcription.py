import os
import argparse
import openai
from dotenv import load_dotenv


def load_repo_dotenv():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    while True:
        env_file = os.path.join(current_dir, ".env")
        if os.path.exists(env_file):
            load_dotenv(env_file)
            return
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            return
        current_dir = parent_dir


load_repo_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY environment variable.")

def split_text_into_paragraphs(text, word_limit=2900):
    # Split the text into sentences based on the period followed by a space
    sentences = text.split('. ')
    paragraphs = []
    current_paragraph = []

    # Helper function to count words in a paragraph
    def word_count(paragraph):
        return len(paragraph.split())

    for sentence in sentences:
        # Add the sentence to the current paragraph
        current_paragraph.append(sentence + '.')
        
        # If the current paragraph exceeds the word limit, move it to paragraphs
        if word_count(' '.join(current_paragraph)) >= word_limit:
            paragraphs.append(' '.join(current_paragraph))
            current_paragraph = []
    
    # Add any remaining sentences as the last paragraph
    if current_paragraph:
        paragraphs.append(' '.join(current_paragraph))
    
    return paragraphs

def load_formatted_files(input_folder):
    transcriptions_folder = os.path.join(input_folder, 'transcriptions')
    formatted_file_path = os.path.join(transcriptions_folder, 'already_formatted.txt')
    if os.path.exists(formatted_file_path):
        with open(formatted_file_path, 'r') as f:
            return set(f.read().splitlines())
    return set()

def save_formatted_file(input_folder, filename):
    transcriptions_folder = os.path.join(input_folder, 'transcriptions')
    formatted_file_path = os.path.join(transcriptions_folder, 'already_formatted.txt')
    with open(formatted_file_path, 'a') as f:
        f.write(filename + '\n')

def generate_markdown_from_transcriptions(input_folder):
    formatted_files = load_formatted_files(input_folder)
        
    for root, _, files in os.walk(input_folder):
        if 'transcriptions' in root:
            for filename in files:
                if filename.endswith('-transcription.txt'):
                    file_path = os.path.join(root, filename)

                    print(f"Processing transcription file: {file_path}")
                        
                    if filename in formatted_files:
                        print(f"    Already formatted. Skipping {file_path}...\n")
                        continue

                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            transcription = f.read()
                    except UnicodeDecodeError as e:
                        print(f"    Error reading {file_path}: {e}")
                        continue

                    base_filename = os.path.splitext(filename)[0]
                    output_folder = os.path.join(root, 'formatted')
                    os.makedirs(output_folder, exist_ok=True)

                    client = openai.OpenAI(api_key=OPENAI_API_KEY)

                    print(f"    Splitting the transcription into chunks.")
                    chunks = split_text_into_paragraphs(transcription)
                    md_content = ""

                    for i, chunk in enumerate(chunks):
                        print(f"    Processing chunk {i + 1} of {len(chunks)} using OpenAI API.")
                        system_message = {
                            "role": "system",
                            "content": "You are a helpful assistant that precisely follows the instructions. Your job is taking the content you are provided with and making it more readable and organized, without changing any of the words and sentences."
                        }
                        user_message = {
                            "role": "user",
                            "content": f"Please transform this SEGMENT from podcast episode transcription into a nice Markdown document with headings, subheadings, etc. \n\nNote this is not the whole episode, only a segment from it. So add ### Introduction and ### Conclusion only if you're absolutely sure it's the begginning or the ending segment of the episode.\n\nIt's of the utmost importance to keep the transcription text intact in its entirety! Just split it up into logical sections to make it more readable!\n\nMake absolutely sure to follow the instructions! Don't create a summary or Cliffsnotes! Don't leave any of the original text out. All of the original text must be kept! It needs to just be split into logical sections to make it more readable!\n\nEach section should have a H3 heading (### Markdown tag) and should be split into MULTIPLE paragraphs. Here it's important that you make the paragraphs in the sections SUPER SHORT! 3 to 5 sentences in each paragraph is the maximum!\n\nAgain, make absolutely sure to follow ALL of the above instructions!\n\n{chunk}"
                        }

                        completion = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[system_message, user_message]
                        )

                        #print(str(completion) + "\n\n")
                        if completion.choices[0].finish_reason == 'length':
                            raise RuntimeError(f"Completion for chunk {i + 1} was cut off due to length.")

                        chunk_md_content = completion.choices[0].message.content

                        # Remove the first line if it starts with "```markdown"
                        if chunk_md_content.startswith("```markdown"):
                            chunk_md_content = chunk_md_content.split('\n', 1)[1]

                        # Remove all lines that are equal to ```
                        chunk_md_content = '\n'.join(
                            line for line in chunk_md_content.split('\n') if line.strip() != "```"
                        )

                        md_content += chunk_md_content + "\n"

                    md_output_path = os.path.join(output_folder, f"{base_filename}-formatted.md")
                    with open(md_output_path, 'w', encoding='utf-8') as f:
                        f.write(md_content)

                    print(f"    Markdown file created at: {md_output_path}\n")

                    # Save the filename to already_formatted.txt file
                    save_formatted_file(input_folder, filename)

def main():
    parser = argparse.ArgumentParser(description='Generate Markdown files from transcriptions.')
    parser.add_argument('input_folder', type=str, help='Path to the input folder containing transcriptions.')

    args = parser.parse_args()

    generate_markdown_from_transcriptions(args.input_folder)

if __name__ == '__main__':
    main()