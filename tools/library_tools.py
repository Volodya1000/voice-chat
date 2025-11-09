from langchain.tools import tool
import requests
import re

BASE_URL = "https://openlibrary.org/search.json"

def normalize_spacings(text: str) -> str:
    text = re.sub(r"[ ]{2,}", " ", text.replace("\t", "")).replace("\r\n", "\n").replace("\n ", "\n").strip()
    text = re.sub(r"(\n){2,}", "\n", text)
    return text


@tool(
    description="Returns the number of books available by a specific author. Use only this tool to get the count of books by an author."
)
def get_available_book_count_by_author(author: str) -> int:
    resp = requests.get(BASE_URL, params={"author": author})
    resp.raise_for_status()
    data = resp.json()
    return int(data.get("num_found", 0))

@tool(
    description="Retrieves detailed information about a book by its title, including authors, publisher, publish year, pages, formats, ISBN, and e-book availability. Use only this tool to get full information about a book."
)
def get_book_info(title: str) -> str:
    resp = requests.get(BASE_URL, params={"title": title})
    resp.raise_for_status()
    data = resp.json()
    docs = data.get("docs", [])
    if not docs:
        return f"No data found for title: {title}"
    doc = docs[0]
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


@tool(
    description="Retrieves information about the most recent book by a given author. Use only this tool to get the latest book from an author."
)
def get_last_book_from_author(author: str) -> str:
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


@tool(
    description="Retrieves the author(s) of a specified book. Use only this tool to get the author(s) of a book."
)
def get_book_author(book: str) -> str:
    resp = requests.get(BASE_URL, params={"q": book})
    resp.raise_for_status()
    data = resp.json()
    docs = data.get("docs", [])
    if not docs:
        return "unknown"
    authors = docs[0].get("author_name", [])
    return authors[0] if authors else "unknown"
