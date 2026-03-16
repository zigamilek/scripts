from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

url = "https://prvi.rtvslo.si/podkast/lahko-noc-otroci/54/175160099"
options = Options()
# Disable headless to allow full JS execution for debugging
# options.add_argument("--headless")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get(url)
# DEBUG: print fetched HTML snippet and check for audio icon
page_html = driver.page_source
print("\n=== Debug: Fetched Prvi page HTML (first 1000 chars) ===")
print(page_html[:1000])
if 'icon-audio' in page_html:
    print("Debug: 'icon-audio' found in HTML.")
else:
    print("Debug: 'icon-audio' NOT found in HTML.")
print("=== End debug snippet ===\n")
# On Prvi page, click the play button to inject the audio player
play_btn = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, 'span.icon-audio'))
)
driver.execute_script("arguments[0].scrollIntoView({behavior:'smooth', block:'center'});", play_btn)
play_btn.click()
# Wait up to 20s for the audio tag to appear in the DOM
audio = WebDriverWait(driver, 20).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, 'audio.audio-player-html5'))
)
print("MP3 URL:", audio.get_attribute("src"))

driver.quit()