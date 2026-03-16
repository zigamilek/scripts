#!/bin/bash

# Log file
folder="/home/ziga/share/Logs/$(hostname)/$(date +%Y)/$(date +%m)"
mkdir -p "$folder"
log="$folder/$(date +%Y%m%d)_ReverseSymlink.log";

if [ $# -ne 1 ]; then
    # TODO: print usage
    echo "You must include 1 argument!"
    exit 1
fi

symlink=$1
current_target="$(readlink -f "$symlink")"
symlink_parent="$(dirname "$symlink")"

# add / to the end of $symlink_parent
if [[ "${symlink_parent}" != */ ]]; then
    symlink_parent="$symlink_parent""/"
fi

echo ""
echo "Removing symlink $symlink"
rm $symlink

echo ""
echo "Copying $current_target to $symlink_parent"

if rsync -avh --info=progress2 --no-inc-recursive --log-file="$log" "$current_target" "$symlink_parent" ; then
    echo ""

    # Delete current_target
    echo "Deleting $current_target"
    rm -r "$current_target"
    echo ""
else
    echo ""
    echo "rsync interrupted. Aborting..."
fi
