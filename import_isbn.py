#! /usr/bin/env python3

import argparse
import logging
import requests
import csv
import os
import sys

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Import ISBNs into SLiMS database"
        )
    parser.add_argument(
        "isbn",
        metavar="isbn",
        nargs="+",
        help="an ISBN or list of ISBNs to try to import")
    parser.add_argument(
        "--verbose","-v",action="store_true",help="toggle verbosity")
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)

    logging.debug(f"Working on ISBNs: {args.isbn}")

    # setup output
    headers_csv = ['title','isbn_issn','publisher_name','publish_year','authors']
    ofile = sys.stdout
    header_writer = csv.writer(
        ofile,
        quoting=csv.QUOTE_NONE)
    header_writer.writerow(headers_csv)
    
    writer = csv.DictWriter(
        ofile,
        fieldnames=headers_csv,
        quoting=csv.QUOTE_ALL)
    
    # got list of ISBNs
    # for each one
    #   look up on server
    #   if they are good
    #     then vomit them into the database
    #   else give a warning

    for each_isbn in args.isbn:
        logging.debug(f"Handling ISBN: {each_isbn}")

        url = "https://openlibrary.org/api/books"
        params = {
            "bibkeys": f"ISBN:{each_isbn}",
            "format": "json",
            "jscmd": "data"
            }
        headers = {
            "User-Agent": "pyslims/0.0 (devangel77b@gmail.com)"
            }
        response = requests.get(url, params=params,headers=headers)
        data = response.json()
        book_key = f"ISBN:{each_isbn}"
        if book_key in data:
            book_info = data[book_key]
            logging.debug(f"Found title: {book_info.get("title")}")

            authors=", ".join([a['name'] for a in book_info.get("authors", [])])
            pub_date = book_info.get("publish_date", "")
            pub_year = pub_date[-4:] if len(pub_date) >= 4 else ""
            publishers = ", ".join([p['name'] for p in book_info.get("publishers", [])])
            writer.writerow({
                "title": book_info.get("title", ""),
                "isbn_issn": each_isbn,
                "publisher_name": publishers,
                "publish_year": pub_year,
                "authors": authors
            })
            logging.debug(f"Successfully processed ISBN: {each_isbn}")
        else:
            logging.debug("Not found on Open Library, skipping.")

    ofile.close()
