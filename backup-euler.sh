#!/bin/bash
# Naredi backup pomembnih konfiguracijskih datotek
# Log file
export folder="/home/ziga/share/Logs/$(hostname)/$(date +%Y)/$(date +%m)"
mkdir -p "$folder"
export logconf="$folder/$(date +%Y%m%d)_backup-euler-conf.log"
export log="$folder/$(date +%Y%m)_backup-euler.log"
# What to backup
export BackupThis="
	/etc/ssh/sshd_config
	/etc/default/locale
	/etc/default/motd-news
	/etc/mysql/my.cnf
	/etc/hostname
	/etc/hosts
	/etc/samba/smb.conf
	/etc/fstab
	/etc/vsftpd.conf
	/etc/vsftpd.userlist
	/etc/vsftpd.chroot_list
	/etc/apt/sources.list
	/etc/systemd/system/rtorrent.service
	/var/spool/cron/crontabs
	/home/ziga/.rtorrent.rc
	/home/ziga/.screenrc
	/home/ziga/.my.cnf
	/home/ziga/.config
"
#	/home/ziga/.unison
#	/home/ziga/unison-2.49.543-installed-from-source
#	/home/ziga/.flexget
#	/etc/mysql/mysql.conf.d/mysqld.cnf
#   /etc/init.d/rtorrent
#	/etc/dnsmasq.conf
#	/etc/shorewall/*
#	/etc/modules.conf
#	/etc/default/shorewall
#	/etc/ntp.conf
#	/etc/vsftpd.chroot_list
#	/home/ziga/.rtorrent.rc
#	/etc/init.d/rtorrent
#	/etc/cups/cupsd.conf
#	/etc/mdadm/mdadm.conf
#	/etc/initramfs-tools/conf.d/mdadm
#	/home/ziga/.msmtprc
#	/home/ziga/.mailrc
#	/etc/default/smartmontools
#	/etc/smartmontools/run.d/10mail
#	/etc/smartd.conf
#	/etc/igmpproxy.conf
#	/etc/default/apcupsd
#	/etc/apcupsd/apcupsd.conf
#	/etc/modules
#	/etc/initramfs-tools/modules
#	/etc/hdparm.conf
#	/etc/hosts.allow
#	/etc/hosts.deny
#	/etc/resolv.conf
#	/etc/network/interfaces

# Where to backup to
#export BackupTo="/home/ziga/Zigec/Racunalnik/Nastavitve/Linux/Euler/"
export BackupTo="/home/ziga/git/homelab/configurations/linhartova/euler/"
mkdir -p "$BackupTo"

# rsync backup (keep the directory structure = '-R' option; ce so symlinki, prenesi doticne fajle = '-L' option)
#rsync -RazvLh --delete --info=progress2 --no-inc-recursive --ignore-errors --exclude-from=$ExcludeFile --log-file=$log $BackupThis $BackupTo
rsync -RazvLh --delete --info=progress2 --no-inc-recursive --log-file=$logconf $BackupThis $BackupTo
#---------------------------------------
# Ce ga se ni za trenutni mesec, naredi popoln system backup
if ! [ -f "$log" ]; then
	# Exclude file
	export ExcludeFileTar="/home/ziga/git/scripts/backup-exclude-tar.txt"
	# Remove files, older than 32 days
    find "/home/ziga/share/Backups/System" -mtime +32 -exec rm {} \;
    find "/home/ziga/share/Backups/MySQL" -mtime +32 -exec rm {} \;
    # Naredi backup
	sudo /bin/tar cvpjf /home/ziga/share/Backups/System/"backup.euler.$(date +%Y).$(date +%m).$(date +%d).tar.bz2" --exclude-from=$ExcludeFileTar / > "$log" 2>&1
fi
