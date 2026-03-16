#!/bin/bash

# Log file
export folder="/home/ziga/share/Logs/$(hostname)/$(date +%Y)/$(date +%m)"
mkdir -p "$folder"
export log="$folder/$(date +%Y%m%d)_YouTubeDL-4k.log"

export DOWNLOAD_FOLDER="/home/ziga/share/Downloads/YouTube-4k/ZZZ Single Videos"
export DOWNLOAD_ARCHIVE="/home/ziga/share/Downloads/YouTube-4k/archive.txt"

export video=$1
export quality=$2
export quality_string="" # to download absolute best quality available

if [ ! -z "$2" ]; then # the second parameter is supplied
    if [ $quality == "1080" ] || [ $quality == "1080p" ] || [ $quality == "hd" ]; then
        quality_string="[height=1080]" # to download at most 1080p resolution
    fi
fi

# download BEST quality webm video and merge it with best webm audio
#/home/ziga/.local/bin/yt-dlp \
yt-dlp \
    -f "bv*${quality_string}[ext=webm]+ba[ext=webm]/b" \
    --ignore-errors \
    --download-archive $DOWNLOAD_ARCHIVE \
    -o "$DOWNLOAD_FOLDER/%(uploader)s/%(upload_date)s - %(title)s - %(resolution)s - %(id)s.%(ext)s" \
    --restrict-filenames \
    --write-subs --sub-langs "en" --sub-format "srt" \
    --sponsorblock-mark "all" \
    --concurrent-fragments 10 \
    $video