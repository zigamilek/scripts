import json
import os
import yt_dlp
import urllib.request
from pathlib import Path

#course = 'Mastering Tabular'
#course = 'Introduction to Data Modeling'
#course = 'Introducing DAX'
#course = 'DAX Tools'
course = 'Data Modeling for Power BI'
#course = 'Mastering DAX'

script_folder = os.path.dirname(os.path.realpath(__file__))
folder_with_jsons = script_folder + '/courses/' + course + '/'

cookies_file = script_folder + 'cookies.txt'
sections_file = folder_with_jsons + 'sections.json'
lectures_file = folder_with_jsons + 'lectures.json'

output_folder = '/home/ziga/share/Business/0 Favorite Authors/SQLBI/' + course + '/'

def main():
    with open(lectures_file, 'r') as lectures:
        l = json.load(lectures)
        j = 0

        # loop through all lectures
        for lecture_uuid in l.keys():
            j = j + 1
            #lecture_id = l[lecture_uuid]['id']
            #lecture_url = 'https://www.sqlbi.com/learn/mastering-tabular-video-course/' + lecture_id + '/'
            lecture_title = l[lecture_uuid]['title'].replace('/', '-')
            lecture_type = l[lecture_uuid]['type']
            parent_uuid = l[lecture_uuid]['parent']

            # connect the lecture with its section
            with open(sections_file, 'r') as sections:
                s = json.load(sections)
                i = 0

                for section_uuid in s.keys():
                    i = i + 1

                    if section_uuid != parent_uuid: continue

                    # get the section title
                    section_title = s[section_uuid]['title']

                    # create a folder for each section
                    section_folder = str(i) + ' - ' + section_title.replace('/', '-')
                    try: 
                        os.mkdir(output_folder + section_folder) 
                    except FileExistsError as error:
                        #print(error)
                        pass

            # print what lecture we're working on
            print('--------------------')
            print(section_title + ' - ' + str(j) + ' - ' + lecture_title + ' (' + lecture_type + ')')
            print()

            # output file name
            output_file_without_extension = output_folder + section_folder + '/' + str(j) + ' - ' + lecture_title

            # download video
            if lecture_type == 'video':
                video_id = l[lecture_uuid]['video']
                video_url = 'https://player.vimeo.com/video/' + video_id
                #video_url = 'https://www.youtube.com/watch?v=' + video_id

                yt_opts = {
                    #'verbose': True,
                    'cookiefile': cookies_file,
                    'http_headers': {
                        'Referer': 'https://www.sqlbi.com'
                    },
                    'outtmpl': output_file_without_extension + '.%(ext)s',
                    'restrictfilenames': True,
                    'windowsfilenames': True
                }

                ydl = yt_dlp.YoutubeDL(yt_opts)

                ydl.download(video_url)
            # download text
            elif lecture_type == 'text':
                with open(output_file_without_extension + '.html', 'w') as text_file:
                    text_file.write(l[lecture_uuid]['text'])

            # save files and links
            files = l[lecture_uuid]['files']
            if len(files) > 0:
                for file in files:
                    file_title = file['title'].replace('/', '-')
                    file_url = file['url']
                    file_type = file['type']

                    # create the "Files" folder
                    try: 
                        os.mkdir(output_folder + section_folder + '/Files/') 
                    except FileExistsError as error:
                        #print(error)
                        pass

                    # save the files
                    if file_type == 'file':
                        output_file = output_folder + section_folder + '/Files/' + file_title

                        # download the file if it doesn't exist
                        if os.path.isfile(output_file) == False:
                            opener = urllib.request.build_opener()
                            opener.addheaders = [('User-agent', 'Mozilla/5.0')]
                            urllib.request.install_opener(opener)
                            urllib.request.urlretrieve(file_url.replace(' ', '%20'), output_file)
                    # save the links
                    elif file_type == 'web':
                        with open(output_folder + section_folder + '/Files/' + file_title + '.txt', 'w') as text_file:
                            text_file.write(file_url)                    

            print()
            print('DONE!')
            print()

if __name__ == "__main__":
    """ This is executed when run from the command line """
    main()