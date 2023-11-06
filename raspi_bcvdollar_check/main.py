#!/usr/bin/python3

from bs4 import BeautifulSoup
from decimal import Decimal
from lxml import etree
import requests
import sys

# Constants
TARGET_URL = "https://www.bcv.org.ve/"

def get_price_from_website():
    rounded_amount = -1
    date_price = ""

    try:
        response = requests.get(TARGET_URL, timeout=10)

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
        # print(rounded_amount)
        # print(date_price)

    except requests.exceptions.Timeout:
        print("A Timeout occurred")
        raise
    except requests.exceptions.HTTPError:
        print("HTTP request returned an unsuccessful status code")
        raise
    except requests.exceptions.ConnectionError:
        print("A network problem occurred")
        raise

    return rounded_amount, date_price

def main() -> int:
    try:
        usd_price, date_price = get_price_from_website()

        print(usd_price)
        print(date_price)

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