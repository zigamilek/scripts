#!/bin/bash
# Log file
# export folder="/home/ziga/Mounted/Seagate_3TB_2014_03/Logs/$(hostname)/$(date +%Y)/$(date +%m)"
# mkdir -p "$folder"
# export log="$folder/$(date +%Y%m%d)_MountBinds.log";

if [ "$(hostname)" == "euler" ]; then
    grep "/Volumes/eulerSSH" /proc/mounts | cut -f2 -d" " | sed 's/\040/\ /g' | sort -r | xargs sudo umount -n
    sudo umount "/Volumes/eulerSSH"
elif [ "$(hostname)" == "cauchy" ]; then
    grep "/Volumes/cauchySSH" /proc/mounts | cut -f2 -d" " | sed 's/\040/\ /g' | sort -r | xargs sudo umount -n
    sudo umount "/Volumes/cauchySSH"
fi

find /home/ziga/share/Series/ -maxdepth 1 -mindepth 1 -type d -exec sudo umount "{}" \;
#find /home/ziga/share/ -maxdepth 1 -mindepth 1 ! -name "Series" -type d -exec sudo umount "{}" \;

find /home/ziga/share/ -maxdepth 1 -mindepth 1 -type d -exec sudo umount "{}" \;
