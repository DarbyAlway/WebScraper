import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, unquote
import os
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor

# --- CONFIGURATION ---
base_url = "https://www.musashino-u.ac.jp/"
visited = set()
to_visit = [base_url]
MAX_PDFS = 10
pdfs_saved = 0
PDF_DIR = "downloaded_pdfs"

if not os.path.exists(PDF_DIR):
    os.makedirs(PDF_DIR)

lock = threading.Lock()
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
})

def scrape_page(url):
    global pdfs_saved
    
    with lock:
        if pdfs_saved >= MAX_PDFS:
            return []

    time.sleep(random.uniform(1, 2)) 

    try:
        # 1. DOWNLOAD PDF
        if url.lower().endswith('.pdf'):
            res = session.get(url, timeout=20, stream=True)
            if res.status_code == 200:
                # unquote converts %E3%83... into Japanese characters for the filename
                file_name = unquote(url.split('/')[-1])
                save_path = os.path.join(PDF_DIR, file_name)
                
                with open(save_path, 'wb') as f:
                    for chunk in res.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                with lock:
                    pdfs_saved += 1
                    print(f"[{pdfs_saved}/{MAX_PDFS}] Saved: {file_name}")
            return [] 

        # 2. FIND LINKS ON HTML PAGES
        res = session.get(url, timeout=15)
        res.encoding = res.apparent_encoding # Handles Japanese encoding automatically
        
        if 'text/html' not in res.headers.get('Content-Type', '').lower():
            return []

        soup = BeautifulSoup(res.text, "html.parser")
        new_links = []
        
        for link in soup.find_all("a", href=True):
            full_url = urljoin(base_url, link["href"]).split('#')[0].rstrip('/')
            
            # Stay on Musashino domain
            if urlparse(full_url).netloc == urlparse(base_url).netloc:
                if full_url not in visited:
                    new_links.append(full_url)
                    
        return new_links

    except Exception as e:
        # print(f"Error at {url}: {e}") # Uncomment if you want to see errors
        return []

# --- MAIN LOOP ---
print(f"Starting crawl... Target: {MAX_PDFS} PDF files.")

with ThreadPoolExecutor(max_workers=3) as executor:
    while to_visit and pdfs_saved < MAX_PDFS:
        current_batch = []
        while to_visit and len(current_batch) < 3:
            target = to_visit.pop(0)
            if target not in visited:
                visited.add(target)
                current_batch.append(target)
        
        if not current_batch:
            break

        results = executor.map(scrape_page, current_batch)
        for links in results:
            if links:
                for l in links:
                    if l not in visited:
                        to_visit.append(l)

print(f"\nSuccess! Downloaded {pdfs_saved} files to the '{PDF_DIR}' folder.")