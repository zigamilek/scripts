import feedparser
import urllib.request
import re
import os
from pathlib import Path
import io
import ssl

# download_path = "/Users/zigamilek/Desktop/Podcasts/"
# download_path = "/home/ziga/share/Podcasts/"

# da dobiš RSS feed od nekega podcasta uporabi tole: https://getrssfeed.com/

podcasts = [
    [
        "Tim Ferriss - The Tim Ferriss Show",
        "https://rss.art19.com/tim-ferriss-show",
        "/home/ziga/share/Podcasts/"
    ], [
        "Seth Godin - Akimbo",
        "https://rss.acast.com/akimbo",
        "/home/ziga/share/Podcasts/"
    ], [
        "Shane Parrish - The Knowledge Project",
        "http://theknowledgeproject.libsyn.com/rss",
        "/home/ziga/share/Podcasts/"
    ], [
        "Simon Sinek - A Bit of Optimism",
        "https://feeds.simplecast.com/0aMcqx_F",
        "/home/ziga/share/Podcasts/"
    ], [
        "Gold Medal Bodies",
        "https://feeds.buzzsprout.com/7120.rss",
        "/home/ziga/share/Podcasts/"
    ], [
        "Pat Flynn - Ask Pat 2.0",
        "https://feeds.buzzsprout.com/56535.rss",
        "/home/ziga/share/Podcasts/"
    ], [
        "Pat Flynn - Smart Passive Income",
        "http://feeds.feedburner.com/spipodcast",
        "/home/ziga/share/Podcasts/"
    ], [
        "Empire Flippers",
        "http://adsenseflippers.libsyn.com/rss",
        "/home/ziga/share/Podcasts/"
    ], [
        "AuthorityHacker",
        "https://www.authorityhacker.com/podcast-episodes/feed/",
        "/home/ziga/share/Podcasts/"
    ], [
        "Empire Flippers - Web Equity Show",
        "http://webequityshow.libsyn.com/rss",
        "/home/ziga/share/Podcasts/"
    ], [
        "Empire Flippers - Real Money Real Business",
        "http://realmoneyrealbusiness.libsyn.com/rss",
        "/home/ziga/share/Podcasts/"
    ], [
        "Empire Flippers - The Opportunity",
        "https://theopportunity.libsyn.com/rss",
        "/home/ziga/share/Podcasts/"
    ], [
        "Janet Lansbury - Respectful Parenting",
        "http://feeds.soundcloud.com/users/soundcloud:users:91056977/sounds.rss",
        "/home/ziga/share/Podcasts/"
    ], [
        "Tim Ferriss - Tools of Titans",
        "https://anchor.fm/s/2379cb10/podcast/rss",
        "/home/ziga/share/Podcasts/"
    ], [
        "Cal Newport - Deep Questions",
        "https://feeds.buzzsprout.com/1121972.rss",
        "/home/ziga/share/Podcasts/"
    ], [
        "Noah Kagan Presents",
        "https://noahkagan.libsyn.com/rss",
        "/home/ziga/share/Podcasts/"
    ], [
        "Tropical MBA",
        "https://feeds.fireside.fm/tropicalmba/rss",
        "/home/ziga/share/Podcasts/"
    ], [
        "Naval Ravikant",
        "https://naval.libsyn.com/rss",
        "/home/ziga/share/Podcasts/"
    ], [
        "George Bryant - Mind Of George",
        "https://feeds.simplecast.com/q4Gd_PrF",
        "/home/ziga/share/Podcasts/"
    ], [
        "Nick Loper - The Side Hustle Show",
        "https://sidehustlenation.libsyn.com/rss",
        "/home/ziga/share/Podcasts/"
    ], [
        "Chris Guillebeau - Side Hustle School",
        "https://feeds.megaphone.fm/sidehustleschool",
        "/home/ziga/share/Podcasts/"
    ], [
        "Ryan Holiday - The Daily Stoic",
        "https://rss.art19.com/the-daily-stoic",
        "/home/ziga/share/Podcasts/"
    ], [
        "Dr. Andrew Huberman - Huberman Lab",
        "https://hubermanlab.libsyn.com/rss",
        "/home/ziga/share/Podcasts/"
    ], [
        "Dr. Matt Walker - The Matt Walker Podcast",
        "https://feeds.buzzsprout.com/1821163.rss",
        "/home/ziga/share/Podcasts/"
    ], [
        "Rhonda Patrick, Ph.D. - FoundMyFitness",
        "https://podcast.foundmyfitness.com/rss.xml",
        "/home/ziga/share/Podcasts/"
    ], [
        "Peter Attia - The Peter Attia Drive",
        "http://peterattiadrive.libsyn.com/rss",
        "/home/ziga/share/Podcasts/"
    ], [
        "Benjamin Felix and Cameron Passmore - The Rational Reminder",
        "https://rationalreminder.libsyn.com/rss",
        "/home/ziga/share/Podcasts/"
    ], [
        "Chris Williamson - Modern Wisdom",
        "https://feeds.megaphone.fm/SIXMSB5088139739",
        "/home/ziga/share/Podcasts/"
    ], [
        "3D Muscle Journey",
        "https://anchor.fm/s/f2ddbc2c/podcast/rss",
        "/home/ziga/share/Podcasts/"
    ]
]


def main():
    for podcast in podcasts:
        print("Checking " + podcast[0])

        download_path_full = podcast[2] + podcast[0] + "/"
        Path(download_path_full).mkdir(parents=True, exist_ok=True)

        NewsFeed = feedparser.parse(podcast[1])

        for entry in NewsFeed.entries:
            download_podcast(entry, download_path_full)


def download_podcast(entry, download_path):
    file_url = get_link(entry.links)

    already_downloaded = download_path + '0_downloaded.txt'

    try:
        with open(already_downloaded, 'r') as f:
            downloaded_links = f.read().splitlines()
    except FileNotFoundError:
        downloaded_links = []

    # check if we already downloaded this mp3
    if file_url in downloaded_links:
        # print("  Already downloaded.")
        return

    print("  Downloading " + entry.title)

    filename = get_date(entry.published_parsed) + \
        " - " + slugify(entry.title) + ".mp3"

    file_path = download_path + filename

    # download the mp3
    ssl._create_default_https_context = ssl._create_unverified_context # possibly unsafe, but it solved this error that started appearing in july 2023: ssl.SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: Hostname mismatch, certificate is not valid for 'dts.podtrac.com'. (_ssl.c:1076). source: https://stackoverflow.com/a/60671292
    opener = urllib.request.build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
    urllib.request.install_opener(opener)

    try:
        urllib.request.urlretrieve(file_url, file_path)
    except urllib.error.URLError as e:
        print(f"  Failed to download {entry.title}: {e}")
        return

    # write the link to already_downloaded file
    with open(already_downloaded, 'a+') as f:
        f.write(file_url + "\n")


def get_link(links_list):
    for link in links_list:
        if "rel" in link:
            if link["rel"] == "enclosure":
                return link["href"]


def get_date(date):
    year = str(date.tm_year)

    month = str(f'{date.tm_mon:02}')

    day = str(f'{date.tm_mday:02}')

    return year + "-" + month + "-" + day


# source: https://stackoverflow.com/a/295466/1199569
def slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    import unicodedata
    value = unicodedata.normalize('NFKD', value).encode(
        'ascii', 'ignore').decode('utf-8')
    value = str(re.sub('[^\w\s-]', '', value).strip().lower())
    value = str(re.sub('[-\s]+', '-', value))[0:100]
    # ...
    return value


if __name__ == "__main__":
    """ This is executed when run from the command line """
    main()
