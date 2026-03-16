#!/bin/bash
# Log file
#export folder="/home/ziga/Mounted/Seagate_3TB_2014_03/Logs/$(hostname)/$(date +%Y)/$(date +%m)"
#mkdir -p "$folder"
#export log="$folder/$(date +%Y%m%d)_MountBinds.log";

export SHARE_ROOT="${SHARE_ROOT:-/home/ziga/share}"
export DROPBOX_SOURCE_DIR="${DROPBOX_SOURCE_DIR:-/home/ziga/Dropbox}"
export MOUNTED_ROOT="${MOUNTED_ROOT:-/home/ziga/Mounted}"

mkdir -p "$SHARE_ROOT/Dropbox"
#mkdir -p /home/ziga/Mounted/Seagate_Exos_X10_10TB_2019_11_1/Dropbox
sudo mount --bind "$DROPBOX_SOURCE_DIR/" "$SHARE_ROOT/Dropbox/"
#sudo mount --bind /home/ziga/Dropbox/ /home/ziga/Mounted/Seagate_Exos_X10_10TB_2019_11_1/Dropbox/

mkdir -p "$SHARE_ROOT/Zigec"
#mkdir -p /home/ziga/Mounted/Seagate_Exos_X10_10TB_2019_11_1/Zigec
sudo mount --bind "$DROPBOX_SOURCE_DIR/Zigec/" "$SHARE_ROOT/Zigec/"
#sudo mount --bind /home/ziga/Dropbox/Zigec/ /home/ziga/Mounted/Seagate_Exos_X10_10TB_2019_11_1/Zigec/

# commented out when switched to mergerfs
# multilevel formula
# exclude Survivor and Series
find "$MOUNTED_ROOT/" -maxdepth 2 -mindepth 2 \
    -type d ! -name "Survivor" ! -name "Series" ! -name "lost+found" ! -name ".Trash*" \
    -exec sh -c 'mkdir -p "$1/$(basename "$0")"' "{}" "$SHARE_ROOT" \; \
    -exec sh -c 'sudo mount --bind "$0" "$1/$(basename "$0")"' "{}" "$SHARE_ROOT" \;

# Survivor
find "$MOUNTED_ROOT/" -maxdepth 3 -mindepth 3 \
   -type d -path "*/Survivor/*" ! -name "Series" ! -name "lost+found" ! -name ".Trash*" \
   -exec sh -c 'mkdir -p "$1/Series/$(basename "$0")"' "{}" "$SHARE_ROOT" \; \
   -exec sh -c 'sudo mount --bind "$0" "$1/Series/$(basename "$0")"' "{}" "$SHARE_ROOT" \;

# Series
find "$MOUNTED_ROOT/" -maxdepth 3 -mindepth 3 \
   -type d -path "*/Series/*" ! -name "*Survivor*" ! -name "lost+found" ! -name ".Trash*" \
   -exec sh -c 'mkdir -p "$1/Series/$(basename "$0")"' "{}" "$SHARE_ROOT" \; \
   -exec sh -c 'sudo mount --bind "$0" "$1/Series/$(basename "$0")"' "{}" "$SHARE_ROOT" \;

#if [ "$(hostname)" == "euler" ]; then
#    sudo mount --rbind /home/ziga/share /Volumes/eulerSSH
#elif [ "$(hostname)" == "cauchy" ]; then
#    sudo mount --rbind /home/ziga/share /Volumes/cauchySSH
#fi
