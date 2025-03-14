import urllib.parse
from datetime import datetime, timedelta
import logging
import aiohttp
from bs4 import BeautifulSoup
import re


logger = logging.getLogger("pyhabot_logger")


def get_url_params(url):
    parsed_url = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed_url.query)
    stext = params["stext"][0] if "stext" in params else "-"
    minprice = params["minprice"][0] if "minprice" in params else "0"
    maxprice = params["maxprice"][0] if "maxprice" in params else "∞"
    return stext, minprice, maxprice


def convert_date(expression):
    now = datetime.now()
    if expression.startswith("ma"):
        time_part = expression.split()[1]
        ret_date = datetime.strptime(time_part, "%H:%M").replace(year=now.year, month=now.month, day=now.day)
    elif expression.startswith("tegnap"):
        time_part = expression.split()[1]
        ret_date = datetime.strptime(time_part, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        ) - timedelta(days=1)
    else:
        ret_date = datetime.strptime(expression, "%Y-%m-%d")
    return ret_date.strftime("%Y-%m-%d %H:%M")


def convert_price(price: str):
    price = price.strip()

    if price.lower() == "keresem":
        return None

    if "M" in price:
        match = re.search(r"([0-9,]+)M Ft", price)
        if match:
            return int(float(match.group(1).replace(",", ".")) * 1_000_000)

    match = re.search(r"([0-9 ]+) Ft", price)
    if match:
        return int(match.group(1).replace(" ", ""))

    return None


async def scrape_ads(url):
    ads = []
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            parsed_url = urllib.parse.urlparse(url)
            base_url = parsed_url.scheme + "://" + parsed_url.netloc

            html = BeautifulSoup(await response.text(), "html.parser")
            uad_list = html.find("div", class_="uad-list")

            if uad_list.ul and uad_list.ul.li:
                medias = html.findAll(class_="media")
                for ad in medias:
                    title = ad.find("div", class_="uad-col-title")
                    info = ad.find("div", class_="uad-col-info")
                    price = ad.find("div", class_="uad-price")

                    if title and info:
                        new_entry = {
                            "id": int(ad["data-uadid"]),
                            "title": title.h1.a.text.strip(),
                            "url": title.h1.a["href"],
                            "price": convert_price(price.span.text.strip()),
                            "city": info.find("div", class_="uad-cities").text.strip(),
                            "date": convert_date(info.find("div", class_="uad-time").time.text.strip()),
                            "seller_name": info.find("span", class_="uad-user-text").a.text.strip(),
                            "seller_url": base_url + info.find("span", class_="uad-user-text").a["href"],
                            "seller_rates": info.find("span", class_="uad-user-text").span.text.strip(),
                            "image": ad.a.img["src"],
                        }

                        if all(new_entry.values()):
                            ads.append(new_entry)
                        else:
                            logger.warning(f"Invalid new ad entry: {new_entry}")
                    else:
                        logger.warning(f"Invalid ad entry: {ad}")
    return ads
