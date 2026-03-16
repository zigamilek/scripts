#!/bin/bash
# source: https://stackoverflow.com/a/51474667/1199569
#         https://stackoverflow.com/a/46172106/1199569
# Log file
export folder="/home/ziga/share/Logs/$(hostname)/$(date +%Y)/$(date +%m)"
mkdir -p "$folder"
export log="$folder/$(date +%Y%m%d)_BatchSymlinks.log";

destinationPath="/home/ziga/share/Downloads/BitTorrent/Series/Modern.Family.S01.1080p.BluRay.x264-TENEIGHTY/"

listOfTargets=(
    "/home/ziga/share/Series/Modern Family/Modern.Family.S01.1080p.BluRay.x264-TENEIGHTY/modern.family.s01e01.1080p.bluray.x264-teneighty.mkv"
    "/home/ziga/share/Series/Modern Family/Modern.Family.S01.1080p.BluRay.x264-TENEIGHTY/modern.family.s01e02.1080p.bluray.x264-teneighty.mkv"
    "/home/ziga/share/Series/Modern Family/Modern.Family.S01.1080p.BluRay.x264-TENEIGHTY/modern.family.s01e03.1080p.bluray.x264-teneighty.mkv"
    "/home/ziga/share/Series/Modern Family/Modern.Family.S01.1080p.BluRay.x264-TENEIGHTY/modern.family.s01e04.1080p.bluray.x264-teneighty.mkv"
    "/home/ziga/share/Series/Modern Family/Modern.Family.S01.1080p.BluRay.x264-TENEIGHTY/modern.family.s01e05.1080p.bluray.x264-teneighty.mkv"
    "/home/ziga/share/Series/Modern Family/Modern.Family.S01.1080p.BluRay.x264-TENEIGHTY/modern.family.s01e06.1080p.bluray.x264-teneighty.mkv"
    "/home/ziga/share/Series/Modern Family/Modern.Family.S01.1080p.BluRay.x264-TENEIGHTY/modern.family.s01e07.1080p.bluray.x264-teneighty.mkv"
    "/home/ziga/share/Series/Modern Family/Modern.Family.S01.1080p.BluRay.x264-TENEIGHTY/modern.family.s01e08.1080p.bluray.x264-teneighty.mkv"
    "/home/ziga/share/Series/Modern Family/Modern.Family.S01.1080p.BluRay.x264-TENEIGHTY/modern.family.s01e09.1080p.bluray.x264-teneighty.mkv"
    "/home/ziga/share/Series/Modern Family/Modern.Family.S01.1080p.BluRay.x264-TENEIGHTY/modern.family.s01e10.1080p.bluray.x264-teneighty.mkv"
    "/home/ziga/share/Series/Modern Family/Modern.Family.S01.1080p.BluRay.x264-TENEIGHTY/modern.family.s01e11.1080p.bluray.x264-teneighty.mkv"
    "/home/ziga/share/Series/Modern Family/Modern.Family.S01.1080p.BluRay.x264-TENEIGHTY/modern.family.s01e12.1080p.bluray.x264-teneighty.mkv"
    "/home/ziga/share/Series/Modern Family/Modern.Family.S01.1080p.BluRay.x264-TENEIGHTY/modern.family.s01e13.1080p.bluray.x264-teneighty.mkv"
    "/home/ziga/share/Series/Modern Family/Modern.Family.S01.1080p.BluRay.x264-TENEIGHTY/modern.family.s01e14.1080p.bluray.x264-teneighty.mkv"
    "/home/ziga/share/Series/Modern Family/Modern.Family.S01.1080p.BluRay.x264-TENEIGHTY/modern.family.s01e15.1080p.bluray.x264-teneighty.mkv"
    "/home/ziga/share/Series/Modern Family/Modern.Family.S01.1080p.BluRay.x264-TENEIGHTY/modern.family.s01e16.1080p.bluray.x264-teneighty.mkv"
    "/home/ziga/share/Series/Modern Family/Modern.Family.S01.1080p.BluRay.x264-TENEIGHTY/modern.family.s01e17.1080p.bluray.x264-teneighty.mkv"
    "/home/ziga/share/Series/Modern Family/Modern.Family.S01.1080p.BluRay.x264-TENEIGHTY/modern.family.s01e18.1080p.bluray.x264-teneighty.mkv"
    "/home/ziga/share/Series/Modern Family/Modern.Family.S01.1080p.BluRay.x264-TENEIGHTY/modern.family.s01e19.1080p.bluray.x264-teneighty.mkv"
    "/home/ziga/share/Series/Modern Family/Modern.Family.S01.1080p.BluRay.x264-TENEIGHTY/modern.family.s01e20.1080p.bluray.x264-teneighty.mkv"
    "/home/ziga/share/Series/Modern Family/Modern.Family.S01.1080p.BluRay.x264-TENEIGHTY/modern.family.s01e21.1080p.bluray.x264-teneighty.mkv"
    "/home/ziga/share/Series/Modern Family/Modern.Family.S01.1080p.BluRay.x264-TENEIGHTY/modern.family.s01e22.1080p.bluray.x264-teneighty.mkv"
    "/home/ziga/share/Series/Modern Family/Modern.Family.S01.1080p.BluRay.x264-TENEIGHTY/modern.family.s01e23.1080p.bluray.x264-teneighty.mkv"
    "/home/ziga/share/Series/Modern Family/Modern.Family.S01.1080p.BluRay.x264-TENEIGHTY/modern.family.s01e24.1080p.bluray.x264-teneighty.mkv"
)

for target in "${listOfTargets[@]}";
do
    symlink="$destinationPath$(basename "$target")"
    # check if symlink exists. if it's broken remove it. source: https://stackoverflow.com/a/36180056/1199569
    if [ -L "$symlink" ] ; then
       if [ -e "$symlink" ] ; then
          echo "Good link: $symlink"
       else
          echo "Broken link: $symlink"
          echo "    Deleting..."
          rm "$symlink"
       fi
    fi
    # create the symlink
    [[ -e "$target" ]] && ln -sv "$target" "$destinationPath"
done
