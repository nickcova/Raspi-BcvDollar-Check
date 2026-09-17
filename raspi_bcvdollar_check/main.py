#!/usr/bin/python3

from bs4 import BeautifulSoup
from datetime import datetime
from decimal import Decimal
from font_source_sans_pro import SourceSansProBold
from inky import auto
from lxml import etree
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import argparse
import os
import sqlite3
import requests
import subprocess
import sys

requests.urllib3.disable_warnings()

# ANSI escape sequences
RED_ANSI = "\033[31m"
GREEN_ANSI = "\033[32m"
YELLOW_ANSI = "\033[33m"
RESET_ANSI = "\033[0m"

# Constants
SCRIPT_DIR_PATH = os.path.dirname(os.path.abspath(__file__))
OFICIAL_TARGET_URL = "https://www.bcv.org.ve/" # TODO Delete this variable
PARALLEL_TARGET_URL = "https://exchangemonitor.net/venezuela/monitor-dolar" # TODO Delete this variable
DOLAR_API_URL = "https://ve.dolarapi.com/v1"
DOLLARS_ENDPOINT = "/dolares"
EUROS_ENDPOINT = "/euros"
DB_FILE = Path("/home/nick/Data/exchange_rates.db")

# Globals
update_screen = True
silent_mode = False
mute = False
dry_run = False

# deprecated: "Use format_date() instead"
def shorten_date(date_str):
    word_list = date_str.split(" ")
    month_str = word_list[2]
    word_list[2] = month_str[:3] + "."
    # print(word_array)
    return " ".join(word_list)


def format_date(date_str: str):
    try:
        dt = datetime.fromisoformat(date_str)
        formatted = dt.strftime("%Y-%m-%d %I:%M %p")
        return formatted
    except ValueError as e:
        if not silent_mode:
            print("Error parsing date:", e)
        return None


# deprecated: "Use get_dolarapi_json() instead"
def get_price_from_bcv():
    rounded_amount = -1
    date_price = ""

    try:
        response = requests.get(OFICIAL_TARGET_URL, timeout=10, verify=False)

        if response.status_code != requests.codes.ok:
            response.raise_for_status()

        soup = BeautifulSoup(response.text, features="html.parser")
        dom = etree.HTML(str(soup))
        amount_as_str = dom.xpath('//*[@id="dolar"]/div/div/div[2]/strong')[0].text.strip()
        amount_as_str = amount_as_str.replace(",", ".")
        amount_as_decimal = Decimal(amount_as_str)
        rounded_amount = round(amount_as_decimal,2)

        date_price = dom.xpath('/html/body/div[4]/div/div[2]/div/div[1]/div[1]/section[1]/div/div[2]/div/div[8]/span')[0].text.strip()
        date_price = date_price.replace("  ", " ")
        date_price = shorten_date(date_price)
        # print(rounded_amount)
        # print(date_price)

    except requests.exceptions.Timeout:
        if not silent_mode:
            print("A Timeout occurred (BCV)")
        if update_screen:
            show_error_screen("A Timeout occurred (BCV)")
        raise
    except requests.exceptions.HTTPError as err:
        if not silent_mode:
            print("HTTP request returned an unsuccessful status code (BCV)")
            print(f"Status code: {err.response.status_code}")
        if update_screen:
            show_error_screen("HTTP Error", f"Status code: {err.response.status_code}")
        raise
    except requests.exceptions.ConnectionError as conErr:
        if not silent_mode:
            print("A network problem occurred (BCV)")
        if update_screen:
            show_error_screen("A network problem", "occurred (BCV)")
        raise

    return rounded_amount, date_price


