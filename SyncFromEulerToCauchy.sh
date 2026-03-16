#!/bin/bash
# Log file
export folder="/home/ziga/share/Logs/$(hostname)/$(date +%Y)/$(date +%m)";
mkdir -p "$folder";
export log="$folder/$(date +%Y%m%d)_SyncFromEulerToCauchy.log";

# What to sync
SyncThis="/home/ziga/share/";

# Where to sync to
export SyncTo="crnomelj.milek.org:/home/ziga/share/";
#export SyncTo="46.248.89.167:/home/ziga/share/";
#export SyncTo="188.230.174.98:/home/ziga/share/";
# export SyncTo="192.168.111.155:/home/ziga/share/";

Delete="--progress ";
OutputTo="/tmp/TempRsyncOutput.txt";

if [ ! -z "$1" ]; then # parameter is not empty
    if [ "$1" == "dry-run" ]; then
        Delete="--dry-run --progress ";
        OutputTo="$folder/$(date +%Y%m%d)_SyncFromEulerToCauchy_dry_run.log";
    fi
    if [ "$1" == "dry-delete" ]; then
        Delete="--dry-run --delete-before --progress ";
        OutputTo="$folder/$(date +%Y%m%d)_SyncFromEulerToCauchy_dry_delete.log";
    fi
    if [ "$1" == "delete" ]; then
        Delete="--delete-before --no-inc-recursive --info=progress2 ";
    fi
    if [ "$1" == "no-inc-recursive" ]; then
        Delete="--no-inc-recursive --info=progress2 ";
    fi
fi

InProgress="/tmp/SyncFromEulerToCauchyInProgress.txt";

# run the sync if $InProgress file doesn't exist (= previous sync is still in progress)
if [ ! -f "$InProgress" ]; then
    touch $InProgress;

    # add "z" when using over WAN, remove "z" when using over LAN
    # limit bandwidth to 2000 KBytes per second
    # --bwlimit=2000 \

    rsync -e "ssh -p 50002" -avzhi \
        $Delete \
        --exclude="Backups/TimeMachine" \
        --exclude="Backups/Proxmox/gauss" \
        --exclude="Dropbox" \
        --exclude="Logs/cauchy" \
        --exclude="Zigec" \
        --exclude="lost+found" \
        --exclude=".Trash-1000" \
        --exclude="rtorrent.lock" \
        --inplace \
        --log-file="$log" \
        "$SyncThis" \
        "$SyncTo" |& tee $OutputTo

    # rsync -e "ssh -p 50002" -avhi \
    #     $Delete \
    #     --exclude="Backups/TimeMachine" \
    #     --exclude="Dropbox" \
    #     --exclude="Zigec" \
    #     --exclude="lost+found" \
    #     --exclude=".Trash-1000" \
    #     --exclude="rtorrent.lock" \
    #     --inplace \
    #     --log-file="$log" \
    #     "$SyncThis" \
    #     "$SyncTo" |& tee $OutputTo

    # remove $InProgress file
    rm $InProgress;
else
    echo "Previous sync still in progress. Aborting..."
fi
