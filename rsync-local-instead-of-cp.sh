#!/bin/bash
# This script will move files from source to destination, entered as arguments.

export folder="/home/ziga/share/Logs/$(hostname)/$(date +%Y)/$(date +%m)"
mkdir -p "$folder"
export log="$folder/$(date +%Y%m%d)_RsyncCopy.log"
touch "$log"

mv --backup=numbered "$log" "$log".old

export src="$1"
export dest="$2"

#cp -afv "$src" "$dest" >> "$log"
#rsync -avh --progress --log-file="$log" "$src" "$dest"
# show total progress with --info=progress2 --no-inc-recursive
rsync -avh --info=progress2 --no-inc-recursive --log-file="$log" "$src" "$dest"
