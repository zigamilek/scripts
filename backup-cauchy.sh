#!/bin/bash
# Naredi backup pomembnih konfiguracijskih datotek
# Log file
export folder="/home/ziga/share/Logs/$(hostname)/$(date +%Y)/$(date +%m)"
mkdir -p "$folder"
export logconf="$folder/$(date +%Y%m%d)_backup-cauchy-conf.log"
export log="$folder/$(date +%Y%m)_backup-cauchy.log"
# What to backup
export BackupThis="
	/etc/ssh/sshd_config
	/etc/default/locale
	/etc/default/motd-news
	/etc/hostname
	/etc/hosts
	/etc/samba/smb.conf
	/etc/fstab
	/etc/vsftpd.conf
	/etc/vsftpd.chroot_list
	/etc/cups/cupsd.conf
	/etc/apt/sources.list
	/home/ziga/.unison
	/home/ziga/unison-2.49.543-installed-from-source
"
#	/etc/shorewall/*
#	/home/ziga/.screenrc
#	/home/ziga/.bash_aliases
#	/home/ziga/.dropbox
#	/home/ziga/.dropbox-dist
#	/etc/dnsmasq.conf
#	/etc/modules.conf
#	/etc/default/shorewall
#	/etc/ntp.conf
#	/etc/network/interfaces
#	/home/ziga/.rtorrent.rc
#	/etc/init.d/rtorrent
#	/etc/mdadm/mdadm.conf
#	/etc/modules
#	/etc/initramfs-tools/modules
#	/etc/initramfs-tools/conf.d/mdadm
#	/etc/hdparm.conf
#	/etc/hosts.allow
#	/etc/hosts.deny
#	/home/ziga/.msmtprc
#	/home/ziga/.mailrc
#	/etc/default/smartmontools
#	/etc/smartmontools/run.d/10mail
#	/etc/smartd.conf
#	/etc/resolv.conf
#	/etc/igmpproxy.conf
#	/etc/default/apcupsd
#	/etc/apcupsd/apcupsd.conf
# tale fajl /etc/ddclient.conf se noce backupat (permissions), zato sem ga odstranil iz BackupThis. itak se ne spreminja, tako da je v redu. sem ga manualno prenesel.
# Where to backup to
export BackupTo="/home/ziga/git/homelab/configurations/linhartova/cauchy/"
mkdir -p "$BackupTo"
# rsync backup (keep the directory structure = '-R' option)
rsync -RazvLh --delete --info=progress2 --no-inc-recursive --log-file=$logconf $BackupThis $BackupTo

# Ce ga se ni za trenutni mesec, naredi popoln system backup
if ! [ -f "$log" ]; then
	# Exclude file
	export ExcludeFileTar="/home/ziga/git/scripts/backup-exclude-tar.txt"
    # Remove files, older than 32 days
    find "/home/ziga/share/Backups/System" -mtime +32 -exec rm {} \;
    # Naredi backup
    export TarOutputFile="/home/ziga/share/Backups/System/backup.cauchy.$(date +%Y).$(date +%m).$(date +%d).tar.bz2"
    sudo /bin/tar cvpjf "$TarOutputFile" --exclude-from=$ExcludeFileTar / > "$log" 2>&1
    # Send the file to euler
    rsync -e "ssh -p 50002" -azvhi --inplace --info=progress2 --no-inc-recursive --log-file="$log" "$TarOutputFile" "linhartova.zigamilek.com:/home/ziga/share/Backups/System/"
fi

# sync logs
# added R parameter to create the necessary folders on euler
# and consequently removed $folder from the euler destination
# source: https://stackoverflow.com/a/22908437/1199569
rsync -e "ssh -p 50002" -azvhiR --inplace --info=progress2 --no-inc-recursive "$folder/" "linhartova.zigamilek.com:/"
