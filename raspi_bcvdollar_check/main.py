#!/usr/bin/python3

# from font_intuitive import Intuitive
from bs4 import BeautifulSoup
from datetime import datetime
from decimal import Decimal
from font_source_sans_pro import SourceSansProBold
from inky import auto
from lxml import etree
from PIL import Image, ImageDraw, ImageFont
import argparse
import os
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
OFICIAL_TARGET_URL = "https://www.bcv.org.ve/"
PARALLEL_TARGET_URL = "https://exchangemonitor.net/venezuela/monitor-dolar"
DOLAR_API_URL = "https://ve.dolarapi.com/v1"
DOLLARS_ENDPOINT = "/dolares"

# Globals
update_screen = True
silent_mode = False

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
 
    # print(rounded_amount)
    return rounded_amount


def get_dolarapi_json():
    try:
        response = requests.get(f"{DOLAR_API_URL}{DOLLARS_ENDPOINT}", timeout=10, verify=False)

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


def update_screen(date, official_price, average_price):
    inky_display = auto()
    image = Image.new("P", inky_display.resolution)
    draw = ImageDraw.Draw(image)
    # font = ImageFont.truetype(Intuitive, int(22))
    font = ImageFont.truetype(SourceSansProBold, int(21))
    date_font = ImageFont.truetype(SourceSansProBold, int(18))

    draw.text((5,0), date, inky_display.BLACK, font=date_font)
    draw.text((5,20), "OFICIAL", inky_display.BLACK, font=date_font)
    draw.text((110,20), "Bs.{}".format(official_price), inky_display.BLACK, font=font)
    draw.text((5,40), "PARALELO", inky_display.BLACK, font=date_font)
    draw.text((110,40), "Bs.{}".format(average_price), inky_display.BLACK, font=font)

    inky_display.set_image(image)
    inky_display.show()
    return


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

    # For testing stuff, will delete later
    # show_error_screen("A Timeout occurred (BCV)")
    # return 0

    parser = argparse.ArgumentParser(description="RasPi BCV Dollar Check - Looks up and shows current dollar exchange rates")
    parser.add_argument("-c", "--console", action="store_true", help="Console mode. Does not update e-ink screen.")
    parser.add_argument("-s", "--silent", action="store_true", help="Silent mode. Does not print messages to standard output.")

    args = parser.parse_args()

    if args.console:
        update_screen = False
        print(YELLOW_ANSI + "Running in console mode\n" + RESET_ANSI)

    if args.silent:
        silent_mode = True
        print(YELLOW_ANSI + "Running in silent mode\n" + RESET_ANSI)

    try:
        # official_price, date_price = get_price_from_bcv()
        # average_price = get_parallel_price()
        data_json = get_dolarapi_json()
        if data_json is not None:
            official_price = round(data_json[0].get("promedio"), 2)
            average_price = round(data_json[1].get("promedio"), 2)
            date_price = format_date(data_json[0].get("fechaActualizacion"))
            

        if not silent_mode:
            print(date_price)
            print("Oficial (BCV):\tBs. {}".format(official_price))
            print("Paralelo (promedio):\tBs. {}".format(average_price))

        # Update Screen
        if update_screen:
            update_screen(date_price, official_price, average_price)

        # Play Sound
        mp3_path = os.path.join(SCRIPT_DIR_PATH, "sound/notification.mp3")
        audio_subprocess = subprocess.Popen(["mpg123", "-q", mp3_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Update DB (?)

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


