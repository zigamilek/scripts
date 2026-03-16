#!/bin/bash
# Log file
#export folder="/home/ziga/Mounted/Seagate_3TB_2014_03/Logs/$(hostname)/$(date +%Y)/$(date +%m)"
#mkdir -p "$folder"
#export log="$folder/$(date +%Y%m%d)_MountBinds.log";

mkdir -p /home/ziga/share/Dropbox
#mkdir -p /home/ziga/Mounted/Seagate_Exos_X10_10TB_2019_11_1/Dropbox
sudo mount --bind /home/ziga/Dropbox/ /home/ziga/share/Dropbox/
#sudo mount --bind /home/ziga/Dropbox/ /home/ziga/Mounted/Seagate_Exos_X10_10TB_2019_11_1/Dropbox/

mkdir -p /home/ziga/share/Zigec
#mkdir -p /home/ziga/Mounted/Seagate_Exos_X10_10TB_2019_11_1/Zigec
sudo mount --bind /home/ziga/Dropbox/Zigec/ /home/ziga/share/Zigec/
#sudo mount --bind /home/ziga/Dropbox/Zigec/ /home/ziga/Mounted/Seagate_Exos_X10_10TB_2019_11_1/Zigec/

# commented out when switched to mergerfs
# multilevel formula
# exclude Survivor and Series
find /home/ziga/Mounted/ -maxdepth 2 -mindepth 2 \
    -type d ! -name "Survivor" ! -name "Series" ! -name "lost+found" ! -name ".Trash*" \
    -exec sh -c 'mkdir -p /home/ziga/share/"$(basename "$0")"' "{}" \; \
    -exec sh -c 'sudo mount --bind "$0" /home/ziga/share/"$(basename "$0")"' "{}" \;

# Survivor
find /home/ziga/Mounted/ -maxdepth 3 -mindepth 3 \
   -type d -path "*/Survivor/*" ! -name "Series" ! -name "lost+found" ! -name ".Trash*" \
   -exec sh -c 'mkdir -p /home/ziga/share/Series/"$(basename "$0")"' "{}" \; \
   -exec sh -c 'sudo mount --bind "$0" /home/ziga/share/Series/"$(basename "$0")"' "{}" \;

# Series
find /home/ziga/Mounted/ -maxdepth 3 -mindepth 3 \
   -type d -path "*/Series/*" ! -name "*Survivor*" ! -name "lost+found" ! -name ".Trash*" \
   -exec sh -c 'mkdir -p /home/ziga/share/Series/"$(basename "$0")"' "{}" \; \
   -exec sh -c 'sudo mount --bind "$0" /home/ziga/share/Series/"$(basename "$0")"' "{}" \;

#if [ "$(hostname)" == "euler" ]; then
#    sudo mount --rbind /home/ziga/share /Volumes/eulerSSH
#elif [ "$(hostname)" == "cauchy" ]; then
#    sudo mount --rbind /home/ziga/share /Volumes/cauchySSH
#fi