# deprecated: "Use get_dolarapi_json() instead"
def get_parallel_price():
    rounded_amount = -1;

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Referer": "https://www.google.com/",
        };

        response = requests.get(PARALLEL_TARGET_URL, headers=headers, timeout=10, verify=False)

        if response.status_code != requests.codes.ok:
            response.raise_for_status()

        soup = BeautifulSoup(response.text, features="html.parser")
        dom = etree.HTML(str(soup))
        amount_as_str = dom.xpath('/html/body/div[2]/div/main/section/div[1]/table/tbody/tr[3]/td[2]')[0].text.strip()
        amount_as_str = amount_as_str.split(" ")[1]
        amount_as_str = amount_as_str.replace(",", ".")
        amount_as_decimal = Decimal(amount_as_str)
        rounded_amount = round(amount_as_decimal,2)

    except requests.exceptions.Timeout:
        if not silent_mode:
            print("A Timeout occurred (Monitor Dólar VZLA)")
        raise
    except requests.exceptions.HTTPError as err:
        if not silent_mode:
            print("HTTP request returned an unsuccessful status code (Monitor Dólar VZLA)")
            print(f"Status code: {err.response.status_code}")
            print(f"Error message: {err.response.text}")
        raise
    except requests.exceptions.ConnectionError as conErr:
        if not silent_mode:
            print("A network problem occurred (Monitor Dólar VZLA)")
        raise

    return rounded_amount


def get_dolarapi_json(endpoint):
    try:
        response = requests.get(f"{DOLAR_API_URL}{endpoint}", timeout=10, verify=False)

        if response.status_code != requests.codes.ok:
            response.raise_for_status()

        try:
            data = response.json()
        except ValueError:
            if not silent_mode:
                print(f"{RED_ANSI}Error:{RESET_ANSI} Response is not a valid JSON.")
            if update_screen:
                show_error_screen("Response is not", "a valid JSON")
            return None
        return data

    except requests.exceptions.Timeout:
        if not silent_mode:
            print("A Timeout occurred (Dólar API)")
        if update_screen:
            show_error_screen("A Timeout occurred (Dólar API)")
        raise
    except requests.exceptions.HTTPError as err:
        if not silent_mode:
            print("HTTP request returned an unsuccessful status code (Dólar API)")
            print(f"Status code: {err.response.status_code}")
        if update_screen:
            show_error_screen("HTTP Error", f"Status code: {err.response.status_code}")
        raise
    except requests.exceptions.ConnectionError as conErr:
        if not silent_mode:
            print("A network problem occurred (Dólar API)")
        if update_screen:
            show_error_screen("A network problem", "occurred (Dólar API)")
        raise
    except requests.exceptions.RequestException as e:
        if not silent_mode:
            print(f"Request failed: {e}")
        if update_screen:
            show_error_screen("Http Error", f"{e}")
        raise
    return


