import csv
import logging
import re
import sys
from dataclasses import dataclass, fields, astuple
from datetime import datetime
from urllib.parse import urljoin
import requests
import unicodedata
from bs4 import BeautifulSoup, Tag

BASE_URL = "https://quotes.toscrape.com/"


@dataclass
class Quote:
    text: str
    author: str
    tags: list[str]


@dataclass
class Author:
    name: str
    biography: str


QUOTE_FIELDS = [field.name for field in fields(Quote)]
AUTHOR_FIELDS = [field.name for field in fields(Author)]
authors_list = []


logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)8s]: %(message)s",
    handlers=[
        logging.FileHandler("parser.log"),
        logging.StreamHandler(sys.stdout),
    ]
)


def parse_single_quote(quote_soup: Tag) -> Quote:
    author_name = quote_soup.select_one(".author").text
    if author_name not in authors_list:
        authors_list.append(author_name)
    return Quote(
        text=quote_soup.select_one(".text").text,
        author=author_name,
        tags=quote_soup.select_one(".tags").text.split()[1:]
    )


def get_single_author(name: str, biography: str) -> Author:
    return Author(
        name=name,
        biography=biography,
    )


def get_single_page_quotes(page_soup: Tag) -> [Quote]:
    quotes = page_soup.select(".quote")
    return [parse_single_quote(quote_soup) for quote_soup in quotes]


def get_all_pages_quotes() -> [Quote]:
    # logging
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"{time} - Start parsing quotes")

    page_text = requests.get(BASE_URL).content
    page_soup = BeautifulSoup(page_text, "html.parser")

    all_quotes = get_single_page_quotes(page_soup)

    # next button searching
    next_element = page_soup.select_one(".next")
    while next_element is not None:
        # Checking the existence of an element and the href attribute
        if next_element and next_element.a and "href" in next_element.a.attrs:
            next_href = next_element.a["href"]
            # Using a Regular Expression to Extract a Number from a URL
            match = re.search(r"/page/(\d+)/", next_href)
            if match:
                next_page_number = match.group(1)

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

    return all_quotes


def write_quotes_to_csv(output_csv_path: str) -> None:
    quotes = get_all_pages_quotes()
    with open(output_csv_path, "w", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(QUOTE_FIELDS)
        writer.writerows([astuple(quote) for quote in quotes])


def format_name(input_name: str) -> str:
    # Removing diacritics
    normalized_name = unicodedata.normalize("NFD", input_name)
    name_without_accents = "".join(
        char for char in normalized_name if unicodedata.category(char) != "Mn"
    )
    # Replace spaces and dots with hyphens
    formatted_name = re.sub(
        r"[.\s]+", "-",
        name_without_accents
    ).replace("'", "").rstrip("-")
    return formatted_name


def get_all_authors_biography(authors: list) -> [Author]:
    returning_authors_list = []
    for name in authors:
        refactored_name = format_name(name)
        author_url = urljoin(BASE_URL, f"/author/{refactored_name}/")
        page_text = requests.get(author_url).content
        first_page_soup = BeautifulSoup(page_text, "html.parser")
        biography = first_page_soup.select_one(
            ".author-description"
        ).text.strip()
        returning_authors_list.append(get_single_author(name, biography))

    return returning_authors_list


def write_authors_to_csv(output_csv_path: str) -> None:
    authors = get_all_authors_biography(authors_list)
    with open(output_csv_path, "w", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(AUTHOR_FIELDS)
        writer.writerows([astuple(author) for author in authors])


def main(output_csv_path: str) -> None:
    write_quotes_to_csv(output_csv_path)


if __name__ == "__main__":
    main("quotes.csv")
    write_authors_to_csv("authors.csv")
