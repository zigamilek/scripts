import json
import re
import os
import yt_dlp
from http.cookiejar import MozillaCookieJar
from pathlib import Path
import requests
from bs4 import BeautifulSoup

#course = 'Power Query Fundamentals'
#course = 'Dimensional Modeling for the Power BI Pro'
#course = 'Dimensional Modeling for the Excel Pro'
course = 'The Art and Science of Data Visualization'

#course_url = 'https://skillwave.training/courses/power-query-fundamentals/lessons/welcome-to-power-query-fundamentals/'
#course_url = 'https://skillwave.training/courses/dimensional-modeling-for-the-power-bi-pro/lessons/course-introduction-pbi/'
#course_url = 'https://skillwave.training/courses/dimensional-modeling-for-the-excel-pro/lessons/course-introduction/'
course_url = 'https://skillwave.training/courses/the-art-and-science-of-data-visualization/lessons/welcome-to-the-course-data-viz/'

script_folder = os.path.dirname(os.path.realpath(__file__))

cookies_file = os.path.join(script_folder, 'cookies.txt')

output_folder = os.path.join('/home/ziga/share/Business/0 Favorite Authors/Skillwave/', course)

# create the folder for the course
os.makedirs(output_folder, exist_ok=True)

def main():
    # set cookies and headers
    jar = MozillaCookieJar(Path(cookies_file))
    jar.load()

    headers = {
        'User-Agent': 'Mozilla/5.0',
    }

    page = requests.get(course_url, cookies=jar, headers=headers)
    soup = BeautifulSoup(page.content, "html.parser")

    lesson_list = soup.find(id="lesson_list")

    modules = lesson_list.find_all("div", class_="lesson_sidebar_module_area")

    m = 0
    for module in modules:
        m = m + 1
        
        #print(module)
        
        module_title = slugify(module.find("a")['title'])
        print(module_title)
        
        module_folder = os.path.join(output_folder, f"{m} - {module_title}")

        # create the folder for the module
        try: 
            os.mkdir(module_folder) 
        except FileExistsError as error:
            #print(error)
            pass

        lessons = module.find_all("div", class_="lesson_sidebar_module_lesson_single")
        j = 0
        for lesson in lessons:
            j = j + 1
            # --------------
            # Download lesson page
            lesson_url = lesson.find("a")['href']
            lesson_page = requests.get(lesson_url, cookies=jar, headers=headers)
            
            lesson_soup = BeautifulSoup(lesson_page.content, "html.parser")

            lesson_title = slugify(lesson_soup.find("div", class_="lesson_player_info_bottom_left").find("h2").text)
            print("    " + lesson_title)

            lesson_folder = os.path.join(module_folder, f"{j} - {lesson_title}")

            # create the folder for the lesson
            try: 
                os.mkdir(lesson_folder) 
            except FileExistsError as error:
                #print(error)
                pass

            quiz = lesson_soup.find("div", class_="wpProQuiz_content")
            if quiz != None: continue # Ignore Quiz lessons

            lesson_content = lesson_soup.find("div", class_="lesson_video_player")

            lesson_output_file = os.path.join(lesson_folder, 'Lesson.html')

            with open(lesson_output_file, 'w') as f:
                f.write('<h1>' + lesson_title + '</h1>')
                f.write(lesson_content.prettify())

            # --------------
            # Download video
            yt_opts = {
                #'verbose': True,
                'cookiefile': cookies_file,
                'restrictfilenames': True,
                'windowsfilenames': True,
                'outtmpl': os.path.join(lesson_folder, f"{lesson_title}.%(ext)s"),
                'ignoreerrors': True
            }

            ydl = yt_dlp.YoutubeDL(yt_opts)

            ydl.download(lesson_url)

            # --------------
            # Download files
            file_links = lesson_soup.find("div", class_="lesson_materials_details_area").find_all("a")
            for file_link in file_links:
                file_url = file_link['href']
                # create the "Files" folder
                files_folder = os.path.join(lesson_folder, 'Files')
                try: 
                    os.mkdir(files_folder) 
                except FileExistsError as error:
                    #print(error)
                    pass
                #print(file_url, end="\n"*2)

                content_type = requests.head(file_url, cookies=jar, headers=headers, allow_redirects=True).headers.get('content-type')
                #print(content_type)

                if 'text/html' in content_type: # it's a url to a web page
                    output_file = files_folder + url_to_filename(file_link.text) + '.txt'

                    # save the url in a txt file
                    with open(output_file, 'w') as f:
                        f.write(file_url)
                else: # it's actually a file
                    output_file = files_folder + file_url.rsplit('/', 1)[1]

                    # download the file if it doesn't exist
                    if os.path.isfile(output_file) == False:
                        r = requests.get(file_url, cookies=jar, headers=headers, allow_redirects=True)
                        open(output_file, 'wb').write(r.content)

            print()
            print('DONE!')
            print()


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

def url_to_filename(url):
    # List of characters that are not allowed in filenames
    invalid_chars = '/\:*?"<>|'
    
    # Replace each invalid character with an underscore
    for char in invalid_chars:
        url = url.replace(char, '_')
    
    # Optionally, you can remove any other characters or patterns as needed
    # For example, to remove trailing periods or spaces:
    url = url.rstrip('. ')
    
    return url

if __name__ == "__main__":
    """ This is executed when run from the command line """
    main()