def update_screen(date, official_rate, parallel_rate, euro_rate, official_rate_delta, parallel_rate_delta, euro_rate_delta):
    inky_display = auto()
    display_width = inky_display.resolution[0]
    display_height = inky_display.resolution[1]
    canvas = Image.new("P", inky_display.resolution)
    draw = ImageDraw.Draw(canvas)

    # Set fonts
    font = ImageFont.truetype(SourceSansProBold, int(24))
    date_font = ImageFont.truetype(SourceSansProBold, int(18))

    # Fetch images
    arrow_up_img_path = os.path.join(SCRIPT_DIR_PATH, "img/arrow-up.png")
    arrow_up_img = Image.open(arrow_up_img_path)
    arrow_up_img = arrow_up_img.resize((16, 16), Image.Resampling.LANCZOS)

    arrow_down_img_path = os.path.join(SCRIPT_DIR_PATH, "img/arrow-down.png")
    arrow_down_img = Image.open(arrow_down_img_path)
    arrow_down_img = arrow_down_img.resize((16, 16), Image.Resampling.LANCZOS)

    equal_img_path = os.path.join(SCRIPT_DIR_PATH, "img/equal.png")
    equal_img = Image.open(equal_img_path)
    equal_img = equal_img.resize((16, 16), Image.Resampling.LANCZOS)

    # Set texts
    official_txt = "DÓLAR"
    official_rate_txt = "Bs.{}".format(official_rate)
    official_rate_delta_txt = "+99.99"
    parallel_txt = "PROM$"
    parallel_rate_txt = "Bs.{}".format(parallel_rate)
    parallel_rate_delta_txt = "-99.99"
    euro_txt = "EURO"
    euro_rate_txt = "Bs.{}".format(euro_rate)

    # Draw texts
    draw.text((5, 0), date, inky_display.BLACK, font=date_font)

    draw.text((5, 26), official_txt, inky_display.BLACK, font=date_font)
    draw.text((93, 21), official_rate_txt, inky_display.BLACK, font=font)

    draw.text((5, 48), parallel_txt, inky_display.BLACK, font=date_font)
    draw.text((93, 43), parallel_rate_txt, inky_display.BLACK, font=font)

    draw.text((5, 70), euro_txt, inky_display.BLACK, font=date_font)
    draw.text((93, 65), euro_rate_txt, inky_display.BLACK, font=font)

    # Draw icons
    # Dollar rate delta arrow
    dollar_icon = arrow_up_img if official_rate_delta > 0.0 else arrow_down_img if official_rate_delta < 0.0 else equal_img
    draw = ImageDraw.Draw(dollar_icon)
    canvas.paste(dollar_icon, (70, 28))

    # Parallel rate delta arrow
    parallel_icon = arrow_up_img if parallel_rate_delta > 0.0 else arrow_down_img if parallel_rate_delta < 0.0 else equal_img
    draw = ImageDraw.Draw(parallel_icon)
    canvas.paste(parallel_icon, (70, 52))

    # Euro
    euro_icon = arrow_up_img if euro_rate_delta > 0.0 else arrow_down_img if euro_rate_delta < 0.0 else equal_img
    draw = ImageDraw.Draw(euro_icon)
    canvas.paste(euro_icon, (70, 74))

    inky_display.set_image(canvas)
    inky_display.show()
    return


