#!/usr/bin/python3

from bs4 import BeautifulSoup
from decimal import Decimal
from lxml import etree
from inky import auto
import argparse
import requests
import sys
from PIL import Image, ImageDraw, ImageFont
# from font_intuitive import Intuitive
from font_source_sans_pro import SourceSansProBold

requests.urllib3.disable_warnings()

# ANSI escape sequences
RED_ANSI = "\033[31m"
GREEN_ANSI = "\033[32m"
YELLOW_ANSI = "\033[33m"
RESET_ANSI = "\033[0m"

# Constants
OFICIAL_TARGET_URL = "https://www.bcv.org.ve/"
PARALLEL_TARGET_URL = "https://exchangemonitor.net/venezuela/monitor-dolar"

# Globals
update_screen = True
silent_mode = False


def shorten_date(date_str):
    word_list = date_str.split(" ")
    month_str = word_list[2]
    word_list[2] = month_str[:3] + "."
    # print(word_array)
    return " ".join(word_list)

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
        raise
    except requests.exceptions.HTTPError as err:
        if not silent_mode:        
            print("HTTP request returned an unsuccessful status code (BCV)")
            print(f"Status code: {err.response.status_code}")
        raise
    except requests.exceptions.ConnectionError as conErr:
        if not silent_mode:
            print("A network problem occurred (BCV)")
        raise

    return rounded_amount, date_price

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

def update_screen(date, official_price, average_price):
    inky_display = auto()
    image = Image.new("P", inky_display.resolution)
    draw = ImageDraw.Draw(image)
    # font = ImageFont.truetype(Intuitive, int(22))
    font = ImageFont.truetype(SourceSansProBold, int(21))
    date_font = ImageFont.truetype(SourceSansProBold, int(18))

    draw.text((5,0), date, inky_display.BLACK, font=date_font)
    draw.text((5,20), "OFICIAL", inky_display.BLACK, font=date_font)
    draw.text((120,20), "PARALELO", inky_display.BLACK, font=date_font)
    draw.text((5,40), "Bs.{}".format(official_price), inky_display.BLACK, font=font)
    draw.text((120,40), "Bs.{}".format(average_price), inky_display.BLACK, font=font)

    inky_display.set_image(image)
    inky_display.show()
    return

def main() -> int:
    global silent_mode
    global update_screen

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
        official_price, date_price = get_price_from_bcv()
        average_price = get_parallel_price()

        if not silent_mode:
            print(date_price)
            print("Oficial (BCV):\tBs. {}".format(official_price))
            print("Paralelo:\tBs. {}".format(average_price))

        # Update Screen
        if update_screen:
            update_screen(date_price, official_price, average_price)

        # Play Sound (?)

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


