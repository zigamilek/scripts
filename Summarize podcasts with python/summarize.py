from whisperplus.pipelines.long_text_summarization import LongTextSummarizationPipeline
from whisperplus import SpeechToTextPipeline, download_youtube_to_mp3
from transformers import BitsAndBytesConfig, HqqConfig
import torch

url = "https://www.youtube.com/watch?v=Io5xV9rtbm4"
audio_path = download_youtube_to_mp3(url, output_dir="downloads", filename="test")

hqq_config = HqqConfig(
    nbits=4,
    group_size=64,
    quant_zero=False,
    quant_scale=False,
    axis=0,
    offload_meta=False,
)  # axis=0 is used by default

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

pipeline = SpeechToTextPipeline(
    model_id="distil-whisper/distil-large-v3",
    quant_config=hqq_config,
    flash_attention_2=True,
)

transcript = pipeline(
    audio_path=audio_path,
    chunk_length_s=30,
    stride_length_s=5,
    max_new_tokens=128,
    batch_size=100,
    language="english",
    return_timestamps=False,
)

print(transcript)

summarizer = LongTextSummarizationPipeline(model_id="facebook/bart-large-cnn")
summary_text = summarizer.summarize(transcript)
print(summary_text)