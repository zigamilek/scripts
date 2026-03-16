# download-rescuetime.py: Backup all of last month's rescuetime data
#
# Columns are Date,Time Spent (seconds),Number of People,Activity,Category,Productivity
# Rows are hourly breakdowns of the activities done
#
#
# Sample crontab entry to backup at 6AM on the 1st of every month:
# 0 6 1 * * python3 ~/rescuetime/backup-rescuetime.py
#
# You must also create an API key to use the script.
# Scroll to the bottom of https://www.rescuetime.com/anapi/manage
# Make the key in the form and copy it into the string below

# source: https://gist.github.com/AlexLamson/59554e9e9a521bf4460906c39951367a

import urllib.request
import datetime
import os
from dotenv import load_dotenv


def load_repo_dotenv():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    while True:
        env_file = os.path.join(current_dir, ".env")
        if os.path.exists(env_file):
            load_dotenv(env_file)
            return
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            return
        current_dir = parent_dir


load_repo_dotenv()

api_key = os.getenv("RESCUETIME_API_KEY")

if not api_key:
    raise RuntimeError("Missing RESCUETIME_API_KEY environment variable.")

output_folder = os.getenv(
    "RESCUETIME_OUTPUT_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports"),
)


def main():
    # determine the strings for getting last month's data
    now = datetime.datetime.now()

    get_m = 10
    get_y = 2024
    get_d = 31

    start_time = '{:04}-{:02}-{:02}'.format(get_y, get_m, 1)
    end_time = '{:04}-{:02}-{:02}'.format(get_y, get_m, get_d)

    # get the data
    body = [
        'key={}'.format(api_key),
        'perspective=interval',
        'interval=hour',
        'restrict_kind=document',
        'restrict_begin={}'.format(start_time),
        'restrict_end={}'.format(end_time),
        'format=json'
    ]

    link = 'https://www.rescuetime.com/anapi/data?{}'.format(
        '&'.join(body))

    print("Downloading from " + link)

    response = simple_get(link)

    # write it to a file
    os.makedirs(output_folder, exist_ok=True)
    output_file = os.path.join(output_folder, '{:04}-{:02}.json'.format(get_y, get_m))
    with open(output_file, 'w+b') as f:
        for i, line in enumerate(response.readlines()):
            f.write(line)


def simple_get(url):
    opener = urllib.request.build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
    urllib.request.install_opener(opener)
    return urllib.request.urlopen(url)


if __name__ == "__main__":
    """ This is executed when run from the command line """
    main()
