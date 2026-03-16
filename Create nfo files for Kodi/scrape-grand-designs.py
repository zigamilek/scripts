# By Ziga Milek, 2.10.2018
from __future__ import print_function
import json, re, requests, sys, os, codecs, urllib, hashlib, time, datetime
from random import randint
from requests.exceptions import HTTPError
from requests.exceptions import RequestException
from requests.exceptions import ChunkedEncodingError

##########################
# ---- set parameters ----
# TVMaze
tvmaze_grand_designs_url = "http://api.tvmaze.com/shows/3251/seasons"

# TheTVDB
thetvdb_username = "REMOVED_THETVDB_USERNAME"
thetvdb_user_key = "REMOVED_THETVDB_USER_KEY"
thetvdb_api_key = "REMOVED_THETVDB_API_KEY"
thetvdb_grand_designs_url = "https://api.thetvdb.com/series/79264/episodes"

# Skip episodes
skip_episodes = [
    "S19E01",
    "S19E02",
]

# Chrome user agent
CHROME_UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36'
# ---- end set parameters ----
##############################

def main():
    seasons = get_tvmaze_json(tvmaze_grand_designs_url)

    for season in seasons:
        season_url = season['_links']['self']['href']

        episodes = get_tvmaze_json(season_url + "/episodes")
        for episode in episodes:
            season_number = episode['season']
            episode_number = episode['number']
            season_and_episode = "S" + str(season_number).zfill(2) + "E" + str(episode_number).zfill(2)
            if season_and_episode in skip_episodes:
                continue
            name = episode['name']
            date = episode['airdate']
            plot = str(episode['summary']).replace("<p>","").replace("</p>","").replace(";",",")

            try:
                tvdb_episode = get_correct_thetvdb_season_and_episode(season_and_episode)
                #image = get_thetvdb_image(season_number, episode_number)
                image = get_thetvdb_image(tvdb_episode["season"], tvdb_episode["episode"])
            except (ValueError, KeyError):
                image = ""

            print("Scraping " + season_and_episode + ": " + name)

            try:
                episode_path = get_path(season_and_episode)
            except KeyError:
                continue

            filename = os.path.basename(episode_path)
            output_nfo = os.path.dirname(episode_path) + "/" + os.path.splitext(filename)[0] + ".nfo"

            generate_nfo(output_nfo, name, str(episode['season']), str(episode['number']), plot, date, episode_path, image)

def get_tvmaze_json(url):
    session = requests.Session()
    session.headers = { 'user-agent': CHROME_UA }

    response = session.get(url)

    return json.loads(response.text)

def generate_nfo(filename, title, season, episode, plot, aired, episode_path, image):
    file = codecs.open(filename,"w",'utf-8')

    file.write("\
<episodedetails>\n\
    <title>" + title + "</title>\n\
    <showtitle>Grand Designs</showtitle>\n\
    <season>" + season + "</season>\n\
    <episode>" + episode + "</episode>\n\
    <plot>" + plot + "</plot>\n\
    <thumb>" + image + "</thumb>\n\
    <mpaa>TV-PG</mpaa>\n\
    <path>smb://" + os.path.dirname(episode_path).replace("/home/ziga/share", "EULER/eulerShare") + "/</path>\n\
    <filenameandpath>smb://" + episode_path.replace("/home/ziga/share", "EULER/eulerShare") + "</filenameandpath>\n\
    <basepath>smb://" + episode_path.replace("/home/ziga/share", "EULER/eulerShare") + "</basepath>\n\
    <genre>Documentary</genre>\n\
    <genre>Home and Garden</genre>\n\
    <genre>Reality</genre>\n\
    <premiered>1999-04-29</premiered>\n\
    <year>" + aired[:4] + "</year>\n\
    <aired>" + aired + "</aired>\n\
    <studio>Channel 4</studio>\n\
    <actor>\n\
        <name>Kevin McCloud</name>\n\
        <role>Presenter</role>\n\
        <order>0</order>\n\
        <thumb>http://thetvdb.com/banners/actors/70483.jpg</thumb>\n\
    </actor>\n\
    <art>\n\
        <thumb>" + image + "</thumb>\n\
    </art>\n\
</episodedetails>")

    file.close()

