import json
import re
import os
import yt_dlp
from http.cookiejar import MozillaCookieJar
from pathlib import Path
import requests
from bs4 import BeautifulSoup

courses = [
    #'Eliot, Travis & Lauren Eckstrom - Yoga 45 for 45',
    #'Eliot, Travis - PY108 (Power Yoga 108)',
    #'Eckstrom, Lauren - Initiating the Mother',
    #'Eckstrom, Lauren - Complete Practice - The Program',
    #'Eliot, Travis & Lauren Eckstrom - Yoga Detox 30',
    #'Eckstrom, Lauren - Journey to Yoga',
    #'Eliot, Travis & Lauren Eckstrom - Meditation 101',
    #'Eliot, Travis & Lauren Eckstrom - Yoga for Beginners',
    'Eliot, Travis - Level Up 108',
    'Eliot, Travis - Flexibility & Beyond',
    'Eliot, Travis & Lauren Eckstrom - Yoga 30 for 30'
]

script_folder = os.path.dirname(os.path.realpath(__file__))
cookies_file = script_folder + '/cookies.txt'

def main():
    for course in courses:
        download_course(course)

def download_course(course):
    output_folder = '/home/ziga/share/PaleoPrimal/0 Yoga/Eliot, Travis - Inner Dimension TV/' + course + '/'
    #output_folder = '/Volumes/cauchyShare/PaleoPrimal/0 Yoga/' + course + '/'

    folder_with_links = output_folder + '/Materials/'
    course_html = folder_with_links + 'course_page.html'

    with open(course_html) as fp:
        soup = BeautifulSoup(fp, 'html.parser')

    a_tags = soup.find_all("a", attrs={'data-hls' : True}) # returns a list of all <a> tags with all their attributes

    links_all = [a_tag.attrs.get("data-hls", None) for a_tag in a_tags] # returns a list of only the data-hls attributes of those <a> tags
    links_unique = [*set(links_all)] # remove duplicates of those links

    #print(links_unique)

    for link in links_unique:
        #print(link)

        if( len(link) == 0 ):
            continue

        # Download video with two audio tracks: music + no music
        yt_opts = { # find a list of all available options here: https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py (search for "options")
            #'verbose': True,
            'cookiefile': cookies_file,
            'restrictfilenames': True,
            'windowsfilenames': True,
            'outtmpl': output_folder + '%(title)s.%(ext)s',
            #'ignoreerrors': True,
            #'listformats': True,
            #'format': 'wv*+wa*',
            #'format': 'bv*+mergeall[vcodec=none]', # download best video and all audio formats
            'format': 'bv*+program_audio-Music+program_audio-No_Music', # download best video and specific audio formats - one with music and one without music IN THAT ORDER. The first audio format specified will be the default audio track.
            'allow_multiple_audio_streams': True # merge all audio formats into the same output file
        }

        ydl = yt_dlp.YoutubeDL(yt_opts)

        try: 
            ydl.download(link)
        except yt_dlp.utils.DownloadError as error:
            # Fallback if program_audio-Music and program_audio-No_Music audio tracks don't exist: Download video with best video and audio
            yt_opts = {
                #'verbose': True,
                'cookiefile': cookies_file,
                'restrictfilenames': True,
                'windowsfilenames': True,
                'outtmpl': output_folder + '%(title)s.%(ext)s',
                #'ignoreerrors': True,
                #'listformats': True,
                #'format': 'wv*+wa*',
                #'format': 'bv*+mergeall[vcodec=none]', # download best video and all audio formats
                #'format': 'bv*+program_audio-Music+program_audio-No_Music', # download best video and specific audio formats - one with music and one without music IN THAT ORDER. The first audio format specified will be the default audio track.
                #'allow_multiple_audio_streams': True # merge all audio formats into the same output file
            }

            ydl = yt_dlp.YoutubeDL(yt_opts)

            ydl.download(link)
        

# source: https://stackoverflow.com/a/295466/1199569
def slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    import unicodedata
    value = unicodedata.normalize('NFKD', value).encode(
        'ascii', 'ignore').decode('utf-8')
    value = str(re.sub('[^\w\s-]', '', value).strip())
    value = str(re.sub('[-\s]+', '-', value))[0:100]
    # ...
    return value

if __name__ == "__main__":
    """ This is executed when run from the command line """
    main()