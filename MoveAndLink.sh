#!/bin/bash
# če hočeš v destination imeti drugačen filename,
# najprej na destination lokaciji na roko naredi ustrezno mapo ali prazen fajl,
# nato pa poženi skripto. Če delaš z mapami, moraš v tem primeru
# tako na src kot dest uporabiti trailing slash /

# Log file
export folder="/home/ziga/share/Logs/$(hostname)/$(date +%Y)/$(date +%m)"
mkdir -p "$folder"
export log="$folder/$(date +%Y%m%d)_MoveAndLink.log";

if [ $# -ne 2 ]; then
    # TODO: print usage
    echo "You must include 2 arguments!"
    exit 1
fi

# get full paths
export src="$(readlink -f "$1")"
export filename="${src##*/}"

export dest="$(readlink -f "$2")"

# add / to the end if $src originally has it at the end
if [[ "${1}" == */ ]]; then
    src="$src""/"
    filename=""
fi

# Add / to the end if $dest is a directory
if [ -d "$dest" ]; then
    dest="$dest""/"
fi

echo ""
# echo "$dest""$filename"
echo "Source:      $src"
echo "Destination: $dest"
echo ""

# TODO dodaj promt for confirmation:
# https://stackoverflow.com/questions/1885525/how-do-i-prompt-a-user-for-confirmation-in-bash-script

# exit 1

# Copy
echo "Copying..."
#mv -v "$src" "$dest" >> "$log"
if rsync -avh --info=progress2 --no-inc-recursive --log-file="$log" "$src" "$dest" ; then
    echo ""

    # Delete source
    echo "Deleting source..."
    rm -r "$src"
    echo ""

    # Add the filename to $dest variable
    if [ -d "$dest" ]; then
        target="$dest""$filename"
    else
        target="$dest"
    fi
    
    # Create symbolic link (remove the trailing slashes)
    echo "Creating symbolic link..."
    ln -s "${target%/}" "${src%/}"
    echo ""
else
    echo ""
    echo "rsync interrupted. Aborting..."
fi

