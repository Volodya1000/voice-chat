import requests
import re
from langchain.tools import tool


BASE_URL = "https://openlibrary.org/search.json"


def normalize_spacings(text: str) -> str:
    text = re.sub(r"[ ]{2,}", " ", text.replace("\t", "")).replace("\r\n", "\n").replace("\n ", "\n").strip()
    text = re.sub(r"(\n){2,}", "\n", text)
    return text


# =======================
# GetAvailableBookCountByAuthor
# =======================
@tool("GetAvailableBookCountByAuthor")
def get_available_book_count_by_author(author: str) -> int:
    """
    Retrieves the count of books available by a specified author.
    """
    resp = requests.get(BASE_URL, params={"author": author})
    resp.raise_for_status()

    data = resp.json()
    return int(data.get("num_found", 0))


# =======================
# GetBookInfo
# =======================
@tool("GetBookInfo")
def get_book_info(title: str) -> str:
    """
    Retrieves detailed information about a book by its title.
    """
    resp = requests.get(BASE_URL, params={"title": title})
    resp.raise_for_status()

    data = resp.json()
    docs = data.get("docs", [])

    if not docs:
        return f"No data found for title: {title}"

    doc = docs[0]

    # extract fields safely
    first_publish_year = str(doc.get("first_publish_year", "unknown"))
    number_of_pages_median = str(doc.get("number_of_pages_median", "unknown"))
    ebook_access = doc.get("ebook_access", "unknown")
    isbn = normalize_spacings(str(doc.get("isbn", "unknown")))
    formats = normalize_spacings(str(doc.get("format", "unknown")))
    publisher = doc.get("publisher", ["unknown"])[0]
    authors = normalize_spacings(str(doc.get("author_name", "unknown")))
    book_title = doc.get("title", title)

    return (
        f"Title: {book_title}\n"
        f"First publish year: {first_publish_year}\n"
        f"Authors: {authors}\n"
        f"Number of pages median: {number_of_pages_median}\n"
        f"Formats: {formats}\n"
        f"E-book access: {ebook_access}\n"
        f"ISBN: {isbn}\n"
        f"Publisher: {publisher}"
    )


# =======================
# GetLastBookFromAuthor
# =======================
@tool("GetLastBookFromAuthor")
def get_last_book_from_author(author: str) -> str:
    """
    Retrieves info about the most recent book from a given author.
    """
    resp = requests.get(BASE_URL, params={"author": author, "sort": "new"})
    resp.raise_for_status()

    data = resp.json()
    docs = data.get("docs", [])

    if not docs:
        return f"No books found for author: {author}"

    doc = docs[0]

    title = doc.get("title", "unknown")
    publish_years = doc.get("publish_year", [])
    publish_year = str(publish_years[0]) if publish_years else "unknown"

    return f"{title}, publish year: {publish_year}"


# =======================
# GetBookAuthor
# =======================
@tool("GetBookAuthor")
def get_book_author(book: str) -> str:
    """
    Retrieves the author(s) of the specified book.
    """
    resp = requests.get(BASE_URL, params={"q": book})
    resp.raise_for_status()

    data = resp.json()
    docs = data.get("docs", [])

    if not docs:
        return "unknown"

    authors = docs[0].get("author_name", [])

    if authors:
        return authors[0]

    return "unknown"
