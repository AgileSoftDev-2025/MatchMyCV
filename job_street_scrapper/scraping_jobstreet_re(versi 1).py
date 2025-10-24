# -*- coding: utf-8 -*-
"""Scraping JobStreet (id.jobstreet.com) — list title+link only; detail enrichment via JSON-LD + robust fallbacks + job_field/work_type/salary"""

from bs4 import BeautifulSoup
from tqdm import tqdm
import requests
import pandas as pd
import re
import time
import datetime
import psutil
import os
import json
from dateutil import parser as dateparser  # parse ISO date

import db_mysql  # comment jika belum pakai DB


# ---------- memory profile ----------
def process_memory():
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    return mem_info.rss

def profile(func):
    def wrapper(*args, **kwargs):
        mem_before = process_memory()
        result = func(*args, **kwargs)
        mem_after = process_memory()
        print("{}:consumed memory: {:,}".format(
            func.__name__, mem_before, mem_after, mem_after - mem_before))
        return result
    return wrapper
# -----------------------------------


@profile
def scrapeData(tableName):
    start = time.time()
    net_stat = psutil.net_io_counters()
    net_in_start = net_stat.bytes_recv
    net_out_start = net_stat.bytes_sent

    os.makedirs("data_csv", exist_ok=True)

    # ---- parameters ----
    keywords = ["accounting finance"]   # tambahkan sesuai kebutuhan
    total_pages = 2                     # range(1, total_pages) -> hanya page=1 saat uji

    session = requests.Session()
    headers = {
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "accept-language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    def slugify_kw(kw: str) -> str:
        return re.sub(r"\s+", "-", kw.strip().lower())

    def list_url(keyword: str, page: int) -> str:
        return f"https://id.jobstreet.com/id/{slugify_kw(keyword)}-jobs?page={page}"

    def fetch_soup(url: str, tries: int = 2, delay: float = 1.0):
        for attempt in range(tries):
            try:
                res = session.get(url, headers=headers, timeout=20)
                if res.status_code == 200:
                    return BeautifulSoup(res.content, "lxml")
                else:
                    print(f"[WARN] {res.status_code} for {url}")
            except requests.RequestException as e:
                print(f"[WARN] Request error {e} (attempt {attempt+1}/{tries})")
            time.sleep(delay)
        return None

    def txt(node):
        return node.get_text(strip=True) if node else ""

    def meta_content(soup, prop=None, name=None):
        tag = soup.find("meta", attrs={"property": prop}) if prop else None
        if not tag and name:
            tag = soup.find("meta", attrs={"name": name})
        return tag.get("content") if tag and tag.has_attr("content") else ""

    # ---------- noise guard ----------
    NAV_NOISE = re.compile(
        r"(Jelajahi|Lewati|Menu|Cari lowongan|Lihat profil|Sumber daya karir|Untuk perusahaan|Komunitas)",
        re.I
    )
    def is_noise(s: str, max_len: int = 80):
        if not s:
            return False
        if NAV_NOISE.search(s):
            return True
        if len(s) > max_len:
            return True
        return False
    # ---------------------------------

    # --------- parse relative date (ID/EN) ---------
    def parse_relative_id(s: str):
        s = (s or "").lower()
        today = datetime.date.today()
        m = re.search(r'(\d+)\s*jam', s)
        if m:
            return today
        m = re.search(r'(\d+)\s*hari', s)
        if m:
            return today - datetime.timedelta(days=int(m.group(1)))
        m = re.search(r'(\d+)\s*minggu', s)
        if m:
            return today - datetime.timedelta(weeks=int(m.group(1)))
        m = re.search(r'(\d+)\s*bulan', s)
        if m:
            return today - datetime.timedelta(days=30*int(m.group(1)))
        # English fallbacks:
        m = re.search(r'(\d+)\s*day', s)
        if m:
            return today - datetime.timedelta(days=int(m.group(1)))
        m = re.search(r'(\d+)\s*week', s)
        if m:
            return today - datetime.timedelta(weeks=int(m.group(1)))
        m = re.search(r'(\d+)\s*month', s)
        if m:
            return today - datetime.timedelta(days=30*int(m.group(1)))
        # explicit date "12-Sep-25" / "12 Sep 2025"
        try:
            m1 = re.search(r"\b(\d{1,2}-[A-Za-z]{3}-\d{2})\b", s)
            if m1:
                return datetime.datetime.strptime(m1.group(1), "%d-%b-%y").date()
            m2 = re.search(r"\b(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})\b", s)
            if m2:
                try:
                    return datetime.datetime.strptime(m2.group(1), "%d %B %Y").date()
                except ValueError:
                    return datetime.datetime.strptime(m2.group(1), "%d %b %Y").date()
        except Exception:
            pass
        return today

    # --------- JSON-LD extractor (robust) ---------
    def extract_from_jsonld(soup: BeautifulSoup):
        """
        Scan semua <script type="application/ld+json">, cari object @type == JobPosting.
        Return dict: {title, company, logo, location, datePosted, description}
        """
        best = {}
        scripts = soup.find_all("script", type="application/ld+json")
        for sc in scripts:
            try:
                payload = sc.string or sc.get_text() or ""
                if not payload.strip():
                    continue
                data = json.loads(payload)
            except Exception:
                continue

            # normalisasi ke list kandidat
            candidates = []
            if isinstance(data, dict):
                candidates = [data] + (data.get("@graph") if isinstance(data.get("@graph"), list) else [])
            elif isinstance(data, list):
                candidates = data

            for jp in candidates:
                if not isinstance(jp, dict):
                    continue
                jptype = jp.get("@type")
                if (isinstance(jptype, list) and "JobPosting" in jptype) or (jptype == "JobPosting"):
                    result = {}
                    # title
                    if jp.get("title"):
                        result["title"] = jp["title"]
                    # org
                    org = jp.get("hiringOrganization") or {}
                    if isinstance(org, dict):
                        if org.get("name"):
                            result["company"] = org["name"]
                        lg = org.get("logo")
                        if isinstance(lg, str):
                            result["logo"] = lg
                        elif isinstance(lg, dict) and lg.get("url"):
                            result["logo"] = lg["url"]
                    # location
                    loc_str = None
                    job_loc = jp.get("jobLocation")
                    def addr_to_str(addr):
                        if not isinstance(addr, dict):
                            return None
                        parts = [addr.get("addressLocality"), addr.get("addressRegion"), addr.get("addressCountry")]
                        return ", ".join([p for p in parts if p])
                    if isinstance(job_loc, dict):
                        addr = job_loc.get("address") or {}
                        loc_str = addr_to_str(addr)
                    elif isinstance(job_loc, list) and job_loc:
                        jl0 = job_loc[0]
                        if isinstance(jl0, dict):
                            addr = jl0.get("address") or {}
                            loc_str = addr_to_str(addr)
                    if loc_str:
                        result["location"] = loc_str
                    # datePosted
                    if jp.get("datePosted"):
                        result["datePosted"] = jp["datePosted"]
                    # description
                    if jp.get("description"):
                        result["description"] = BeautifulSoup(jp["description"], "lxml").get_text(" ", strip=True)

                    if result.get("company"):
                        return result
                    best = result
        return best

    # --------- meta fallbacks for company/location ----------
    def company_from_meta(soup: BeautifulSoup, h1_text: str) -> str:
        val = meta_content(soup, prop="og:title") or meta_content(soup, name="twitter:title")
        if not val:
            return ""
        parts = [p.strip() for p in val.split(" - ") if p.strip()]
        # Pola umum: "<H1> - <Company> - JobStreet"
        if len(parts) >= 2:
            if parts[0].lower() == (h1_text or "").strip().lower():
                if len(parts) >= 3:
                    return parts[-2]
                return parts[-1]
            last = parts[-1].lower()
            if last.startswith("jobstreet"):
                return parts[-2]
            return parts[-1]
        return ""

    def location_from_meta(soup: BeautifulSoup) -> str:
        desc = meta_content(soup, prop="og:description") or meta_content(soup, name="twitter:description")
        if not desc:
            return ""
        m = re.search(
            r'(Jakarta(?:\s\w+)?(?:,?\sJakarta Raya)?|Surabaya|Bandung|Bekasi|Depok|Tangerang|Bogor|Yogyakarta|Semarang|Bali|Medan|Makassar|Jawa|Sumatera|Kalimantan|Sulawesi)',
            desc, re.I
        )
        return m.group(0) if m else ""

    # --------- logo extractor (prefer SEEK CDN; includes <picture><source srcset=...>) ----------
    SEEK_HOST_RX = re.compile(r'image-service-cdn\.seek\.com\.au', re.I)

    def parse_srcset(srcset: str) -> str:
        """
        Ambil URL resolusi tertinggi dari atribut srcset.
        """
        if not srcset:
            return ""
        parts = [p.strip() for p in srcset.split(",") if p.strip()]
        if not parts:
            return ""
        return parts[-1].split()[0]

    def extract_logo(dsoup: BeautifulSoup) -> str:
        # 1) <picture><source srcset=...> (prefer)
        for pic in dsoup.find_all("picture"):
            for source in pic.find_all("source"):
                srcset = source.get("srcset") or source.get("data-srcset") or ""
                url = parse_srcset(srcset)
                if url and SEEK_HOST_RX.search(url):
                    return url
            img = pic.find("img")
            if img:
                for attr in ("src", "data-src"):
                    u = img.get(attr)
                    if u and SEEK_HOST_RX.search(u):
                        return u

        # 2) img mana pun di halaman yang host-nya seek
        img_any = dsoup.find("img", src=SEEK_HOST_RX) or dsoup.find("img", attrs={"data-src": SEEK_HOST_RX})
        if img_any:
            return img_any.get("src") or img_any.get("data-src") or ""

        # 3) og:image (cadangan terakhir)
        return meta_content(dsoup, prop="og:image") or ""

    # --------- HTML -> text util for requirement ----------
    def requirement_text_from_node(node: BeautifulSoup) -> str:
        """
        Konversi HTML jobAdDetails menjadi teks rapi:
        - tiap <li> dijadikan baris '- ...'
        - jaga newline antar paragraf/poin
        """
        if not node:
            return ""
        # buat salinan agar aman dimodifikasi
        node = BeautifulSoup(str(node), "lxml")

        # ubah <li> jadi teks dengan prefix '- '
        for li in node.find_all("li"):
            li.insert_before("\n- ")
        # ganti <br> dengan newline
        for br in node.find_all(["br"]):
            br.replace_with("\n")
        # ambil teks dengan separator newline
        text = node.get_text("\n", strip=True)

        # rapikan newline berlebih
        text = re.sub(r'\n{3,}', '\n\n', text)
        # hapus spasi berlebih setelah bullet
        text = re.sub(r'\n-\s*', '\n- ', text)
        # pastikan tidak ada spasi dobel
        text = re.sub(r'[ \t]{2,}', ' ', text)
        return text.strip()

    # --------- enrichment from detail page ----------
    def enrich_from_detail(link: str):
        out = {
            "title": "", "company": "", "location": "", "job_field": "",
            "work_type": "", "salary": "", "requirement": "",
            "posted": "", "image": "", "_date_posted_iso": ""
        }
        if not link:
            return out
        dsoup = fetch_soup(link)
        if dsoup is None:
            return out

        def t(n):
            return n.get_text(strip=True) if n else ""

        # Header elements
        h1 = dsoup.find("h1")
        h1_text = txt(h1)

        # 1) JSON-LD first (title/company/location/desc/logo/date)
        jd = extract_from_jsonld(dsoup)
        out["title"] = jd.get("title", "") or t(dsoup.select_one('[data-automation="jobDetailTitle"]')) or h1_text

        # --- COMPANY priority order ---
        company_adv = t(dsoup.select_one('span[data-automation="advertiser-name"]'))
        company_jld = jd.get("company", "")
        company_sel = (
            t(dsoup.select_one('[data-automation="jobCompany"]')) or
            t(dsoup.select_one('[data-automation="jobCompanyName"]')) or
            t(dsoup.select_one('a[href*="/companies"]'))
        )
        company_meta = company_from_meta(dsoup, h1_text)
        for candidate in [company_adv, company_jld, company_sel, company_meta]:
            if candidate and not is_noise(candidate):
                out["company"] = candidate
                break

        # --- LOCATION (use job-detail-location anchor first) ---
        loc_anchor = t(dsoup.select_one('span[data-automation="job-detail-location"] a'))
        out["location"] = loc_anchor or jd.get("location", "")
        if not out["location"] or is_noise(out["location"], 120):
            loc_sel = (
                t(dsoup.select_one('[data-automation="jobLocation"]')) or
                t(dsoup.select_one('[data-automation="job-location"]'))
            )
            if loc_sel and not is_noise(loc_sel, 120):
                out["location"] = loc_sel
            else:
                region_rx = re.compile(r'(Jakarta|Surabaya|Bandung|Bekasi|Depok|Tangerang|Bogor|Yogyakarta|Semarang|Bali|Medan|Makassar|Jawa|Sumatera|Kalimantan|Sulawesi)', re.I)
                for li in dsoup.find_all(["li","div","span"]):
                    text_ = li.get_text(" ", strip=True)
                    if region_rx.search(text_) and not is_noise(text_, 120):
                        out["location"] = text_
                        break
        if not out["location"] or is_noise(out["location"], 120):
            meta_loc = location_from_meta(dsoup)
            if meta_loc and not is_noise(meta_loc, 120):
                out["location"] = meta_loc

        # --- JOB FIELD ---
        out["job_field"] = (
            t(dsoup.select_one('[data-automation="job-detail-classification"]')) or
            t(dsoup.select_one('a[href^="/id/jobs-in-"]'))
        )

        # --- WORK TYPE ---
        out["work_type"] = t(dsoup.select_one('span[data-automation="job-detail-work-type"] a'))

        # --- SALARY ---
        out["salary"] = t(dsoup.select_one('span[data-automation="job-detail-salary"]'))

        # --- REQUIREMENT (prioritaskan jobAdDetails) ---
        job_ad_details = dsoup.select_one('div[data-automation="jobAdDetails"]')
        if job_ad_details:
            out["requirement"] = requirement_text_from_node(job_ad_details)
        else:
            out["requirement"] = jd.get("description", "")
            if not out["requirement"]:
                req_node = dsoup.select_one('[data-automation="jobDescription"]')
                out["requirement"] = requirement_text_from_node(req_node) if req_node else ""
                if not out["requirement"]:
                    section = dsoup.find("section")
                    out["requirement"] = txt(section)

        # LOGO (prefer SEEK CDN)
        out["image"] = jd.get("logo", "") or extract_logo(dsoup)

        # DATE
        out["_date_posted_iso"] = jd.get("datePosted", "")
        if not out["_date_posted_iso"]:
            page_text = dsoup.get_text(" ", strip=True)
            m = re.search(r"\b(\d{1,2}-[A-Za-z]{3}-\d{2})\b", page_text) \
              or re.search(r"\b(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})\b", page_text)
            if m:
                out["posted"] = m.group(1)
            else:
                cand = dsoup.find(string=re.compile(r'(Posted|hari|minggu|bulan|jam).*lalu', re.I))
                out["posted"] = cand.strip() if isinstance(cand, str) else txt(cand)

        return out

    # -------- list page: ONLY TITLE + LINK (avoid noise) --------
    rows = []
    for kw in keywords:
        for page in tqdm(range(1, total_pages)):
            url = list_url(kw, page)
            print("Scraping list:", url)
            soup = fetch_soup(url)
            if soup is None:
                continue

            cards = soup.find_all(attrs={"data-automation": re.compile(r"job-card", re.I)})
            if not cards:
                # Fallback: anchor jobTitle
                for a in soup.select('a[data-automation="jobTitle"]'):
                    parent = a.find_parent("div") or a.find_parent("article")
                    if parent:
                        cards.append(parent)

            if not cards:
                print("[INFO] Tidak menemukan job cards di halaman ini. Selector mungkin beda.")
                continue

            for card in cards:
                a_title = card.select_one('a[data-automation="jobTitle"]')
                if not a_title:
                    continue
                title = txt(a_title)
                href = a_title.get("href") if a_title and a_title.has_attr("href") else ""
                link = href if href.startswith("http") else ("https://id.jobstreet.com" + href if href else "")
                if not link:
                    continue
                rows.append({"title": title, "link": link})

            time.sleep(0.6)

    # -------- enrich details for every row --------
    enriched = []
    for r in rows:
        det = enrich_from_detail(r["link"])
        enriched.append({
            "title": r["title"] or det["title"],
            "company": det["company"],
            "location": det["location"],
            "job_field": det["job_field"],
            "work_type": det["work_type"],
            "salary": det["salary"],
            "requirement": det["requirement"],
            "posted": det["posted"],
            "image": det["image"],   # logo
            "link": r["link"],
            "_date_posted_iso": det["_date_posted_iso"]
        })

    if not enriched:
        print("[INFO] Tidak ada data ter-scrape.")
        return pd.DataFrame(columns=['title','company','location','job_field','work_type','salary','requirement','posted','image','link','date_posted'])

    # ---- date_posted: STRING ISO to avoid 1970 ----
    def to_date(dstr):
        try:
            return dateparser.isoparse(dstr).date()
        except Exception:
            return None

    dates = []
    for r in enriched:
        dp = None
        if r.get("_date_posted_iso"):
            dp = to_date(r["_date_posted_iso"])
        if not dp:
            dp = parse_relative_id(r.get("posted", ""))
        dates.append(dp or datetime.date.today())
    date_posted_str = [d.isoformat() for d in dates]

    # Build DataFrame (ensure correct column mapping)
    df = pd.DataFrame(
        [{k: v for k, v in rec.items() if k != "_date_posted_iso"} for rec in enriched],
        columns=['title','company','location','job_field','work_type','salary','requirement','posted','image','link']
    )
    df["date_posted"] = date_posted_str

    # light cleanup
    def clean_noise(s):
        if is_noise(s, 200):
            return ""
        return s

    for col in ["company", "location", "job_field", "work_type", "salary"]:
        df[col] = df[col].apply(lambda x: clean_noise(x))

    df_for_csv = df.copy()
    df_for_csv = df_for_csv.replace(r'\t|\r', '', regex=True)
    df_for_csv["requirement"] = df_for_csv["requirement"].replace(r'\s{3,}', '  ', regex=True)

    date_scrape = datetime.date.today().strftime("%Y-%m-%d")
    out_path = f"data_csv/jobs_data_jobstreet({date_scrape} {len(df_for_csv.index)}).xlsx"
    try:
        df_for_csv.to_excel(out_path, index=False)
        print(f"[OK] Tersimpan: {out_path}")
    except Exception as e:
        print(f"[WARN] Gagal simpan Excel: {e}")

    # ---- save to DB (optional) ----
    try:
        db_mysql.insertData(df, tableName)
        db_mysql.removeDuplicate(tableName)
    except Exception as e:
        print(f"[WARN] Insert DB gagal: {e}")

    net_stat_end = psutil.net_io_counters()
    end = time.time()
    print("Scrape is finished..")
    print("Time elapse with time:", end - start)
    print("Data usage IN:", net_stat_end.bytes_recv - net_in_start,
          ", OUT:", net_stat_end.bytes_sent - net_out_start)
    print("total", len(df.index))
    return df


if __name__ == "__main__":
    scrapeData("public.scrape_items")