def get_path(season_and_episode):
    paths = {
        "S01E01": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 01/Grand Designs - S01E01 - Newhaven - The Timber Frame Kit House.avi",
        "S01E02": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 01/Grand Designs - S01E02 - Berkshire - English Barn.avi",
        "S01E03": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 01/Grand Designs - S01E03 - Brighton - The Co-Operative Build.avi",
        "S01E04": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 01/Grand Designs - S01E04 - Amersham - The Water Tower.avi",
        "S01E05": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 01/Grand Designs - S01E05 - Suffolk - The Eco-House.avi",
        "S01E06": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 01/Grand Designs - S01E06 - Cornwall - The Chapel.avi",
        "S01E07": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 01/Grand Designs - S01E07 - Islington - The House of Straw.avi",
        "S01E08": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 01/Grand Designs - S01E08 - Doncaster - The Glass House.avi",
        "S02E01": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 02/Grand Designs - S02E01 - Farnham - The Regency Villa.avi",
        "S02E02": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 02/Grand Designs - S02E02 - Sussex - The New England Gable House.avi",
        "S02E03": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 02/Grand Designs - S02E03 - Netherton - The Wool Mill.avi",
        "S02E04": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 02/Grand Designs - S02E04 - Brecon Beacons - The Isolated Cottage.avi",
        "S02E05": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 02/Grand Designs - S02E05 - Lambourn Valley - The Cruciform House.avi",
        "S02E06": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 02/Grand Designs - S02E06 - Birmingham - The Self-Build.avi",
        "S02E07": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 02/Grand Designs - S02E07 - London - The Jewel Box.avi",
        "S02E08": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 02/Grand Designs - S02E08 - Devon - The Derelict Barns.avi",
        "S02E09": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 02/Grand Designs - S02E09 - Revisited - Doncaster - The Glass-House (Revisited from S1 Ep8).avi",
        "S02E10": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 02/Grand Designs - S02E10 - Revisited - Suffolk - The Eco-House (Revisited from S1 Ep5).avi",
        "S02E11": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 02/Grand Designs - S02E11 - Revisited - Islington - The House of Straw (Revisited from S1 Ep7).avi",
        "S02E12": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 02/Grand Designs - S02E12 - Revisited - Birmingham - The Self-Build (Revisited from S2 Ep6).avi",
        "S02E13": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 02/Grand Designs - S02E13 - Revisited - Brighton - The Co-Op (Revisited from S1 Ep3).avi",
        "S02E14": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 02/Grand Designs - S02E14 - Revisited - Brecon Beacons Wales - The Isolated Cottage (Revisited from S2 Ep4).avi",
        "S02E15": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 02/Grand Designs - S02E15 - Revisited - London - The Dilapidated Georgian House (Revisited from Grand Designs Indoors - 15 March 2001).avi",
        "S02E16": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 02/Grand Designs - S02E16 - Revisited - Coleshill Amersham - The Water Tower (Revisited from S1 Ep4).avi",
        "S02E17": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 02/Grand Designs - S02E17 - Revisited - Devon - The Derelict Barns (Revisited from S2 Ep8).avi",
        "S03E01": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 03/Grand Designs - S03E01 - Peterborough - The Wooden Box.avi",
        "S03E02": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 03/Grand Designs - S03E02 - Chesterfield - The Water-Works.mp4",
        "S03E03": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 03/Grand Designs - S03E03 - Sussex - The Woodsmans Cottage.avi",
        "S03E04": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 03/Grand Designs - S03E04 - Surrey - The Victorian Threshing Barn.avi",
        "S03E06": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 03/Grand Designs - S03E06 - Hackney - The Terrace Conversion.avi",
        "S03E07": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 03/Grand Designs - S03E07 - Cumbria - The Underground House.avi",
        "S03E08": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 03/Grand Designs - S03E08 - Herefordshire - The Traditional Cottage.avi",
        "S03E11": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 03/Grand Designs - S03E11 - Revisited - Sunderland - The Former Electricity Sub-Station (Revisited from Grand Designs Indoors - 1 March 2001).avi",
        "S03E12": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 03/Grand Designs - S03E12 - Revisited - Berkshire - The English Barn (Revisited from S1 Ep2).avi",
        "S04E01": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 04/Grand Designs - S04E01 - Lambeth - The Violin Factory.avi",
        "S04E02": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 04/Grand Designs - S04E02 - Walton on Thames - Customised German Kit House.avi",
        "S04E03": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 04/Grand Designs - S04E03 - Revisited - Buckinghamshire - The Inverted-Roof House (Revisited from S3 Ep5).avi",
        "S04E04": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 04/Grand Designs - S04E04 - Leith - 19th Century Sandstone House.avi",
        "S04E05": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 04/Grand Designs - S04E05 - Clapham - The Curved House.avi",
        "S04E06": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 04/Grand Designs - S04E06 - Sussex - The Modernist Sugar Cube.avi",
        "S04E07": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 04/Grand Designs - S04E07 - Argyll - The Oak-Framed House.avi",
        "S04E08": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 04/Grand Designs - S04E08 - Dorset - An Idiosyncratic Home.avi",
        "S05E02": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 05/Grand Designs - S05E02 - Peckham - The sliding glass roof house.avi",
        "S05E03": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 05/Grand Designs - S05E03 - Gloucester - The 16th Century Farmhouse.avi",
        "S05E04": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 05/Grand Designs - S05E04 - Kent - Finnish Log Cabin.avi",
        "S05E05": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 05/Grand Designs - S05E05 - Revisited - Hackney - The Terrace Conversion (Revisited from S3 Ep6).avi",
        "S05E07": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 05/Grand Designs - S05E07 - Shaldon - Shaped Like a Curvy Seashell.avi",
        "S05E09": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 05/Grand Designs - S05E09 - Belfast - A 21st Century Answer to the Roman Villa.avi",
        "S05E10": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 05/Grand Designs - S05E10 - Devon - The Miami-Style Beach House.avi",
        "S05E11": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 05/Grand Designs - S05E11 - Carmarthen - The Eco-House.avi",
        "S06E01": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 06/Grand Designs - S06E01 - Killearn - The Loch House.avi",
        "S06E02": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 06/Grand Designs - S06E02 - Ross-on-Wye - The Contemporary Barn Conversion.avi",
        "S06E03": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 06/Grand Designs - S06E03 - Stirling - The Contemporary Cedar Clad Home.avi",
        "S06E04": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 06/Grand Designs - S06E04 - Ashford - Water Tower Conversion.avi",
        "S06E07": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 06/Grand Designs - S06E07 - Exeter - Garden House aka Mies van der Rohe Inspired House.avi",
        "S07E01": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 07/Grand Designs - S07E01 - Skipton - The 14th Century Castle (90 minutes).avi",
        "S07E02": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 07/Grand Designs - S07E02 - Hampshire - The Thatched Cottage.avi",
        "S07E03": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 07/Grand Designs - S07E03 - Medway - The Eco-Barge.avi",
        "S07E04": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 07/Grand Designs - S07E04 - Bournemouth - The Bournemouth Penthouse.avi",
        "S07E05": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 07/Grand Designs - S07E05 - Revisited - Carmarthen - The Eco-House (Revisited from S5 Ep11).avi",
        "S07E06": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 07/Grand Designs - S07E06 - Tipton - The Birmingham Church.avi",
        "S07E07": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 07/Grand Designs - S07E07 - Guildford - The Art Deco House.avi",
        "S07E08": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 07/Grand Designs - S07E08 - Revisited - Peckham - The Sliding Glass Roof House (Revisited from S5 Ep2).avi",
        "S07E09": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 07/Grand Designs - S07E09 - Revisited - Argyll - The Oak-Framed House (Revisited from S4 Ep7).avi",
        "S07E10": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 07/Grand Designs - S07E10 - Cambridgeshire - The Cambridgeshire Eco Home.avi",
        "S07E11": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 07/Grand Designs - S07E11 - Revisited - Tuscany - The Tuscan Castle (Revisited from Grand Designs Abroad - 13 October 2004).avi",
        "S07E12": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 07/Grand Designs - S07E12 - Dulwich - The Glass & Timber House.avi",
        "S08E01": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 08/Grand Designs - S08E01 - Cheltenham - The Underground House.avi",
        "S08E02": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 08/Grand Designs - S08E02 - Oxford - The Decagon House.avi",
        "S08E03": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 08/Grand Designs - S08E03 - Bristol - The Modernist Sugar Cube.avi",
        "S08E04": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 08/Grand Designs - S08E04 - Herefordshire - The Gothic House.avi",
        "S08E05": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 08/Grand Designs - S08E05 - Midlothian - The Lime Kiln House.avi",
        "S08E06": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 08/Grand Designs - S08E06 - Bath - The Bath Kit House.avi",
        "S08E07": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 08/Grand Designs - S08E07 - Revisited - Puglia - An Artists' Retreat (Revisited from Grand Designs Abroad - 22 September 2004).avi",
        "S08E08": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 08/Grand Designs - S08E08 - Revisited - Peterborough - The Wooden Box (Revisited from S3 Ep1).avi",
        "S08E09": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 08/Grand Designs - S08E09 - Revisited - Surrey - Customised German Kit House (Revisited from S4 Ep2).avi",
        "S08E10": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 08/Grand Designs - S08E10 - Revisited - Surrey - The Victorian Threshing Barn (Revisited from S3 Ep4).avi",
        "S08E11": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 08/Grand Designs - S08E11 - Revisited - Cumbria - The Underground House (Revisited from S3 Ep7).avi",
        "S08E12": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 08/Grand Designs - S08E12 - Maidstone - The Hi Tech Bungalow.avi",
        "S09E01": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 09/Grand Designs - S09E01 - Somerset - The Apprentice Store.avi",
        "S09E02": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 09/Grand Designs - S09E02 - Oxfordshire - The Chilterns Water Mill.avi",
        "S09E03": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 09/Grand Designs - S09E03 - Newport - The Newport Folly.avi",
        "S09E04": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 09/Grand Designs - S09E04 - Kent - The Eco Arch.avi",
        "S09E05": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 09/Grand Designs - S09E05 - Brittany - The Brittany Groundhouse.avi",
        "S09E06": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 09/Grand Designs - S09E06 - Wiltshire - The Marlborough Farm House.avi",
        "S09E07": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 09/Grand Designs - S09E07 - Kent - The Headcorn Minimalist House.avi",
        "S09E08": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 09/Grand Designs - S09E08 - Revisited - The 14th Century Castle (Revisited from S7 Ep1).avi",
        "S09E09": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 09/Grand Designs - S09E09 - Revisited - Cambridgeshire - The Cambridgeshire Eco Home (Revisited from S7 Ep10).avi",
        "S09E10": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 09/Grand Designs - S09E10 - Brighton - The Brighton Modern Mansion.avi",
        "S09E11": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 09/Grand Designs - S09E11 - Revisited - Hampshire - The Thatched Cottage (Revisited from S7 Ep2).avi",
        "S09E12": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 09/Grand Designs - S09E12 - Revisited - Killearn Scotland - The Loch House (Revisited from S6 Ep1).avi",
        "S09E13": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 09/Grand Designs - S09E13 - 2nd Revisit - Sussex - The Woodsmans Cottage (Revisited from S3 Ep3 & S5 Ep8).avi",
        "S10E01": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 10/Grand Designs - S10E01 - Isle of Wight - The Tree House.avi",
        "S10E02": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 10/Grand Designs - S10E02 - Cotswolds - The Stealth House.avi",
        "S10E03": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 10/Grand Designs - S10E03 - Woodbridge - The Modest Home.avi",
        "S10E04": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 10/Grand Designs - S10E04 - Stowmarket - The Barn & Guildhall.avi",
        "S10E05": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 10/Grand Designs - S10E05 - Ipswich - The Radian House.avi",
        "S10E06": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 10/Grand Designs - S10E06 - Lizard Peninsular - The Scandinavian House.avi",
        "S10E07": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 10/Grand Designs - S10E07 - Cumbria - The Adaptahaus.avi",
        "S10E08": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 10/Grand Designs - S10E08 - Lake District - The Dome House.avi",
        "S10E09": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 10/Grand Designs - S10E09 - Revisited - Brittany France - The Brittany Groundhouse (Revisited from S9 Ep5).avi",
        "S10E10": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 10/Grand Designs - S10E10 - Revisited - Dulwich - The Glass & Timber House (Revisited from S7 Ep12).avi",
        "S10E11": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 10/Grand Designs - S10E11 - Revisited - Belfast - A 21st Century Answer to the Roman Villa (Revisited from S5 Ep9).avi",
        "S10E12": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 10/Grand Designs - S10E12 - Revisited - Lot France - House from Straw (Revisited from Grand Designs Abroad - 15 September 2004).avi",
        "S10E13": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 10/Grand Designs - S10E13 - Coleshill Amersham - 2nd Revisit - The Water Tower (Revisited from S1 Ep4 and S2 Ep16).avi",
        "S10E14": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 10/Grand Designs - S10E14 - Revisited - Midlothian Scotland - The Lime Kiln House (Revisited from S8 Ep5).avi",
        "S11E01": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 11/Grand Designs - S11E01 - Morpeth - The Derelict Mill Cottage.avi",
        "S11E02": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 11/Grand Designs - S11E02 - London - The Contemporary Mansion.avi",
        "S11E03": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 11/Grand Designs - S11E03 - Tenby - The Lifeboat Station.avi",
        "S11E04": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 11/Grand Designs - S11E04 - Essex - The Large Timber-framed Barn.avi",
        "S11E05": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 11/Grand Designs - S11E05 - Herefordshire - The Recycled Timber-framed House.avi",
        "S11E06": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 11/Grand Designs - S11E06 - Cornwall - The Dilapidated Engine House.avi",
        "S11E07": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 11/Grand Designs - S11E07 - London - The Disco Home.avi",
        "S11E08": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 11/Grand Designs - S11E08 - Revisited - Lake District - The Dome House.avi",
        "S11E09": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 11/Grand Designs - S11E09 - Revisited - Kent - The Eco Arch.avi",
        "S11E10": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 11/Grand Designs - S11E10 - Revisited - Ashford Kent - The Water Tower Conversion.avi",
        "S11E11": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 11/Grand Designs - S11E11 - Revisited - Cumbria - The Adaptahaus.avi",
        "S11E12": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 11/Grand Designs - S11E12 - Revisited - Kent - The Headcorn Minimalist House.avi",
        "S12E01": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 12/Grand Designs - S12E01 - Roscommon Ireland - Cloontykilla Castle.avi",
        "S12E02": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 12/Grand Designs - S12E02 - Hertfordshire - The Computer-cut House.avi",
        "S12E03": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 12/Grand Designs - S12E03 - Brixton - The Glass Cubes House.avi",
        "S12E04": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 12/Grand Designs - S12E04 - Oxfordshire - The Thames Boathouse.avi",
        "S12E05": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 12/Grand Designs - S12E05 - London - The Derelict Water Tower.mkv",
        "S12E06": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 12/Grand Designs - S12E06 - London - The Underground House.mkv",
        "S12E07": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 12/Grand Designs - S12E07 - Isle of Skye - The Larch-Clad House.avi",
        "S12E08": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 12/Grand Designs - S12E08 - London - The Joinery Workshop.avi",
        "S12E09": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 12/Grand Designs - S12E09 - Revisited - Isle of Wight - The Tree House.avi",
        "S12E10": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 12/Grand Designs - S12E10 - Revisited - London - The Disco Home.avi",
        "S12E11": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 12/Grand Designs - S12E11 - Revisited - Essex - The Large Timber-Framed Barn.avi",
        "S12E12": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 12/Grand Designs - S12E12 - 2nd Revisiting - Brighton - The Co-Op.avi",
        "S13E01": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 13/Grand Designs - S13E01 - South Yorkshire - The 1920's Cinema.mkv",
        "S13E02": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 13/Grand Designs - S13E02 - North London - The Miniature Hollywood Mansion.mkv",
        "S13E03": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 13/Grand Designs - S13E03 - York - The Giant Farm Shed.mkv",
        "S13E04": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 13/Grand Designs - S13E04 - Tiverton - Crooked Chocolate Box Cottage.mkv",
        "S13E05": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 13/Grand Designs - S13E05 - South Lanarkshire - Metal Sculptural Home.mkv",
        "S13E06": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 13/Grand Designs - S13E06 - Monmouthshire - Japanese House.mkv",
        "S13E07": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 13/Grand Designs - S13E07 - South London - Modernist Masterpiece.mkv",
        "S13E08": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 13/Grand Designs - S13E08 - East Devon - Cob Castle.mkv",
        "S13E09": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 13/Grand Designs - S13E09 - Newbury - Christmas Farm.mkv",
        "S13E10": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 13/Grand Designs - S13E10 - Revisited - Málaga Spain - The Modernist Villa.mkv",
        "S13E11": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 13/Grand Designs - S13E11 - Revisited - Woodbridge - The Modest Home.mkv",
        "S14E01": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 14/Grand Designs - S14E01 - North Wales - The Clifftop House.mkv",
        "S14E02": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 14/Grand Designs - S14E02 - North Cornwall - The Cross-Laminated Timber House.mkv",
        "S14E03": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 14/Grand Designs - S14E03 - Milton Keynes - Round House.mkv",
        "S14E04": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 14/Grand Designs - S14E04 - County Derry - Shipping Container House.mkv",
        "S14E05": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 14/Grand Designs - S14E05 - South East London - Urban Shed.mkv",
        "S14E06": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 14/Grand Designs - S14E06 - Norfolk - Periscope House.mkv",
        "S14E07": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 14/Grand Designs - S14E07 - River Thames - Floating House.mkv",
        "S14E08": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 14/Grand Designs - S14E08 - Revisited - Creuse France - 19th Century Manor House.mkv",
        "S14E09": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 14/Grand Designs - S14E09 - Revisited - Monmouthshire - Japanese House.mkv",
        "S14E10": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 14/Grand Designs - S14E10 - Revisited - Tiverton - Crooked Chocolate Box Cottage.mkv",
        "S15E01": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 15/Grand Designs - S15E01 - Living in the City.mkv",
        "S15E02": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 15/Grand Designs - S15E02 - Living in the Wild.mkv",
        "S15E03": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 15/Grand Designs - S15E03 - Living in Suburbia.mkv",
        "S15E04": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 15/Grand Designs - S15E04 - Living in the Country.mkv",
        "S16E01": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 16/Grand Designs - S16E01 - West Sussex - The Perfectionist's Bungalow.mkv",
        "S16E02": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 16/Grand Designs - S16E02 - East Sussex - The Boat House.mkv",
        "S16E03": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 16/Grand Designs - S16E03 - Solent - The Seaside House.mkv",
        "S16E04": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 16/Grand Designs - S16E04 - Wyre Forest - The Cave House.mkv",
        "S16E05": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 16/Grand Designs - S16E05 - County Antrim - The Blacksmith's House.mkv",
        "S16E06": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 16/Grand Designs - S16E06 - Somerset - The Concrete Cow-Shed.mkv",
        "S16E07": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 16/Grand Designs - S16E07 - South Downs - The Rusty Metal House.mkv",
        "S16E08": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 16/Grand Designs - S16E08 - Revisited - River Thames - Floating House.mkv",
        "S16E09": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 16/Grand Designs - S16E09 - Revisited - North Cornwall - The Cross-Laminated Timber House.mkv",
        "S17E01": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 17/Grand Designs - S17E01 - Gloucestershire - Treehouse.mkv",
        "S17E02": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 17/Grand Designs - S17E02 - Horsham - Fun House.mkv",
        "S17E03": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 17/Grand Designs - S17E03 - South Cornwall - Wavy Wooden House.mkv",
        "S17E04": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 17/Grand Designs - S17E04 - Essex - Black House.mkv",
        "S17E05": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 17/Grand Designs - S17E05 - Bolton - Ultra-Modern House.mkv",
        "S17E06": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 17/Grand Designs - S17E06 - Pembrokeshire - Low-Impact House.mkv",
        "S17E07": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 17/Grand Designs - S17E07 - Devon - Plough-Shaped House.mkv",
        "S17E08": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 17/Grand Designs - S17E08 - The Wirral - Floating Timber House.mkv",
        "S17E09": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 17/Grand Designs - S17E09 - Revisited - Somerset - Concrete Cow Shed.mp4",
        "S18E01": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 18 (2017-18) [1080p HDTV]/Grand Designs - S18E01 - Malvern - Hill House.mkv",
        "S18E02": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 18 (2017-18) [1080p HDTV]/Grand Designs - S18E02 - Harringey London - Victorian Gatehouse.mkv",
        "S18E03": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 18 (2017-18) [1080p HDTV]/Grand Designs - S18E03 - County Down - Agricultural House.mkv",
        "S18E04": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 18 (2017-18) [1080p HDTV]/Grand Designs - S18E04 - South Hertfordshire - Roman House.mkv",
        "S18E05": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 18 (2017-18) [1080p HDTV]/Grand Designs - S18E05 - South East London - Victorian Dairy House.mkv",
        "S18E06": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 18 (2017-18) [1080p HDTV]/Grand Designs - S18E06 - Blackdown Hills Devon - Snake House.mkv",
        "S18E07": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 18 (2017-18) [1080p HDTV]/Grand Designs - S18E07 - Peak District - Post-Industrial House.mkv",
        "S18E08": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 18 (2017-18) [1080p HDTV]/Grand Designs - S18E08 - London - Miniscule House.mkv",
        "S18E09": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 18 (2017-18) [1080p HDTV]/Grand Designs - S18E09 - Revisited - Herefordshire - The Recycled Timber-Framed House.mkv",
        "S19E01": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 19 (2018-19) [720p HDTV]/Grand Designs - S19E01 - Aylsebury Vale - Folly House.mkv",
        "S19E02": "/home/ziga/share/Series/Other/0 Home and Gardening/Grand Designs/Season 19 (2018-19) [720p HDTV]/Grand Designs - S19E02 - Padstow Cornwall - American Modernist House.mkv"
    }

    return paths[season_and_episode]

