import json
import re
import os
import yt_dlp
from http.cookiejar import MozillaCookieJar
from pathlib import Path
import requests
from bs4 import BeautifulSoup

courses = [
    'Wild Yoga - Building to Peak Poses',
    'Calendar - Summer & Fall 2023',
    'Hidden Treasures',
    'Improve Your Focus & Concentration',
    'Memory Boost',
    'Empowerment Yoga',
    'Beginner\'s Collection',
    'Vital Recharge',
    'Girlfriends Glow Up',
    'Building a Healthy Spine for Life',
    'Root to Rise - From the Ground Up',
    'Grief is Grace',
    'A Life of Gratitude',
    'Empowered',
    'Vinyasa-Less',
    'Myofascial Yin Yang',
    'Meditation in Motion',
    'Elements of Power Yoga',
    'Flow & Go',
    'Power Blast',
    'Yin It to Win It',
    'The Basics of Mindfulness',
    'Rest Revolution',
    'Yoga for Travel',
    'Power - Yin - Restore',
    'Fierce Grace',
    'Mindful Movement',
    'Primal Elements',
    'Stacked',
    'Awakening the Chakras',
    'Powerful Slow Flow',
    'A Path for Joy',
    'Yoga Basics',
    'Rise - Thrive',
    'Transform',
    'Mom on the Go',
    '360 Core',
    '3-Day Online Retreat Part 2',
    'Power Yoga Blaze',
    'Journey to Handstand - Phase 1',
    'Start Your Day',
    'Sleep Well',
    'Caring for the Anxious Mind',
    'Embracing Imperfection',
    'The Sleep Well Series',
    '3-Day Online Retreat Part 1',
    'Turn Up the Heat',
    'Summer Yoga Loving',
    'Functional Fitness - The Foundations',
    'Work In & Work Out',
    'Practices for Deep Sleep'
]

script_folder = os.path.dirname(os.path.realpath(__file__))
cookies_file = script_folder + '/cookies.txt'

def main():
    for course in courses:
        download_course(course)

def download_course(course):
    output_folder = '/home/ziga/share/PaleoPrimal/0 Yoga/Eliot, Travis - Inner Dimension TV/Series/' + course + '/'
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