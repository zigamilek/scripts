#!/bin/bash
tempfile="/home/ziga/RepairPermissionsEuler-files.txt"

# Mape, ki jim je treba popraviti permissione
echo "/home/ziga/share/Logs
/home/ziga/share/Backups" > "$tempfile"

# || [[ ... ]] dodas, da prebere tudi zadnjo vrstico.
# source: http://stackoverflow.com/questions/15485555/read-last-line-of-file-in-bash-script-when-reading-file-line-by-line
while read f || [[ -n "$f" ]]; do
	bash "/home/ziga/Zigec/Racunalnik/Linux/_Scripts/RepairPermissions.sh" "$f"
done < "$tempfile"

# Zbrisemo temp file
rm -r "$tempfile"
