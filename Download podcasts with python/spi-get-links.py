import urllib.request
from bs4 import BeautifulSoup
import datetime
import re

links = "/home/ziga/Zigec/Racunalnik/Linux/_Scripts/Download podcasts with python/spi-links.txt"


def main():
    with open(links, "w") as links_file:
        for i in range(44, 55):
            archive_page = "https://www.smartpassiveincome.com/shows/spi/page/" + \
                str(i)
            print('Scraping page ' + archive_page)

            page = simple_get(archive_page)

            # parse the html using beautiful soup and store in variable 'soup'
            soup = BeautifulSoup(page, "html.parser")

            post_links = soup.select("a[class=podcast_show_episode_card]")
            for post_link in post_links:
                print("  " + post_link['href'])
                links_file.write(post_link['href'] + "\n")


def simple_get(url):
    opener = urllib.request.build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
    urllib.request.install_opener(opener)
    return urllib.request.urlopen(url)


if __name__ == "__main__":
    """ This is executed when run from the command line """
    main()
