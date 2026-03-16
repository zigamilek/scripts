#!/bin/bash
# source: http://stackoverflow.com/questions/40394628/optimizing-bash-script-for-loops-permissions
echo "Repairing chowns."
sudo chown -R ziga:ziga "$@"

echo "Setting chmods of directories to 755."
find "$@" -type d -print0 | xargs -0 --no-run-if-empty chmod 755

echo "Setting chmods of files to 644."
find "$@" -type f -print0 | xargs -0 --no-run-if-empty chmod 644

echo "Setting chmods of scripts to 744."
find "$@" -type f \
   \( -name '*.sh' -o -name '*.pl' -o -name '*.py' \) \
   -print0 | xargs -0 --no-run-if-empty chmod 744
