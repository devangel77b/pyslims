import sys
import requests
import mysql.connector

# --- CONFIGURATION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'YOUR_PASSWORD_HERE',  # Update this with your actual MySQL password
    'database': 'slims_db'
}

def clean_isbn(raw_args):
    """Safely extract the second argument string and strip any non-digit character."""
    if len(raw_args) < 2:
        return None
    # Isolate the text string you typed in the terminal
    isbn_string = raw_args
    return ''.join(c for c in isbn_string if c.isdigit())

def fetch_book_data(isbn):
    """Fetch clean book metadata from Open Library API."""
    print(f"[*] Querying Open Library for ISBN: {isbn}...")
    
    # FIXED: Correct, explicit endpoint path string format
    url = f"https://openlibrary.org:{isbn}&jscmd=data&format=json"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        key = f"ISBN:{isbn}"
        if key not in data:
            print(f"[-] No records found for ISBN {isbn} on Open Library.")
            return None
            
        book_info = data[key]
        
        # Extract title cleanly
        title = book_info.get('title', 'Unknown Title')
        subtitle = book_info.get('subtitle')
        if subtitle:
            title = f"{title}: {subtitle}"
            
        # Extract authors and convert to plain text string
        authors = [a.get('name') for a in book_info.get('authors', []) if a.get('name')]
        author_str = ", ".join(authors) if authors else 'Unknown Author'
        
        # Extract publishers and convert to plain text string
        publishers = [p.get('name') for p in book_info.get('publishers', []) if p.get('name')]
        publisher_str = ", ".join(publishers) if publishers else 'Unknown Publisher'
        
        # Extract publish year
        publish_date = book_info.get('publish_date', '')
        publish_year = ''.join(c for c in publish_date if c.isdigit())[:4]
        if not publish_year or len(publish_year) < 4:
            publish_year = '0000'
            
        return {
            'title': title,
            'author': author_str,
            'publisher': publisher_str,
            'publish_year': publish_year,
            'isbn': isbn
        }
        
    except Exception as e:
        print(f"[-] API Fetching/Parsing Error: {e}")
        return None

def inject_to_slims(book):
    """Directly insert the metadata into SLiMS structural tables."""
    print("[*] Connecting to SLiMS database...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 1. Handle Publisher (Extract index 0 from tuple)
        cursor.execute("SELECT publisher_id FROM mst_publisher WHERE publisher_name = %s", (book['publisher'],))
        pub_row = cursor.fetchone()
        if pub_row:
            publisher_id = pub_row
        else:
            cursor.execute("INSERT INTO mst_publisher (publisher_name, input_date, last_update) VALUES (%s, NOW(), NOW())", (book['publisher'],))
            publisher_id = cursor.lastrowid

        # 2. Handle Author (Extract index 0 from tuple)
        cursor.execute("SELECT author_id FROM mst_author WHERE author_name = %s", (book['author'],))
        auth_row = cursor.fetchone()
        if auth_row:
            author_id = auth_row
        else:
            cursor.execute("INSERT INTO mst_author (author_name, input_date, last_update) VALUES (%s, NOW(), NOW())", (book['author'],))
            author_id = cursor.lastrowid

        # 3. Handle Main Bibliography Record
        sql_biblio = """
            INSERT INTO biblio (title, isbn_issn, publish_year, publisher_id, input_date, last_update) 
            VALUES (%s, %s, %s, %s, NOW(), NOW())
        """
        cursor.execute(sql_biblio, (book['title'], book['isbn'], book['publish_year'], publisher_id))
        biblio_id = cursor.lastrowid

        # 4. Link Bibliography to Author in the pivot table
        sql_link = "INSERT INTO biblio_author (biblio_id, author_id, level) VALUES (%s, %s, 1)"
        cursor.execute(sql_link, (biblio_id, author_id))

        conn.commit()
        print(f"[+] Success! '{book['title']}' is now live inside your SLiMS catalog dashboard.")
        
    except mysql.connector.Error as err:
        print(f"[-] Database Insertion Failed: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    target_isbn = clean_isbn(sys.argv)
    if not target_isbn:
        print("Usage: python3 openlibrary_to_slims.py <ISBN>")
        sys.exit(1)
        
    book_metadata = fetch_book_data(target_isbn)
    if book_metadata:
        inject_to_slims(book_metadata)
