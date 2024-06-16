import os
import argparse
import openai

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

def load_summarized_files(input_folder):
    transcriptions_folder = os.path.join(input_folder, 'transcriptions')
    formatted_file_path = os.path.join(transcriptions_folder, 'already_summarized.txt')
    if os.path.exists(formatted_file_path):
        with open(formatted_file_path, 'r') as f:
            return set(f.read().splitlines())
    return set()

def save_summarized_file(input_folder, filename):
    transcriptions_folder = os.path.join(input_folder, 'transcriptions')
    formatted_file_path = os.path.join(transcriptions_folder, 'already_summarized.txt')
    with open(formatted_file_path, 'a') as f:
        f.write(filename + '\n')

def generate_markdown_from_transcriptions(input_folder):
    formatted_files = load_summarized_files(input_folder)
        
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
                    output_folder = os.path.join(root, 'summaries')
                    os.makedirs(output_folder, exist_ok=True)

                    client = openai.OpenAI(
                        api_key='REMOVED_OPENAI_API_KEY'
                    )

                    print(f"    Splitting the transcription into chunks.")
                    chunks = split_text_into_paragraphs(transcription)
                    summaries = []

                    system_message = {
                        "role": "system",
                        "content": "You are a helpful assistant that precisely follows the instructions. Your job is to create exceptional summaries from the content you are provided."
                    }

                    for i, chunk in enumerate(chunks):
                        print(f"    Processing chunk {i + 1} of {len(chunks)} using OpenAI API.")
                        
                        user_message = {
                            "role": "user",
                            "content": f"Please create a summary of this SEGMENT of a podcast episode transcription. The summary should have a length of 5-10% of the length of the original segment.\n\n{chunk}"
                        }

                        completion = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[system_message, user_message]
                        )

                        #print(str(completion) + "\n\n")

                        if completion.choices[0].finish_reason == 'length':
                            raise RuntimeError(f"Completion for chunk {i + 1} was cut off due to length.")

                        chunk_summary = completion.choices[0].message.content
                        summaries.append(chunk_summary)

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

                    #print(str(final_completion) + "\n\n")
                        
                    if completion.choices[0].finish_reason == 'length':
                        raise RuntimeError(f"Completion for final combined summary was cut off due to length.")

                    final_summary = final_completion.choices[0].message.content

                    # Remove the first line if it starts with "```markdown"
                    if final_summary.startswith("```markdown"):
                        final_summary = final_summary.split('\n', 1)[1]

                    # Remove all lines that are equal to ```
                    final_summary = '\n'.join(
                        line for line in final_summary.split('\n') if line.strip() != "```"
                    )

                    md_output_path = os.path.join(output_folder, f"{base_filename}-summary.md")
                    with open(md_output_path, 'w', encoding='utf-8') as f:
                        f.write(final_summary)

                    print(f"    Summary file created at: {md_output_path}\n")

                    save_summarized_file(input_folder, filename)

def main():
    parser = argparse.ArgumentParser(description='Generate summaries from transcriptions.')
    parser.add_argument('input_folder', type=str, help='Path to the input folder containing transcriptions.')

    args = parser.parse_args()

    generate_markdown_from_transcriptions(args.input_folder)

if __name__ == '__main__':
    main()