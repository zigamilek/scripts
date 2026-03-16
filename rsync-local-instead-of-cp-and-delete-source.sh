#!/bin/bash
# This script will move files from source to destination, entered as arguments.

export folder="/home/ziga/share/Logs/$(hostname)/$(date +%Y)/$(date +%m)"
mkdir -p "$folder"
export log="$folder/$(date +%Y%m%d)_RsyncCopy.log"
touch "$log"

mv --backup=numbered "$log" "$log".old

export src="$1"
export dest="$2"

echo "Copying..."
#cp -afv "$src" "$dest" >> "$log"
#rsync -avh --progress --log-file="$log" "$src" "$dest"
# show total progress with --info=progress2 --no-inc-recursive
if rsync -avh --info=progress2 --no-inc-recursive --log-file="$log" "$src" "$dest" ; then
    echo ""

    # Delete source
    echo "Deleting source..."
    rm -r "$src"
else
    echo ""
    echo "rsync interrupted. Aborting..."
fi