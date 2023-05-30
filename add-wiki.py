##########################################################################################################
# This Python3 script guides you to quickly generate a JSON object for adding a wiki to Indie Wiki Buddy.
# It will also automatically download the destination wiki's favicon,
# convert it to PNG, resize to 16px, and add to the /favicons directory.

# When running, this script should be in the Indie Wiki Buddy project root folder.
##########################################################################################################

import os
import time
import json
import re
import requests
from urllib.request import Request, urlopen
from PIL import Image
from bs4 import BeautifulSoup

# Get data from user input:
lang = input("Enter language as two letter code (leave blank for 'en'): ") or "en"
id = input("Enter entry ID (series name, one word, no dashes e.g. animalcrossing): ")
id = id.lower()
origin_name = input("Enter origin wiki name (leave blank for '<id.capitalize()> Fandom Wiki'): " ) or id.capitalize() + " Fandom Wiki"
origin_link = input("Enter origin wiki link (leave blank for '<id>.fandom.com'): ") or id + ".fandom.com"
origin_content_path = input("Enter origin content path (leave blank for '/wiki/'): ") or "/wiki/"
destination_name = input("Enter destination wiki name: ")
destination_link = input("Enter destination wiki link: ")
destination_content_path = input("Enter destination wiki content path: ")
destination_platform = input("Enter destination wiki platform (leave blank for 'mediawiki'): ") or "mediawiki"

# Output JSON:
data = {
  "id": lang + "-" + id,
  "origins_label": origin_name,
  "origins": [
    {
      "origin": origin_name,
      "origin_base_url": origin_link,
      "origin_content_path": origin_content_path
    }
  ],
  "destination": destination_name,
  "destination_base_url": destination_link,
  "destination_content_path": destination_content_path,
  "destination_platform": destination_platform,
  "destination_icon": destination_name.lower() + ".png"
}
print("==============================")
print(json.dumps(data, indent=2))
print("==============================")


# Pull favicon from destination wiki:
page = urlopen(Request(url="https://" + destination_link, headers={'User-Agent': 'Mozilla/5.0'}))
soup = BeautifulSoup(page, "html.parser")
icon_link = soup.find("link", rel="shortcut icon")
icon = urlopen(Request(url=requests.compat.urljoin("https://" + destination_link + "/favicon.ico", icon_link['href']), headers={'User-Agent': 'Mozilla/5.0'}))
icon_filename =  os.path.join("favicons\\" + lang + "\\" + re.sub('[^A-Za-z0-9]+', '', destination_name).lower() + icon_link['href'][-4:])
with open(icon_filename, "wb+") as f:
  f.write(icon.read())

# Convert favicon to PNG, resize to 16px, save, and delete the original file:
time.sleep(1)
Image.open(icon_filename).save(icon_filename[0:icon_filename.find('.')] + ".png", sizes=(16, 16))
os.remove(icon_filename)
