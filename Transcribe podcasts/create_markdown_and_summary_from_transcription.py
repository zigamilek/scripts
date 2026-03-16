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
    sentences = text.split('. ')
    paragraphs = []
    current_paragraph = []

    def word_count(paragraph):
        return len(paragraph.split())

    for sentence in sentences:
        current_paragraph.append(sentence + '.')
        if word_count(' '.join(current_paragraph)) >= word_limit:
            paragraphs.append(' '.join(current_paragraph))
            current_paragraph = []
    
    if current_paragraph:
        paragraphs.append(' '.join(current_paragraph))
    
    return paragraphs

def load_processed_files(input_folder, filename):
    file_path = os.path.join(input_folder, 'transcriptions', filename)
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return set(f.read().splitlines())
    return set()

def save_processed_file(input_folder, filename, file_to_save):
    file_path = os.path.join(input_folder, 'transcriptions', file_to_save)
    with open(file_path, 'a') as f:
        f.write(filename + '\n')

def generate_markdown_and_summary(input_folder):
    formatted_files = load_processed_files(input_folder, 'already_formatted.txt')
    summarized_files = load_processed_files(input_folder, 'already_summarized.txt')
        
    for root, _, files in os.walk(input_folder):
        if 'transcriptions' in root:
            for filename in files:
                if filename.endswith('-transcription.txt'):
                    file_path = os.path.join(root, filename)

                    print(f"Processing transcription file: {file_path}")
                        
                    if filename in formatted_files and filename in summarized_files:
                        print(f"    Already processed. Skipping {file_path}...\n")
                        continue

                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            transcription = f.read()
                    except UnicodeDecodeError as e:
                        print(f"    Error reading {file_path}: {e}")
                        continue

                    base_filename = os.path.splitext(filename)[0]
                    output_folder = os.path.join(root, 'output')
                    os.makedirs(output_folder, exist_ok=True)

                    client = openai.OpenAI(api_key=OPENAI_API_KEY)

                    print(f"    Splitting the transcription into chunks.")
                    chunks = split_text_into_paragraphs(transcription)
                    summaries = []
                    md_content = ""

                    system_message = {
                        "role": "system",
                        "content": "You are a helpful assistant that precisely follows the instructions. Your job is to create exceptional summaries and formatted markdown from the content you are provided."
                    }

                    for i, chunk in enumerate(chunks):
                        print(f"    Processing chunk {i + 1} of {len(chunks)} using OpenAI API.")
                        
                        user_message_summary = {
                            "role": "user",
                            "content": f"Please create a summary of this SEGMENT of a podcast episode transcription. The summary should have a length of 5-10% of the length of the original segment.\n\n{chunk}"
                        }

                        user_message_md = {
                            "role": "user",
                            "content": f"Please format this SEGMENT of a podcast episode transcription into markdown without changing any of the words and sentences.\n\n{chunk}"
                        }

                        completion_summary = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[system_message, user_message_summary]
                        )

                        completion_md = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[system_message, user_message_md]
                        )

                        if completion_summary.choices[0].finish_reason == 'length' or completion_md.choices[0].finish_reason == 'length':
                            raise RuntimeError(f"Completion for chunk {i + 1} was cut off due to length.")

                        chunk_summary = completion_summary.choices[0].message.content
                        chunk_md_content = completion_md.choices[0].message.content

                        summaries.append(chunk_summary)
                        md_content += chunk_md_content + "\n"

                    print(f"    Creating the final summary from chunk summaries.")
                    final_summary_message = {
                        "role": "user",
                        "content": "Please create a summary of this selection of summarized chunks of a podcast episode.\n\n" +
                                   "\n\n".join(summaries) +
                                   "\n\nThen also provide a list of ALL actionable insights in the format:\n---\n### Insight:\n### Action:\n---\n### Insight:\n### Action:\nEach Insight-Action par should therefore be separated by a horizontal line ---.\n\n" +
                                   "Finally provide a set of detailed notes from the podcast episode.\n\n" +
                                   "Make sure to provide great details for everything! Make it twice as long and detailed as you initially wanted to do it.\n\n" +
                                   "And make sure to format everything nicely with markdown."
                    }

                    final_completion = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[system_message, final_summary_message]
                    )

                    if final_completion.choices[0].finish_reason == 'length':
                        raise RuntimeError(f"Completion for final combined summary was cut off due to length.")

                    final_summary = final_completion.choices[0].message.content

                    if final_summary.startswith("```markdown"):
                        final_summary = final_summary.split('\n', 1)[1]

                    final_summary = '\n'.join(
                        line for line in final_summary.split('\n') if line.strip() != "```"
                    )

                    md_output_path = os.path.join(output_folder, f"{base_filename}-formatted.md")
                    summary_output_path = os.path.join(output_folder, f"{base_filename}-summary.md")

                    with open(md_output_path, 'w', encoding='utf-8') as f:
                        f.write(md_content)

                    with open(summary_output_path, 'w', encoding='utf-8') as f:
                        f.write(final_summary)

                    print(f"    Markdown file created at: {md_output_path}\n")
                    print(f"    Summary file created at: {summary_output_path}\n")

                    save_processed_file(input_folder, filename, 'already_formatted.txt')
                    save_processed_file(input_folder, filename, 'already_summarized.txt')

def main():
    parser = argparse.ArgumentParser(description='Generate markdown and summaries from transcriptions.')
    parser.add_argument('input_folder', type=str, help='Path to the input folder containing transcriptions.')

    args = parser.parse_args()

    generate_markdown_and_summary(args.input_folder)

if __name__ == '__main__':
    main()