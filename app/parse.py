import csv
import logging
import sys
from dataclasses import dataclass, fields, astuple
from datetime import datetime
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup, Tag

BASE_URL = "https://quotes.toscrape.com/"


@dataclass
class Quote:
    text: str
    author: str
    tags: list[str]


QUOTE_FIELDS = [field.name for field in fields(Quote)]


logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)8s]: %(message)s",
    handlers=[
        logging.FileHandler("parser.log"),
        logging.StreamHandler(sys.stdout),
    ]
)


def parse_single_quote(quote_soup: Tag) -> Quote:
    return Quote(
        text=quote_soup.select_one(".text").text,
        author=quote_soup.select_one(".author").text,
        tags=quote_soup.select_one(".tags").text.split()[1:]
    )


def get_single_page_quotes(page_soup: Tag) -> [Quote]:
    quotes = page_soup.select(".quote")
    return [parse_single_quote(quote_soup) for quote_soup in quotes]


def get_all_pages_quotes() -> [Quote]:
    # logging
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"{time} - Start parsing quotes")

    page_text = requests.get(BASE_URL).content
    first_page_soup = BeautifulSoup(page_text, "html.parser")

    all_quotes = get_single_page_quotes(first_page_soup)

    # next button searching
    next_element = first_page_soup.select_one(".next")
    next_page_number = next_element.a["href"].split("/")[-2]
    while next_element is not None:
        try:
            # logging
            time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logging.info(f"{time} - Start parsing page #{next_page_number}")

            next_page_url = urljoin(BASE_URL, f"/page/{next_page_number}/")
            next_page_text = requests.get(next_page_url).content
            next_page_soup = BeautifulSoup(next_page_text, "html.parser")

            # Adding quotes from a new page
            all_quotes.extend(get_single_page_quotes(next_page_soup))

            # next button searching
            next_element = next_page_soup.select_one(".next")
            if next_element is None:
                raise AttributeError("Element '.next' not found")
            next_page_number = next_element.a["href"].split("/")[-2]
        except AttributeError as e:
            time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logging.info(f"{time} - 'Next' button not found")
            break
    return all_quotes


def write_quotes_to_csv(output_csv_path: str) -> None:
    quotes = get_all_pages_quotes()
    with open(output_csv_path, "w", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(QUOTE_FIELDS)
        writer.writerows([astuple(quote) for quote in quotes])


def main(output_csv_path: str) -> None:
    write_quotes_to_csv(output_csv_path)


if __name__ == "__main__":
    main("quotes.csv")