def get_thetvdb_session(username, userKey, apiKey):
    # generate token
    url = "https://api.thetvdb.com/login"
    headers = { "Content-Type": "application/json", "Accept": "application/json" }
    payload = '{ "apikey": "'+apiKey+'", "username": "'+username+'", "userkey": "'+userKey+'" }'
    response = requests.post(url=url, data=payload, headers=headers)
    token = json.loads(response.text)["token"]

    # generate session to return
    session = requests.Session()
    session.headers = { "Content-Type": "application/json", "Accept": "application/json", "Authorization": "Bearer " + token }

    return session

def get_thetvdb_json(url):
    thetvdb_session = get_thetvdb_session(thetvdb_username, thetvdb_user_key, thetvdb_api_key)

    response = thetvdb_session.get(url)

    return json.loads(response.text)

def get_thetvdb_image(season_number, episode_number):
    j = get_thetvdb_json(thetvdb_grand_designs_url + "/query?airedSeason=" + str(season_number) + "&airedEpisode=" + str(episode_number))

    return "https://www.thetvdb.com/banners/" + j["data"][0]["filename"]

def get_correct_thetvdb_season_and_episode(season_and_episode):
    episodes = {
        "S01E01": "S01E01",
        "S01E02": "S01E02",
        "S01E03": "S01E03",
        "S01E04": "S01E04",
        "S01E05": "S01E05",
        "S01E06": "S01E06",
        "S01E07": "S01E07",
        "S01E08": "S01E08",
        "S02E01": "S02E01",
        "S02E02": "S02E02",
        "S02E03": "S02E03",
        "S02E04": "S02E04",
        "S02E05": "S02E05",
        "S02E06": "S02E06",
        "S02E07": "S02E07",
        "S02E08": "S02E08",
        "S02E09": "S01E09",
        "S02E10": "S01E10",
        "S02E11": "S01E11",
        "S02E12": "S02E09",
        "S02E13": "S01E12",
        "S02E14": "S02E10",
        "S02E15": "",
        "S02E16": "S01E13",
        "S02E17": "S02E11",
        "S03E01": "S03E01",
        "S03E02": "S03E02",
        "S03E03": "S03E03",
        "S03E04": "S03E04",
        "S03E05": "S03E05",
        "S03E06": "S03E06",
        "S03E07": "S03E07",
        "S03E08": "S03E08",
        "S03E09": "S02E12",
        "S03E10": "S01E14",
        "S03E11": "",
        "S03E12": "S01E15",
        "S04E01": "S04E01",
        "S04E02": "S04E02",
        "S04E03": "S03E09",
        "S04E04": "S04E03",
        "S04E05": "S04E04",
        "S04E06": "S04E05",
        "S04E07": "S04E06",
        "S04E08": "S04E07",
        "S05E01": "S04E08",
        "S05E02": "S05E01",
        "S05E03": "S05E02",
        "S05E04": "S05E03",
        "S05E05": "S03E10",
        "S05E06": "S04E09",
        "S05E07": "S05E04",
        "S05E08": "S03E11",
        "S05E09": "S05E05",
        "S05E10": "S05E06",
        "S05E11": "S05E07",
        "S06E01": "S06E01",
        "S06E02": "S06E02",
        "S06E03": "S06E03",
        "S06E04": "S06E04",
        "S06E05": "",
        "S06E06": "",
        "S06E07": "S06E05",
        "S06E08": "S04E10",
        "S07E01": "S07E01",
        "S07E02": "S07E02",
        "S07E03": "S07E03",
        "S07E04": "S07E04",
        "S07E05": "S05E08",
        "S07E06": "S07E05",
        "S07E07": "S07E06",
        "S07E08": "S05E09",
        "S07E09": "S04E12",
        "S07E10": "S07E07",
        "S07E11": "",
        "S07E12": "S07E08",
        "S08E01": "S08E01",
        "S08E02": "S08E02",
        "S08E03": "S08E03",
        "S08E04": "S08E04",
        "S08E05": "S08E05",
        "S08E06": "S08E06",
        "S08E07": "",
        "S08E08": "S03E12",
        "S08E09": "S04E11",
        "S08E10": "S03E13",
        "S08E11": "S03E14",
        "S08E12": "S08E07",
        "S09E01": "S09E01",
        "S09E02": "S09E02",
        "S09E03": "S09E03",
        "S09E04": "S09E04",
        "S09E05": "S09E05",
        "S09E06": "S09E06",
        "S09E07": "S09E07",
        "S09E08": "S07E09",
        "S09E09": "S07E10",
        "S09E10": "S09E08",
        "S09E11": "S07E11",
        "S09E12": "S06E06",
        "S09E13": "S03E15",
        "S10E01": "S10E01",
        "S10E02": "S10E02",
        "S10E03": "S10E03",
        "S10E04": "S10E04",
        "S10E05": "S10E05",
        "S10E06": "S10E06",
        "S10E07": "S10E07",
        "S10E08": "S10E08",
        "S10E09": "S09E09",
        "S10E10": "S07E12",
        "S10E11": "S05E10",
        "S10E12": "",
        "S10E13": "S01E16",
        "S10E14": "S08E08",
        "S11E01": "S11E01",
        "S11E02": "S11E02",
        "S11E03": "S11E03",
        "S11E04": "S11E04",
        "S11E05": "S11E05",
        "S11E06": "S11E06",
        "S11E07": "S11E07",
        "S11E08": "S10E09",
        "S11E09": "S09E10",
        "S11E10": "S06E07",
        "S11E11": "S10E10",
        "S11E12": "S09E11",
        "S12E01": "S12E01",
        "S12E02": "S12E02",
        "S12E03": "S12E03",
        "S12E04": "S12E04",
        "S12E05": "S12E05",
        "S12E06": "S12E06",
        "S12E07": "S12E07",
        "S12E08": "S12E08",
        "S12E09": "S10E11",
        "S12E10": "S11E08",
        "S12E11": "S11E09",
        "S12E12": "S01E17",
        "S13E01": "S13E01",
        "S13E02": "S13E02",
        "S13E03": "S13E03",
        "S13E04": "S13E04",
        "S13E05": "S13E05",
        "S13E06": "S13E06",
        "S13E07": "S13E07",
        "S13E08": "S13E08",
        "S13E09": "S13E09",
        "S13E10": "",
        "S13E11": "S10E12",
        "S14E01": "S14E01",
        "S14E02": "S14E02",
        "S14E03": "S14E03",
        "S14E04": "S14E04",
        "S14E05": "S14E05",
        "S14E06": "S14E06",
        "S14E07": "S14E07",
        "S14E08": "S14E08",
        "S14E09": "S14E09",
        "S14E10": "S14E10",
        "S15E01": "S15E01",
        "S15E02": "S15E02",
        "S15E03": "S15E03",
        "S15E04": "S15E04",
        "S16E01": "S16E01",
        "S16E02": "S16E02",
        "S16E03": "S16E03",
        "S16E04": "S16E04",
        "S16E05": "S16E05",
        "S16E06": "S16E06",
        "S16E07": "S16E07",
        "S16E08": "S16E08",
        "S16E09": "S16E09",
        "S17E01": "S17E01",
        "S17E02": "S17E02",
        "S17E03": "S17E03",
        "S17E04": "S17E04",
        "S17E05": "S17E05",
        "S17E06": "S17E06",
        "S17E07": "S17E07",
        "S17E08": "S17E08",
        "S17E09": "S17E09",
        "S18E01": "S18E01",
        "S18E02": "S18E02",
        "S18E03": "S18E03",
        "S18E04": "S18E04",
        "S18E05": "S18E05",
        "S18E06": "S18E06",
        "S18E07": "S18E07",
        "S18E08": "S18E08",
        "S18E09": "S18E09",
        "S19E01": "S19E01",
        "S19E02": "S19E02"
    }

    new_season_and_episode = episodes[season_and_episode]

    season = int(float(new_season_and_episode[1:3]))
    episode = int(float(new_season_and_episode[-2:]))

    dict_to_return = {
        "season": season,
        "episode": episode
    }

    return dict_to_return

main()
