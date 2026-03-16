import json
import re
import os
import yt_dlp
from http.cookiejar import MozillaCookieJar
from pathlib import Path
import requests
from bs4 import BeautifulSoup

trailers = [
        "3-Day Online Retreat Part 1",
        "https://d22rix4bfet7yn.cloudfront.net/54436/3+Day+Retreat.m3u8"
    ], [
        "3-Day Online Retreat Part 2",
        "https://d22rix4bfet7yn.cloudfront.net/86846/3+Day+Retreat+2+-+PROMO.m3u8"
    ], [
        "360 Core",
        "https://d22rix4bfet7yn.cloudfront.net/95142/CLIP+-+360+Core.m3u8"
    ], [
        "A Life of Gratitude",
        "https://d22rix4bfet7yn.cloudfront.net/332927/Intro+-+Life+of+Gratitude.m3u8"
    ], [
        "A Path for Joy",
        "https://d22rix4bfet7yn.cloudfront.net/62830a/Teaser+-+Path+for+Joy.m3u8"
    ], [
        "Awakening the Chakras",
        "https://d22rix4bfet7yn.cloudfront.net/157700a/FINAL+Promo+AWAKENING+THE+CHAKRAS+with+Brittany.m3u8"
    ], [
        "Beginner's Collection",
        "https://d22rix4bfet7yn.cloudfront.net/391666/Preview_Beginners_1.m3u8"
    ], [
        "Building a Healthy Spine for Life",
        "https://d22rix4bfet7yn.cloudfront.net/374746/PROMO_Healthy_Spine.m3u8"
    ], [
        "Calendar - Summer & Fall 2023",
        "https://d22rix4bfet7yn.cloudfront.net/447103/Preview_Cal_summerfall_23.m3u8"
    ], [
        "Caring for the Anxious Mind",
        "https://d22rix4bfet7yn.cloudfront.net/65301a/CLIP_Program_text.m3u8"
    ], [
        "Elements of Power Yoga",
        "https://d22rix4bfet7yn.cloudfront.net/289559a/Intro+Elements.m3u8"
    ], [
        "Embracing Imperfection",
        "https://d22rix4bfet7yn.cloudfront.net/64085/CLIP_Embracing_Imperfections.m3u8"
    ], [
        "Empowered",
        "https://d22rix4bfet7yn.cloudfront.net/324163/Empowered+PROMO+1b.m3u8"
    ], [
        "Empowerment Yoga",
        "https://d22rix4bfet7yn.cloudfront.net/415289/Empowerment_INTRO_2b.m3u8"
    ], [
        "Fierce Grace",
        "https://d22rix4bfet7yn.cloudfront.net/188428a/Trailer+Web+FG.m3u8"
    ], [
        "Flow & Go",
        "https://d22rix4bfet7yn.cloudfront.net/281703a/F&G+PROMO+-+J1+-+FINAL.m3u8"
    ], [
        "Functional Fitness - The Foundations",
        "https://d22rix4bfet7yn.cloudfront.net/34907/FunctionalFitnessIntro.m3u8"
    ], [
        "Girlfriends Glow Up",
        "https://d22rix4bfet7yn.cloudfront.net/398490/Glow_Up_Promo.m3u8"
    ], [
        "Grief is Grace",
        "https://d22rix4bfet7yn.cloudfront.net/345378/Promo2+Grief+is+Grace.m3u8"
    ], [
        "Hidden Treasures",
        "https://d22rix4bfet7yn.cloudfront.net/395594/Hidden_Treasures_1.m3u8"
    ], [
        "Improve Your Focus & Concentration",
        "https://d22rix4bfet7yn.cloudfront.net/415290/INTRO_3_Short_Improve_Your_Focus.m3u8"
    ], [
        "Journey to Handstand - Phase 1",
        "https://d22rix4bfet7yn.cloudfront.net/77753a/Trailer+-+Journey+to+Handstand.m3u8"
    ], [
        "Meditation in Motion",
        "https://d22rix4bfet7yn.cloudfront.net/300600/Test+Trailer+MM.m3u8"
    ], [
        "Memory Boost",
        "https://d22rix4bfet7yn.cloudfront.net/415566/Intro_Short_Memory_Boost.m3u8"
    ], [
        "Mindful Movement",
        "https://d22rix4bfet7yn.cloudfront.net/183935a/SERIES+Trailer+-+Mindful+Movement.m3u8"
    ], [
        "Mom on the Go",
        "https://d22rix4bfet7yn.cloudfront.net/99652/Series+Promo+-+Mom+on+the+Go+2.m3u8"
    ], [
        "Myofascial Yin Yang",
        "https://d22rix4bfet7yn.cloudfront.net/310673/Introduction+-+MYOFASCIAL+YIN+YANG.m3u8"
    ], [
        "Power - Yin - Restore",
        "https://d22rix4bfet7yn.cloudfront.net/212766a/PROMO+-+Power+Yin+Restore.m3u8"
    ], [
        "Power Blast",
        "https://d22rix4bfet7yn.cloudfront.net/254743a/Promo+-+Power+Blast.m3u8"
    ], [
        "Power Yoga Blaze",
        "https://d22rix4bfet7yn.cloudfront.net/84310/CLIP+-+Blaze+3.m3u8"
    ], [
        "Powerful Slow Flow",
        "https://d22rix4bfet7yn.cloudfront.net/148558a/Promo+-+POWERFUL+SLOW+FLOW.m3u8"
    ], [
        "Practices for Deep Sleep",
        "https://d22rix4bfet7yn.cloudfront.net/34938/CLIP+-+Restore.m3u8"
    ], [
        "Primal Elements",
        "https://d22rix4bfet7yn.cloudfront.net/175566a/trailer+-+Primal+Elements.m3u8"
    ], [
        "Rest Revolution",
        "https://d22rix4bfet7yn.cloudfront.net/218126a/PROMO+-+RR.m3u8"
    ], [
        "Rise - Thrive",
        "https://d22rix4bfet7yn.cloudfront.net/119725a/34+Series+Promo-Rise+&+Thrive.m3u8"
    ], [
        "Root to Rise - From the Ground Up",
        "https://d22rix4bfet7yn.cloudfront.net/357453/Promo+-+Root+to+Rise+-+web.m3u8"
    ], [
        "Sleep Well",
        "https://d22rix4bfet7yn.cloudfront.net/71468/Trailer+-+Sleep+Well.m3u8"
    ], [
        "Stacked",
        "https://d22rix4bfet7yn.cloudfront.net/166402a/STACKED.m3u8"
    ], [
        "Start Your Day",
        "https://d22rix4bfet7yn.cloudfront.net/74149/CLIP+-+2Start+Your+Day+Meditation+Series+with+Lauren.m3u8"
    ], [
        "Summer Yoga Loving",
        "https://d22rix4bfet7yn.cloudfront.net/34945/CLIP+-+Balancing+ACTivation.m3u8"
    ], [
        "The Basics of Mindfulness",
        "https://d22rix4bfet7yn.cloudfront.net/239221a/INTRO_Mindfull.m3u8"
    ], [
        "The Sleep Well Series",
        "https://d22rix4bfet7yn.cloudfront.net/58469a/Trailer-Sleep_Well+-widescreen.m3u8"
    ], [
        "Transform",
        "https://d22rix4bfet7yn.cloudfront.net/110067/TRANSFORM+-+trailer+-+website.m3u8"
    ], [
        "Turn Up the Heat",
        "https://d22rix4bfet7yn.cloudfront.net/34937/CLIP+-+Power+Yoga+Classic.m3u8"
    ], [
        "Vinyasa-Less",
        "https://d22rix4bfet7yn.cloudfront.net/320794/Website+-+Vinyasa-less+-+Horizontal.m3u8"
    ], [
        "Vital Recharge",
        "https://d22rix4bfet7yn.cloudfront.net/413958/Vital_Intro_Web2.m3u8"
    ], [
        "Wild Yoga - Building to Peak Poses",
        "https://d22rix4bfet7yn.cloudfront.net/447422/Intro_Short_Wild_Yoga.m3u8"
    ], [
        "Work In & Work Out",
        "https://d22rix4bfet7yn.cloudfront.net/34940/CLIP+-+Double+Trouble.m3u8"
    ], [
        "Yin It to Win It",
        "https://d22rix4bfet7yn.cloudfront.net/243733/Yin+it+to+Win+it+-+Promo.m3u8"
    ], [
        "Yoga Basics",
        "https://d22rix4bfet7yn.cloudfront.net/127476/CLIP+Series+Promo+-+Yoga+Basics.m3u8"
    ], [
        "Yoga for Travel",
        "https://d22rix4bfet7yn.cloudfront.net/216823/preview+-+yoga+for+travel+.m3u8"
    ]

script_folder = os.path.dirname(os.path.realpath(__file__))
cookies_file = script_folder + '/cookies.txt'

def main():
    for trailer in trailers:
        download_trailer(trailer)

def download_trailer(trailer):
    series_name = trailer[0]
    trailer_url = trailer[1]

    output_folder = '/home/ziga/share/PaleoPrimal/0 Yoga/Eliot, Travis - Inner Dimension TV/Series/' + series_name + '/Materials/'

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
        ydl.download(trailer_url)
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

        ydl.download(trailer_url)
        

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