import csv
import yt_dlp
import os
import re
from concurrent.futures import ThreadPoolExecutor

MAX_THREADS = 5  # Change this value based on how many concurrent downloads you want

script_folder = os.path.dirname(os.path.realpath(__file__))
output_folder = '/home/ziga/share/PaleoPrimal/0 Bodyweight Exercises/Videos/Mike Fitch/Animal Flow/On Demand/'

def download_video(output_folder, video_url, filename):
	yt_opts = {
		#'verbose': True,
		#'cookiefile': cookies_file,
		'restrictfilenames': True,
		'windowsfilenames': True,
		'outtmpl': os.path.join(output_folder, filename + '.%(ext)s'),
		'ignoreerrors': True
	}

	ydl = yt_dlp.YoutubeDL(yt_opts)
	ydl.download(video_url)

def save_description(output_folder, content, filename):
	with open(f"{output_folder}{filename} - description.html", 'w', encoding='utf-8') as file:
		file.write(content)

def save_links(output_folder, class_link, video_url, filename):
	with open(f"{output_folder}{filename} - links.txt", 'w', encoding='utf-8') as file:
		file.writelines([
			"Class link: " + class_link + "\n", 
			"Video link: " + video_url
		])

def main():
	current_series = None
	class_counter = 0

	with open(script_folder + "/scraped_data_edited.csv", 'r') as csv_file:
		reader = csv.DictReader(csv_file, delimiter=';')
		
		with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
			for row in reader:
				class_link = row["Class Link"]
				class_title = row["Class Title"]
				class_description = row["Class Description"]
				video_url = row["HLS URL"]
				parent_folder = row["Parent"]
				series_title = row["Series"]

				if current_series == series_title:
					class_counter += 1
				else:
					current_series = series_title
					class_counter = 1

				series_folder = output_folder + parent_folder + '/' + series_title + '/'
				filename = f"{class_counter:02} - {slugify(class_title)}"

				if not os.path.exists(series_folder):
					os.makedirs(series_folder)
				
				print(f"Queuing download for: {class_title}")
				
				# Create files with description concurrently
				executor.submit(save_description, series_folder, class_description, filename)

				# Create files with links concurrently
				executor.submit(save_links, series_folder, class_link, video_url, filename)

				# Download videos concurrently
				executor.submit(download_video, series_folder, video_url, filename)

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
	main()
