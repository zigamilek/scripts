#!/bin/bash
# This script will create a folder and symlink to it from the current folder

export dest="$1"

if [[ $dest == *.mkv || $dest == *.avi || $dest == *.mp4 || $dest == *.mpeg || $dest == *.mpg || $dest == *.ts ]]; then
    # dest will be a file
    mkdir -p "$(dirname "$dest")"
    touch "$dest"
else
    # dest will be a directory
    mkdir -p "$dest"
fi

# create a symlink
if [ $# -eq 2 ]; then
    # if there is a second argument, create a symlink to $dest with the name specified in the second argument
    ln -sf "$dest" "$2"
else
    ln -sf "$dest"
fi