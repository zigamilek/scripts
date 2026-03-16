import urllib.request
from bs4 import BeautifulSoup
import datetime
import re
from download_podcasts_from_rss import download_podcast, slugify

links = "/home/ziga/Zigec/Racunalnik/Linux/_Scripts/Download podcasts with python/rmrb-links.txt"
download_path = "/home/ziga/share/Downloads/Podcasts/Empire Flippers - Real Money Real Business/"


def main():
    with open(links, "r") as links_file:
        for link in links_file:
            link = link.strip()

            print('Scraping article ' + link)

            page = simple_get(link)

            # parse the html using beautiful soup and store in variable 'soup'
            soup = BeautifulSoup(page, "html.parser")

            # title
            title = soup.find('h1', attrs={'class': 'post-title'}).text

            # date
            date_string = soup.find('span', attrs={'class': 'date'}).text
            date_datetime = datetime.datetime.strptime(
                date_string.strip(), '%B %d, %Y')
            date = date_datetime.strftime("%Y-%m-%d")

            filename = date + " - " + slugify(title) + ".mp3"

            file_url = soup.select_one("a[href$=mp3]")['href']

            download_podcast(file_url, download_path, filename)


def simple_get(url):
    opener = urllib.request.build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
    urllib.request.install_opener(opener)
    return urllib.request.urlopen(url)


if __name__ == "__main__":
    """ This is executed when run from the command line """
    main()
