#! /usr/bin/env python3

import argparse
import logging

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
    
    # got list of ISBNs
    # for each one
    #   look up on server
    #   if they are good
    #     then vomit them into the database
    #   else give a warning

    for each_isbn in args.isbn:
        logging.debug(f"..handling {each_isbn}")
