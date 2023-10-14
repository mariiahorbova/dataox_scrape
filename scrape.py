import os
import re
import time

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from decouple import config

from utils.db_scripts import (
    connect_to_db,
    close_db,
    insert_into_db,
    create_table
)
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler({'apscheduler.timezone': 'Europe/Kiev'})

START_URL = 'https://auto.ria.com/uk/car/used/'
BACKUP_PATH = 'dumps'
TIMESTAMP = time.strftime('%Y-%m-%d-%H-%M-%S')
BACKUP_FILE = config("POSTGRES_DB") + '_' + TIMESTAMP + '.sql'

db_params = {
    'dbname': config("POSTGRES_DB"),
    'user': config("POSTGRES_USER"),
    'password': config("POSTGRES_PASSWORD"),
    'host': config("POSTGRES_HOST"),
    'port': config("POSTGRES_PORT"),
}

conn = connect_to_db(db_params)
cursor = conn.cursor()


def find_hash(tag):
    return tag.name == "script" and tag.has_attr("data-hash")


def scrape_car_listing(url):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        sold_check = soup.select("div[class='gallery-order sold-out carousel']")
        if sold_check:
            return
        title = soup.find('h1', class_='head').text.strip()
        price_usd = soup.select("div[class='price_value']")[0].select("strong")[0].text[:-1].replace(' ', '')
        odometer = int(soup.select("div[class='base-information bold']")[0].select("span")[0].text) * 1000
        username_info = soup.find('div', class_='seller_info_name')
        if username_info:
            username = username_info.text.strip()
        else:
            username = soup.find("h4", class_="seller_info_name").findChildren()[0].text
        data_hash = soup.find(find_hash)["data-hash"]
        id = re.search(r"_[0-9]*.html", url).group(0)[1:-5]
        phone_url = f"https://auto.ria.com/users/phones/{id}?hash={data_hash}&expires=2592000"
        phone_response = requests.get(phone_url)
        phone_number = int(phone_response.json()["phones"][0]["phoneFormatted"].replace("(", "").replace(")", "").replace(" ", ""))
        image_element = soup.select("div[class='photo-620x465']")[0]
        image_url = image_element.findChildren("source", recursive=True)[0]['srcset']
        images_count = soup.select("div[class='count-photo left']")[0].select("span[class='mhide']")[0].text[2:]
        car_info = soup.find("div", class_="t-check")
        if car_info.select("span[class='state-num ua']"):
            number_element = car_info.select("span[class='state-num ua']")[0].text
            car_number = number_element.split("Ми")[0].strip()
        else:
            car_number = "Інформація у цифрових реєстрах МВС відсутня."
        codes_container = car_info.findChildren(recursive=False)
        for child in codes_container:
            code_label = child.attrs["class"][0]
            if code_label == "vin-code":
                car_vin = child.contents[0]
            elif code_label == "label-vin":
                car_vin = child.contents[1]

        datetime_found = datetime.now()

        data = [
            url,
            title,
            price_usd,
            odometer,
            username,
            phone_number,
            image_url,
            images_count,
            car_number,
            car_vin,
            datetime_found
        ]
        insert_into_db(conn, cursor, "car_data", data)


def scrape_auto_ria_listings(url):
    create_table(conn, cursor, "car_data")

    page = 1
    while True:
        page_url = f"{url}?page={page}"
        response = requests.get(page_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            listings = soup.find_all('div', class_='content-bar')
            for listing in listings:
                listing_url = listing.find('a', class_='address')['href']
                scrape_car_listing(listing_url)
            next_button = soup.find('a', class_='page-link')
            if next_button is None:
                break
            page += 1
        else:
            break
    close_db(conn)


def dump_of_db():
    BACKUP_CMD = f"PGPASSWORD='{3}' pg_dump -h {0} -U {1} -d {2} > {4}".format(
        config("POSTGRES_HOST"),
        config("POSTGRES_USER"),
        config("POSTGRES_DB"),
        config("POSTGRES_PASSWORD"),
        os.path.join(BACKUP_PATH, BACKUP_FILE)
    )
    os.system(BACKUP_CMD)


if __name__ == "__main__":
    scheduler.add_job(scrape_auto_ria_listings,
                      'cron',
                      args=[START_URL],
                      hour=12,
                      minute=0,
                      misfire_grace_time=None,
                      max_instances=1000)

    scheduler.add_job(dump_of_db,
                      'cron',
                      hour=0,
                      minute=0,
                      misfire_grace_time=None,
                      max_instances=1000)

    scheduler.start()

    while True:
        time.sleep(1)
        print("Waiting to start scraping...")
