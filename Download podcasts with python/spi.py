import urllib.request
from bs4 import BeautifulSoup
import datetime
import re
import json
import os
from download_podcasts_from_rss import download_podcast, slugify

script_folder = os.path.dirname(os.path.abspath(__file__))
links = os.path.join(script_folder, "spi-links.txt")
download_path = "/home/ziga/share/Downloads/Podcasts/Pat Flynn - Smart Passive Income/"


def main():
    with open(links, "r") as links_file:
        for link in links_file:
            link = link.strip()

            print('Scraping article ' + link)

            page = simple_get(link)

            # parse the html using beautiful soup and store in variable 'soup'
            soup = BeautifulSoup(page, "html.parser")

            # title
            title = soup.find('h1', attrs={'class': 'entry-title'}).text

            # date
            date_json = json.loads(
                soup.find('script', attrs={'class': 'yoast-schema-graph'}).contents[0])
            date = date_json['@graph'][3]['datePublished'][:10]

            filename = date + " - " + slugify(title) + ".mp3"

            file_url = soup.find(
                text=re.compile("AP_Player")).split(
                    'shortcode_options":{"url":"')[1].split(
                        '","title"')[0].replace('\\', '')

            download_podcast(file_url, download_path, filename)


def simple_get(url):
    opener = urllib.request.build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
    urllib.request.install_opener(opener)
    return urllib.request.urlopen(url)


if __name__ == "__main__":
    """ This is executed when run from the command line """
    main()
