#!/bin/bash
#folder="/home/ziga/share/Downloads/FTP"
folder="/home/ziga/Mounted/WD_Red_4TB_2015_09/Downloads/FTP"

echo "Repairing chowns."

sudo chown ando:ziga -R "$folder/ando"
sudo chown andraz:ziga -R "$folder/andraz"
sudo chown andreas:ziga -R "$folder/andreas"
sudo chown anja:ziga -R "$folder/anja"
sudo chown blue:ziga -R "$folder/blue"
sudo chown igor:ziga -R "$folder/igor"
sudo chown mart1n:ziga -R "$folder/mart1n"
sudo chown matejka:ziga -R "$folder/matejka"
sudo chown nejc:ziga -R "$folder/nejc"
sudo chown peter:ziga -R "$folder/peter"
sudo chown tilen:ziga -R "$folder/tilen"
sudo chown tomaz:ziga -R "$folder/tomaz"
sudo chown ziga:ziga -R "$folder/ziga"
sudo chown download:ziga -R "$folder/download"

#Nastavi pravilen chmod za vse direktorije (glej http://www.linuxquestions.org/questions/linux-general-1/why-can-i-not-write-to-a-samba-share-when-read-write-is-enabled-475630/ )
# Ta chmod je drugacen kot ponavadi. 775 namesto 755
echo "Setting chmods of directories to 775."
sudo find "$folder" -type d -exec chmod 775 {} \;
#Nastavi pravilen chmod za vse fajle
# Ta chmod je drugacen kot ponavadi. 664 namesto 644
echo "Setting chmods of files to 664."
sudo find "$folder" -type f -exec chmod 664 {} \;
#Naredi skripte executable
# Ta chmod je drugacen kot ponavadi. 774 namesto 744
echo "Setting chmods of scripts to 774."
sudo find "$folder" -type f -name "*.sh" -exec chmod 774 {} \;
sudo find "$folder" -type f -name "*.pl" -exec chmod 774 {} \;
sudo find "$folder" -type f -name "*.py" -exec chmod 774 {} \;
