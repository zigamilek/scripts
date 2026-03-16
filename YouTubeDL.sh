#!/bin/bash

# Log file
export folder="/home/ziga/share/Logs/$(hostname)/$(date +%Y)/$(date +%m)"
mkdir -p "$folder"
export log="$folder/$(date +%Y%m%d)_YouTubeDL-4k.log"

export DOWNLOAD_FOLDER="/home/ziga/share/YouTube"
export DOWNLOAD_ARCHIVE="/home/ziga/share/YouTube/archive.txt"

# ---- Download complete channels  ----
CHANNELS=(
    # Business
    "https://www.youtube.com/channel/UCTvgSAxisCh58hjzlMdED0A" # Authority Hacker
    "https://www.youtube.com/channel/UCUnFdkKEu7nhgo41yVT-WCQ" # Jon Dykstra - Fat Stacks
    "https://www.youtube.com/channel/UC7RZRFCrN4XKoMsy5MgJKrg" # Miles Beckler
    "https://www.youtube.com/channel/UCyfj9qyOzBInnFITIt2Bw0w" # Shaun Marrs
    # Self Improvement
    "https://www.youtube.com/channel/UCtUId5WFnN82GdDy7DgaQ7w" # Better Ideas
    "https://www.youtube.com/channel/UCBIt1VN5j37PVM8LLSuTTlw" # Improvement Pill
    "https://www.youtube.com/channel/UC0TnW9acNxqeojxXDMbohcA" # Mark Manson
    "https://www.youtube.com/channel/UCJ24N4O0bP7LGLBDvye7oCA" # Matt D'Avella
    "https://www.youtube.com/channel/UCG-KntY7aVnIGXYEBQvmBAQ" # Thomas Frank
    "https://www.youtube.com/channel/UCqYPhGiB9tkShZorfgcL2lA" # What I've Learned
    "https://www.youtube.com/channel/UCybBViio_TH_uiFFDJuz5tg" # Einzelgänger
    "https://www.youtube.com/channel/UCIhJnsJ0IHlVNnYfp-gw_5Q" # Cal Newport
    # Health
    "https://www.youtube.com/channel/UCVz3b1bpwQnLYrT_0R8EFog" # Kit Laughlin
    "https://www.youtube.com/channel/UCU0DZhN-8KFLYO6beSaYljg" # Tom Merrick - BodyweightWarrior
    "https://www.youtube.com/channel/UCyPYQTT20IgzVw92LDvtClw" # Squat University
    "https://www.youtube.com/channel/UCnBDVUnNmy5QdyWMF3RK_Kg" # Summerfunfitness
    "https://www.youtube.com/channel/UCWF8SqJVNlx-ctXbLswcTcA" # Rhonda Patrick - FoundMyFitness
    
    # Mike Israetel 
    
    # Investing
    "https://www.youtube.com/channel/UCmYFMOiIuqJEW_TPxM61o0w" # Marja Milic
    "https://www.youtube.com/channel/UCDXTQ8nWmx_EhZ2v-kp7QxA" # Ben Felix
    # Other
    "https://www.youtube.com/playlist?list=PLp2G5GXjpIZ9833syzfb9m5Z8SJfkjpP7" # Mind the Game Pod w/ LeBron James and JJ Redick
)

CHANNELS1080=(
    # Business
    "https://www.youtube.com/channel/UCytOqtKYpACcWMD14UjhSeQ" # Income School
    # Health
    "https://www.youtube.com/channel/UCq0hKkwnW5Cw1wQqu455WrA" # Mind Pump Show
    "https://www.youtube.com/channel/UC9BNGVGr_lvbn3d23ckuVOA" # Josh Hash - Strength Side
    # Self Improvement
    "https://www.youtube.com/channel/UCkUaT0T03TJvafYkfATM2Ag" # Ryan Holiday - Daily Stoic
    "https://www.youtube.com/channel/UC8kGsMa0LygSX9nkBcBH1Sg" # Peter Attia
    "https://www.youtube.com/channel/UC2D2CMWXMOVWx7giW1n3LIg" # Andrew Huberman
    "https://www.youtube.com/channel/UCIaH-gZIVC432YRjNVvnyCA" # Chris Williamson
    "https://www.youtube.com/channel/UCoOae5nYA7VqaXzerajD0lg" # Ali Abdaal
    "https://www.youtube.com/channel/UCznv7Vf9nBdJYvBagFdAHWw" # Tim Ferriss
    # Crypto
    "https://www.youtube.com/channel/UCRvqjQPSeaWn-uEx-w0XOIg" # Benjamin Cowen
    "https://www.youtube.com/channel/UCCatR7nWbYrkVXdxXb4cGXw" # DataDash
    "https://www.youtube.com/channel/UC_bG7yHgT_xOUKvI2Hvo6Vg" # Daily Crypto Analysis
    "https://www.youtube.com/channel/UCzECtg05OBc2sE1KsRnHK7g" # Upside-Down Data
)

download_channel () {
    local channel=$1
    local quality=$2
    #local quality_string="[height=1080]" # to download at most 1080p resolution
    local quality_string="1080" # to download at most 1080p resolution

    if [ $quality == "4k" ]; then
        #quality_string="" # to download absolute best quality available
        quality_string="2160" # to download absolute best quality available
    fi

    # download BEST quality webm video and merge it with best webm audio
    #-f "bv*${quality_string}[ext=webm]+ba[ext=webm]/b" \
    # --sponsorblock-mark "all" \
    # --concurrent-fragments 10 \
    # --no-progress \
    # \
    #    >> "$log"
    #-f "bv*${quality_string}+ba/b" \
    /home/ziga/.local/bin/yt-dlp \
        -S "res:${quality_string}" \
        --ignore-errors \
        --no-progress \
        --download-archive $DOWNLOAD_ARCHIVE \
        -o "$DOWNLOAD_FOLDER/%(uploader)s/%(upload_date)s - %(title)s - %(resolution)s - %(id)s.%(ext)s" \
        --restrict-filenames \
        --write-subs --sub-langs "en" --sub-format "srt" \
        --external-downloader aria2c \
        $channel \
        >> "$log"
}

for CHANNEL in "${CHANNELS[@]}"; do
    download_channel $CHANNEL "4k"
done

for CHANNEL in "${CHANNELS1080[@]}"; do
    download_channel $CHANNEL "hd"
done
