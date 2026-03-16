#!/bin/bash
thetime=$(date '+%Y/%m/%d %T')
# Log file
export folder="/cygdrive/d/temp/branko-backup-logs/$(date +%Y)/$(date +%m)"
mkdir -p "$folder"
export log="$folder/$(date +%Y%m%d)_SyncBrankoFromLaptopToEuler.log";

echo "$thetime Starting rsync from Branko-laptop to euler..." >> "$log"

# What to sync
SyncThis1=(
    '/cygdrive/d/Branko'
    '/cygdrive/x/Fotografije'
)
# Where to sync to
export SyncTo1="ziga@linhartova.zigamilek.com:/home/ziga/share/";

# Run rsync
rsync -e "ssh -p 50002" -azvh --progress --log-file="$log" "${SyncThis1[@]}" "$SyncTo1";


echo "----------" >> "$log"
# Downloadamo zadnjo verzijo SyncBrankoFromLaptopToEuler.sh skripte iz cauchya
echo "$thetime Downloading the latest version of SyncBrankoFromLaptopToEuler.sh script from euler..." >> "$log"
# What to sync
export SyncThis2="ziga@linhartova.zigamilek.com:/home/ziga/share/Zigec/Racunalnik/Linux/_Scripts/SyncBrankoFromLaptopToEuler.sh";
# Where to sync to
export SyncTo2="/cygdrive/d/Temp/";

# Run rsync
rsync -e "ssh -p 50002" -azvh --progress --log-file="$log" "$SyncThis2" "$SyncTo2";


echo "----------" >> "$log"
# Posljemo mapo z logi na cauchyja
echo "$thetime Sending log files to euler..." >> "$log"
# What to sync
export SyncThis3="/cygdrive/d/Temp/branko-backup-logs/";
# Where to sync to
export SyncTo3="ziga@linhartova.zigamilek.com:/home/ziga/share/Logs/branko/";

# Run rsync
rsync -e "ssh -p 50002" -azvh --progress --log-file="$log" "$SyncThis3" "$SyncTo3";


# Zapisemo konec v log file
echo "--------------------------------------------------------------------------------------" >> "$log"