def init_db():
    """Checks if the database file exists. Creates it and the schema if missing."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exchange_rates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            official_rate REAL NOT NULL,
            parallel_rate REAL NOT NULL,
            euro_rate REAL NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    return


def save_rate(official_rate, parallel_rate, euro_rate, date_rate):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO exchange_rates (official_rate, parallel_rate, euro_rate, timestamp) VALUES (?, ?, ?, ?)",
        (official_rate, parallel_rate, euro_rate, date_rate)
    )
    conn.commit()
    conn.close()
    return


def exchange_rate_fluctuation(official_rate):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM exchange_rates ORDER BY id DESC LIMIT 2")
    rows = cursor.fetchall()

    dollar_delta = 0.0
    parallel_delta = 0.0
    euro_delta = 0.0

    if len(rows) > 1:
        # Calculate deltas
        dollar_delta = round(rows[0][1] - rows[1][1], 2)
        parallel_delta = round(rows[0][2] - rows[1][2], 2)
        euro_delta = round(rows[0][3] - rows[1][3], 2)

    conn.close()
    return dollar_delta, parallel_delta, euro_delta


def show_error_screen(message, message2="", message3=""):
    inky_display = auto()
    WIDTH, HEIGHT = inky_display.resolution

    message_font = ImageFont.truetype(SourceSansProBold, int(18))
    canvas = Image.new ("P", (WIDTH, HEIGHT))

    image = Image.open(os.path.join(PATH, "img/exception_01.png")).resize((WIDTH, HEIGHT)).convert("P")
    canvas.paste(image, (0, 0))

    draw = ImageDraw.Draw(canvas)

    # Draw date first
    date_font = ImageFont.truetype(SourceSansProBold, int(13))
    now_str = datetime.now().strftime("%Y.%m.%d %I:%M:%S %p")
    draw.text((37, 26), now_str, inky_display.RED, font=date_font)

    # Draw Messages
    draw.text((5, 40), message, inky_display.BLACK, font=message_font)

    if message2 != "":
        draw.text((5, 60), message2, inky_display.BLACK, font=message_font)

    if message3 != "":
        draw.text((5, 80), message3, inky_display.BLACK, font=message_font)

    inky_display.set_image(canvas)
    inky_display.show()
    return


def main() -> int:
    global silent_mode
    global update_screen
    global mute
    global dry_run

    print(GREEN_ANSI + "RasPi BCV Dollar Check" + RESET_ANSI)

    # For testing stuff, will delete later
    # show_error_screen("A Timeout occurred (BCV)")
    # return 0

    parser = argparse.ArgumentParser(description="RasPi BCV Dollar Check - Looks up and shows current dollar exchange rates")
    parser.add_argument("-c", "--console", action="store_true", help="Console mode. Does not update e-ink screen.")
    parser.add_argument("-s", "--silent", action="store_true", help="Silent mode. Does not print messages to standard output.")
    parser.add_argument("-m", "--mute", action="store_true", help="Mute sounds. Does not emit sounds through the SpeakerPhat.")
    parser.add_argument("-n", "--dry-run", action="store_true", help="Run the script without saving changes to the database.")

    args = parser.parse_args()

    if args.console:
        update_screen = False
        print(YELLOW_ANSI + "Running in console mode" + RESET_ANSI)

    if args.silent:
        silent_mode = True
        print(YELLOW_ANSI + "Running in silent mode" + RESET_ANSI)

    if args.mute:
        mute = True
        print(YELLOW_ANSI + "Running in mute mode" + RESET_ANSI)

    if args.dry_run:
        dry_run = True
        print(YELLOW_ANSI + "Running in dry run mode" + RESET_ANSI)

    try:
        # Fetch exchange rates
        dollars_data_json = get_dolarapi_json(DOLLARS_ENDPOINT)
        if dollars_data_json is not None:
            official_rate = round(dollars_data_json[0].get("promedio"), 2)
            parallel_rate = round(dollars_data_json[1].get("promedio"), 2)
            date_rate = format_date(dollars_data_json[0].get("fechaActualizacion"))

        euros_data_json = get_dolarapi_json(EUROS_ENDPOINT)
        if euros_data_json is not None:
            official_euro_rate = round(euros_data_json[0].get("promedio"), 2)

        # Update DB
        if not dry_run:
            init_db()
            save_rate(official_rate, parallel_rate, official_euro_rate, date_rate)
            # Calculate fluctuation
            dollar_delta, parallel_delta, euro_delta = exchange_rate_fluctuation(official_rate)

        if not silent_mode:
            dollar_delta_txt = "+{}".format(dollar_delta) if dollar_delta > 0 else str(dollar_delta)
            parallel_delta_txt = "+{}".format(parallel_delta) if parallel_delta > 0 else str(parallel_delta)
            euro_delta_txt = "+{}".format(euro_delta) if euro_delta > 0 else str(euro_delta)

            print(date_rate)
            print("Dólar BCV:\tBs. {} ({})".format(official_rate, dollar_delta_txt))
            print("Dólar promedio:\tBs. {} ({})".format(parallel_rate, parallel_delta_txt))
            print("Euro BCV:\tBs. {} ({})".format(official_euro_rate, euro_delta_txt))

        # Update Screen
        if update_screen:
            update_screen(date_rate, official_rate, parallel_rate, official_euro_rate, dollar_delta, parallel_delta, euro_delta)

        # Play Sound
        if not mute:
            mp3_path = os.path.join(SCRIPT_DIR_PATH, "sound/notification.mp3")
            audio_subprocess = subprocess.Popen(["mpg123", "-q", mp3_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    except requests.exceptions.Timeout:
        # A Timeout occurred
        return 1
    except requests.exceptions.HTTPError:
        # HTTP request returned an unsuccessful status code
        return 2
    except requests.exceptions.ConnectionError:
        # A network problem occurred
        return 3

    return 0

if __name__ == '__main__':
    sys.exit(main())


