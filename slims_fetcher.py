# -*- coding: utf-8 -*-
import sys
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import mysql.connector
from datetime import datetime

# Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'YOUR_PASSWORD_HERE',  # Adjust this if your root has a password
    'database': 'slims_db'
}

def clean_isbn(isbn_str):
    return ''.join(c for c in isbn_str if c.isdigit())

def fetch_from_loc(isbn):
    print(f"[*] Querying Library of Congress for ISBN: {isbn}...")
    # Using raw HTTP SRU endpoint with standard MARCXML schema
    base_url = "http://lx2.loc.gov:210/LCDB"
    query = f'dc.identifier="{isbn}"'
    params = {
        'operation': 'searchRetrieve',
        'version': '1.1',
        'query': query,
        'maximumRecords': '1',
        'recordSchema': 'marcxml'
    }
    
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read()
    except Exception as e:
        print(f"[-] Network connection failed: {e}")
        return None

    # Parse MARCXML Response
    try:
        # Standard SRU namespaces
        namespaces = {
            'sru': 'http://www.loc.gov/zing/srw/',
            'marc': 'http://www.loc.gov/MARC21/slim'
        }
        
        root = ET.fromstring(xml_data)
        
        # Check if record exists
        record_node = root.find('.//marc:record', namespaces)
        if record_node is None:
            print("[-] No records found matching this ISBN.")
            return None
            
        book = {
            'title': 'Unknown Title',
            'author': '',
            'publisher': '',
            'publish_year': '',
            'isbn': isbn
        }
        
        # Extract fields using standard MARC21 tags
        for field in record_node.findall('marc:datafield', namespaces):
            tag = field.get('tag')
            
            # Title Statement (245)
            if tag == '245':
                a = field.find("marc:subfield[@code='a']", namespaces)
                b = field.find("marc:subfield[@code='b']", namespaces)
                title_str = (a.text if a is not None else '') + (b.text if b is not None else '')
                book['title'] = title_str.strip(' /.,:')
                
            # Main Entry - Personal Name (100)
            elif tag == '100':
                a = field.find("marc:subfield[@code='a']", namespaces)
                if a is not None:
                    book['author'] = a.text.strip(' /.,:')
                    
            # Publication, Distribution, etc. (260 or 264)
            elif tag in ['260', '264']:
                b = field.find("marc:subfield[@code='b']", namespaces) # Publisher
                c = field.find("marc:subfield[@code='c']", namespaces) # Year
                if b is not None:
                    book['publisher'] = b.text.strip(' /.,:')
                if c is not None:
                    # Clean out letters/brackets from year string
                    year_str = ''.join(c for c in c.text if c.isdigit())[:4] if c.text else ''
                    book['publish_year'] = year_str

        print(f"[+] Successfully fetched: {book['title']} by {book['author']}")
        return book

    except Exception as e:
        print(f"[-] Failed to parse XML response: {e}")
        return None

def inject_into_slims(book):
    print("[*] Connecting to SLiMS database...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 1. Author logic
        author_id = 1 # Default fallback to first author block if empty
        if book['author']:
            # Check if author already exists
            cursor.execute("SELECT author_id FROM mst_author WHERE author_name = %s", (book['author'],))
            row = cursor.fetchone()
            if row:
                author_id = row[0]
            else:
                # Insert new author record
                cursor.execute(
                    "INSERT INTO mst_author (author_name, type, last_update) VALUES (%s, 'p', %s)",
                    (book['author'], now_str)
                )
                author_id = cursor.lastrowid

        # 2. Publisher logic
        publisher_id = 1
        if book['publisher']:
            cursor.execute("SELECT publisher_id FROM mst_publisher WHERE publisher_name = %s", (book['publisher'],))
            row = cursor.fetchone()
            if row:
                publisher_id = row[0]
            else:
                cursor.execute(
                    "INSERT INTO mst_publisher (publisher_name, last_update) VALUES (%s, %s)",
                    (book['publisher'], now_str)
                )
                publisher_id = cursor.lastrowid

        # 3. Inject core item description block (bibliography table)
        # SLiMS 9 builds on 'biblio' as the core entity container
        sql_biblio = """
            INSERT INTO biblio (
                title, isbn_issn, publisher_id, publish_year, 
                input_date, last_update, opac_hide, uid
            ) VALUES (%s, %s, %s, %s, %s, %s, 0, 1)
        """
        cursor.execute(sql_biblio, (
            book['title'], 
            book['isbn'], 
            publisher_id, 
            book['publish_year'] if book['publish_year'] else None,
            now_str, 
            now_str
        ))
        biblio_id = cursor.lastrowid

        # 4. Map author mapping relationship link table
        sql_author_map = "INSERT INTO biblio_author (biblio_id, author_id, level) VALUES (%s, %s, 1)"
        cursor.execute(sql_author_map, (biblio_id, author_id))

        conn.commit()
        print(f"[+] Success! '{book['title']}' is now available inside your SLiMS catalog dashboard.")
        
    except mysql.connector.Error as err:
        print(f"[-] Database operation failed: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 slims_fetcher.py <ISBN>")
        sys.exit(1)
        
    raw_isbn = sys.argv[1]
    clean_num = clean_isbn(raw_isbn)
    
    if not clean_num:
        print("[-] Error: Invalid ISBN format provided.")
        sys.exit(1)
        
    book_data = fetch_from_loc(clean_num)
    if book_data:
        inject_into_slims(book_data)
