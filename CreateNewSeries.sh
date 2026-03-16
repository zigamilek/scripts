#!/bin/bash
# Creates a new folder on a HDD for a new Series and bind mount to share/Series

# Log file
export folder="/home/ziga/share/Logs/$(hostname)/$(date +%Y)/$(date +%m)"
mkdir -p "$folder"
export log="$folder/$(date +%Y%m%d)_CreateNewSeries.log";

if [ $# -ne 1 ]; then
    # TODO: print usage
    echo "You must include 1 argument!"
    exit 1
fi

export series="$1"

echo ""
echo "Series:      $series"
echo ""

mkdir -p "/home/ziga/Mounted/Toshiba_Enterprise_16TB_2021_10_1/Series/$series" && mkdir -p "/home/ziga/share/Series/$series" && sudo mount --bind "/home/ziga/Mounted/Toshiba_Enterprise_16TB_2021_10_1/Series/$series" "/home/ziga/share/Series/$series"
