import scraping_kalibrr
import scraping_jobstreet
import scraping_glints

import time

def main():
    start = time.time()

    scraping_kalibrr.scrapeData('public.scrape_items')
    scraping_jobstreet.scrapeData('public.scrape_items')
    scraping_glints.scrapeData('public.scrape_items')
    
    end = time.time()
    print('Waktu total scraping data: ', end-start)
    
    
if __name__ == '__main__':
    main()
