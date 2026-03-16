#!/bin/bash
# This script will move files from source to destination, entered as arguments.

log="/home/ziga/share/Temp/Prenos.txt"

mv --backup=numbered "$log" "$log".old

export src="$1"
export dest="$2"

cp -afv "$src" "$dest" >> "$log" && rm -rv "$src" >> "$log"
