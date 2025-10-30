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

# =========================
# Config / Tuning Section
# =========================
KEYWORDS = [
    # Core dev / eng
    "software engineer", "backend developer", "frontend developer", "full stack developer",
    "mobile developer", "android developer", "ios developer",
    "programmer", "web developer", "devops", "site reliability engineer",
    "data engineer", "machine learning engineer", "ai engineer",

    # Sistem Informasi relevan
    "system analyst", "business analyst", "it business analyst",
    "data analyst", "bi analyst", "database administrator", "dba",
    "qa engineer", "quality assurance", "sqa", "software tester",
    "product manager (tech)", "it project manager", "scrum master",
    "it support", "helpdesk", "network engineer", "sysadmin",
    "erp consultant", "sap consultant", "crm consultant",
    "it auditor", "it governance", "it risk", "information security", "soc analyst",
    "ui ux designer", "ui/ux", "ux researcher",

    # Versi Indonesia
    "pengembang perangkat lunak", "pengembang web", "analis sistem",
    "analis bisnis", "dukungan it", "jaringan", "keamanan informasi",

    # Entry-level signals
    "fresh graduate it", "entry level it", "junior developer", "magang it",
]

# Soft preferences (set [] untuk disable)
PREFERRED_LOCATIONS = [
    "Indonesia", "Jakarta", "Jabodetabek", "Bandung", "Surabaya", "Yogyakarta",
    "Semarang", "Bali", "Malang", "Medan", "Makassar", "Remote"
]
PREFERRED_WORKTYPES = ["full-time", "kontrak", "contract", "intern", "internship", "remote", "hybrid"]

# Rate limits
REQUEST_RETRIES = 2
REQUEST_DELAY = 0.6
REQUEST_TIMEOUT = 20

# =========================
# Memory profile utilities
# =========================
def process_memory():
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    return mem_info.rss

def profile(func):
    def wrapper(*args, **kwargs):
        mem_before = process_memory()
        result = func(*args, **kwargs)
        mem_after = process_memory()
        print(
            "{}: memory before {:,} after {:,} diff {:,}".format(
                func.__name__, mem_before, mem_after, mem_after - mem_before
            )
        )
        return result
    return wrapper

# =========================
# Helpers
# =========================
def slugify_kw(kw: str) -> str:
    return re.sub(r"\s+", "-", kw.strip().lower())

def list_url(keyword: str, page: int) -> str:
    return f"https://id.jobstreet.com/id/{slugify_kw(keyword)}-jobs?page={page}"

def fetch_soup(session: requests.Session, url: str, headers: dict, tries: int = REQUEST_RETRIES, delay: float = 1.0):
    for attempt in range(tries):
        try:
            res = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
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

# ---------- noise guard ----------
NAV_NOISE = re.compile(
    r"(Jelajahi|Lewati|Menu|Cari lowongan|Lihat profil|Sumber daya karir|Untuk perusahaan|Komunitas)",
    re.I,
)

def is_noise(s: str, max_len: int = 80):
    if not s:
        return False
    if NAV_NOISE.search(s):
        return True
    if len(s) > max_len:
        return True
    return False

# --------- parse relative date (ID/EN) ---------
def parse_relative_id(s: str):
    s = (s or "").lower()
    today = datetime.date.today()
    m = re.search(r"(\d+)\s*jam", s)
    if m:
        return today
    m = re.search(r"(\d+)\s*hari", s)
    if m:
        return today - datetime.timedelta(days=int(m.group(1)))
    m = re.search(r"(\d+)\s*minggu", s)
    if m:
        return today - datetime.timedelta(weeks=int(m.group(1)))
    m = re.search(r"(\d+)\s*bulan", s)
    if m:
        return today - datetime.timedelta(days=30 * int(m.group(1)))
    # English fallbacks
    m = re.search(r"(\d+)\s*day", s)
    if m:
        return today - datetime.timedelta(days=int(m.group(1)))
    m = re.search(r"(\d+)\s*week", s)
    if m:
        return today - datetime.timedelta(weeks=int(m.group(1)))
    m = re.search(r"(\d+)\s*month", s)
    if m:
        return today - datetime.timedelta(days=30 * int(m.group(1)))
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
    Cari object @type == JobPosting.
    Return: {title, company, logo, location, datePosted, description}
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
                if jp.get("title"):
                    result["title"] = jp["title"]
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
                if jp.get("datePosted"):
                    result["datePosted"] = jp["datePosted"]
                if jp.get("description"):
                    result["description"] = BeautifulSoup(jp["description"], "lxml").get_text(" ", strip=True)

                if result.get("company"):
                    return result
                best = result
    return best

# --------- meta fallbacks ----------
def meta_content(soup, prop=None, name=None):
    tag = soup.find("meta", attrs={"property": prop}) if prop else None
    if not tag and name:
        tag = soup.find("meta", attrs={"name": name})
    return tag.get("content") if tag and tag.has_attr("content") else ""

def company_from_meta(soup: BeautifulSoup, h1_text: str) -> str:
    val = meta_content(soup, prop="og:title") or meta_content(soup, name="twitter:title")
    if not val:
        return ""
    parts = [p.strip() for p in val.split(" - ") if p.strip()]
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

# GENERIC location from meta
GENERIC_LOC_RX = re.compile(r"([A-Z][\w .&/-]+(?:,\s*[A-Z][\w .&/-]+)+)")

def location_from_meta(soup: BeautifulSoup) -> str:
    desc = meta_content(soup, prop="og:description") or meta_content(soup, name="twitter:description")
    if not desc:
        return ""
    m = GENERIC_LOC_RX.search(desc)
    return m.group(1) if m else ""

# --------- logo extractor (prefer SEEK CDN) ----------
SEEK_HOST_RX = re.compile(r"image-service-cdn\.seek\.com\.au", re.I)

def parse_srcset(srcset: str) -> str:
    if not srcset:
        return ""
    parts = [p.strip() for p in srcset.split(",") if p.strip()]
    if not parts:
        return ""
    return parts[-1].split()[0]

def extract_logo(dsoup: BeautifulSoup) -> str:
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
    img_any = dsoup.find("img", src=SEEK_HOST_RX) or dsoup.find("img", attrs={"data-src": SEEK_HOST_RX})
    if img_any:
        return img_any.get("src") or img_any.get("data-src") or ""
    return meta_content(dsoup, prop="og:image") or ""

# --------- HTML -> text util for requirement ----------
def requirement_text_from_node(node: BeautifulSoup) -> str:
    if not node:
        return ""
    node = BeautifulSoup(str(node), "lxml")
    for li in node.find_all("li"):
        li.insert_before("\n- ")
    for br in node.find_all(["br"]):
        br.replace_with("\n")
    text = node.get_text("\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"\n-\s*", "\n- ", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()

# --------- enrichment from detail page ----------
def enrich_from_detail(session: requests.Session, headers: dict, link: str):
    out = {
        "title": "", "company": "", "location": "", "job_field": "",
        "work_type": "", "salary": "", "requirement": "",
        "posted": "", "image": "", "_date_posted_iso": "",
    }
    if not link:
        return out
    dsoup = fetch_soup(session, link, headers)
    if dsoup is None:
        return out

    def t(n):
        return n.get_text(strip=True) if n else ""

    h1 = dsoup.find("h1")
    h1_text = txt(h1)

    jd = extract_from_jsonld(dsoup)
    out["title"] = jd.get("title", "") or t(dsoup.select_one('[data-automation="jobDetailTitle"]')) or h1_text

    # COMPANY
    company_adv = t(dsoup.select_one('span[data-automation="advertiser-name"]'))
    company_jld = jd.get("company", "")
    company_sel = (
        t(dsoup.select_one('[data-automation="jobCompany"]'))
        or t(dsoup.select_one('[data-automation="jobCompanyName"]'))
        or t(dsoup.select_one('a[href*="/companies"]'))
    )
    company_meta = company_from_meta(dsoup, h1_text)
    for candidate in [company_adv, company_jld, company_sel, company_meta]:
        if candidate and not is_noise(candidate):
            out["company"] = candidate
            break

    # LOCATION
    loc_anchor = t(dsoup.select_one('span[data-automation="job-detail-location"] a'))
    out["location"] = loc_anchor or jd.get("location", "")
    if not out["location"] or is_noise(out["location"], 120):
        loc_sel = (
            t(dsoup.select_one('[data-automation="jobLocation"]'))
            or t(dsoup.select_one('[data-automation="job-location"]'))
        )
        if loc_sel and not is_noise(loc_sel, 120):
            out["location"] = loc_sel
        else:
            best = ""
            for el in dsoup.find_all(["span", "div", "li", "p"]):
                s = el.get_text(" ", strip=True)
                m = GENERIC_LOC_RX.search(s)
                if m:
                    cand = m.group(1)
                    if 3 <= len(cand) <= 80:
                        best = cand
                        break
            if best:
                out["location"] = best
    if not out["location"] or is_noise(out["location"], 120):
        meta_loc = location_from_meta(dsoup)
        if meta_loc and not is_noise(meta_loc, 120):
            out["location"] = meta_loc

    # JOB FIELD
    out["job_field"] = (
        t(dsoup.select_one('[data-automation="job-detail-classification"]'))
        or t(dsoup.select_one('a[href^="/id/jobs-in-"]'))
    )

    # WORK TYPE
    out["work_type"] = t(dsoup.select_one('span[data-automation="job-detail-work-type"] a'))

    # SALARY
    out["salary"] = t(dsoup.select_one('span[data-automation="job-detail-salary"]'))

    # REQUIREMENT
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

    # LOGO
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
            cand = dsoup.find(string=re.compile(r"(Posted|hari|minggu|bulan|jam).*lalu", re.I))
            out["posted"] = cand.strip() if isinstance(cand, str) else txt(cand)

    return out

# --------- IT/SI Relevance Filters ----------
INCLUDE_TITLE_RX = re.compile(
    r"\b(software\s+engineer|backend|frontend|full\s*stack|mobile|android|ios|web\s+developer|"
    r"programmer|devops|sre|data\s+engineer|ml\s+engineer|ai\s+engineer|"
    r"system\s+analyst|business\s+analyst|it\s+business\s+analyst|data\s+analyst|bi\s+analyst|"
    r"database\s+administrator|dba|qa|quality\s+assurance|sqa|tester|product\s+manager|"
    r"it\s+project\s+manager|scrum\s+master|it\s+support|helpdesk|network\s+engineer|sysadmin|"
    r"erp|sap|crm|it\s+auditor|governance|risk|information\s+security|soc|ui\s*/?\s*ux|ux\s+research)\b",
    re.I,
)

INCLUDE_FIELD_RX = re.compile(
    r"\b(Information\s*&\s*Communication|Information\s+Technology|Software|Computer|"
    r"Systems\s+Analyst|Data|Database|Business\s+Analysis|Quality\s+Assurance|Security|Network|"
    r"IT|Engineering|Developer|Programming|UI|UX|Product|Project|ERP|SAP|CRM)\b",
    re.I,
)

EXCLUDE_TITLE_RX = re.compile(
    r"\b(sales|marketing|telemarketing|customer\s+service|cs|admin|receptionist|cashier|"
    r"waiter|barista|accounting|finance|hr|human\s+resources|purchasing|logistics?)\b",
    re.I,
)

PREFERRED_WORKTYPE_RX = re.compile(r"\b(" + "|".join([re.escape(w) for w in PREFERRED_WORKTYPES]) + r")\b", re.I) if PREFERRED_WORKTYPES else None
PREFERRED_LOCATION_RX = re.compile(r"\b(" + "|".join([re.escape(c) for c in PREFERRED_LOCATIONS]) + r")\b", re.I) if PREFERRED_LOCATIONS else None

def keep_row(rec: dict) -> bool:
    title = (rec.get("title") or "").strip()
    field = (rec.get("job_field") or "").strip()
    work = (rec.get("work_type") or "").strip()
    loc = (rec.get("location") or "").strip()

    include_hit = bool(INCLUDE_TITLE_RX.search(title)) or bool(INCLUDE_FIELD_RX.search(field))
    exclude_hit = bool(EXCLUDE_TITLE_RX.search(title)) and (" it" not in f" {title.lower()} ")

    if not include_hit or exclude_hit:
        return False

    if PREFERRED_WORKTYPE_RX and work and not PREFERRED_WORKTYPE_RX.search(work):
        pass  # uncomment return False jika ingin strict

    if PREFERRED_LOCATION_RX and loc and not PREFERRED_LOCATION_RX.search(loc):
        pass  # uncomment return False jika ingin strict

    return True

# --------- Level inference ----------
def infer_level(title: str) -> str:
    t = (title or "").lower()
    if "intern" in t or "magang" in t:
        return "Intern"
    if "junior" in t or re.search(r"\bjr\b", t):
        return "Junior"
    if "senior" in t or re.search(r"\bsr\b", t):
        return "Senior"
    if any(k in t for k in ["lead", "principal", "head"]):
        return "Lead/Principal"
    return "Mid/Unspecified"

# =========================
# Main Scraper
# =========================
@profile
def scrapeData(
    tableName: str = "public.scrape_items",
    max_jobs: int | None = None,                 # None = tanpa batas jumlah
    max_pages_per_kw: int | None = None          # None = tanpa batas halaman per keyword
):
    start = time.time()
    net_stat = psutil.net_io_counters()
    net_in_start = net_stat.bytes_recv
    net_out_start = net_stat.bytes_sent

    os.makedirs("data_csv", exist_ok=True)

    session = requests.Session()
    headers = {
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "accept-language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    # -------- list page: ONLY TITLE + LINK (auto paginate) --------
    rows = []
    seen_links = set()

    for kw in KEYWORDS:
        if max_jobs and len(rows) >= max_jobs:
            break

        page = 1
        empty_pages_in_a_row = 0
        print(f"[KW] {kw}")
        while True:
            if max_jobs and len(rows) >= max_jobs:
                break
            if max_pages_per_kw and page > max_pages_per_kw:
                break

            url = list_url(kw, page)
            print("Scraping list:", url)
            soup = fetch_soup(session, url, headers, tries=REQUEST_RETRIES, delay=REQUEST_DELAY)
            if soup is None:
                break

            found_in_page = 0

            # Selector utama
            for card in soup.select('[data-automation="jobCard"]'):
                a = card.select_one('a[data-automation="jobTitle"], a[href*="/job/"]')
                if not a:
                    continue
                link = a.get("href", "")
                if not link:
                    continue
                if link.startswith("/"):
                    link = "https://id.jobstreet.com" + link
                title = txt(a)
                if not title or link in seen_links:
                    continue

                rows.append({"title": title, "link": link, "kategori": kw})
                seen_links.add(link)
                found_in_page += 1

                if max_jobs and len(rows) >= max_jobs:
                    break

            # Fallback selector bila selector utama tidak menemukan apapun
            if (not max_jobs or len(rows) < max_jobs) and found_in_page == 0:
                for a in soup.select('a[href*="/job/"]'):
                    link = a.get("href", "")
                    if not link:
                        continue
                    if link.startswith("/"):
                        link = "https://id.jobstreet.com" + link
                    title = txt(a)
                    if not title or is_noise(title) or link in seen_links:
                        continue
                    rows.append({"title": title, "link": link, "kategori": kw})
                    seen_links.add(link)
                    found_in_page += 1
                    if max_jobs and len(rows) >= max_jobs:
                        break

            if max_jobs and len(rows) >= max_jobs:
                break

            # Stop jika 2 halaman berturut-turut kosong
            if found_in_page == 0:
                empty_pages_in_a_row += 1
                if empty_pages_in_a_row >= 2:
                    break
            else:
                empty_pages_in_a_row = 0

            page += 1

    # -------- enrich details + filter for SI/IT --------
    enriched = []
    iter_rows = rows if not max_jobs else rows[:max_jobs]

    for r in tqdm(iter_rows, desc="Enrich detail"):
        det = enrich_from_detail(session, headers, r["link"])
        rec = {
            "title": r["title"] or det["title"],
            "company": det["company"],
            "location": det["location"],
            "job_field": det["job_field"],
            "work_type": det["work_type"],
            "salary": det["salary"],
            "requirement": det["requirement"],
            "posted": det["posted"],
            "image": det["image"],
            "link": r["link"],
            "_date_posted_iso": det["_date_posted_iso"],
            "kategori": r.get("kategori", ""),
        }
        if keep_row(rec):
            enriched.append(rec)
        # Jika ingin limit hasil lolos filter, aktifkan guard ini:
        # if max_jobs and len(enriched) >= max_jobs:
        #     break

    if not enriched:
        print("[INFO] Tidak ada data ter-scrape (setelah filter SI/IT).")
        return pd.DataFrame(
            columns=[
                "title", "company", "location", "job_field", "work_type", "salary",
                "requirement", "posted", "image", "link", "date_posted", "level", "kategori"
            ]
        )

    # ---- date_posted: STRING ISO ----
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

    # Build DataFrame
    df = pd.DataFrame(
        [{k: v for k, v in rec.items() if k != "_date_posted_iso"} for rec in enriched],
        columns=[
            "title", "company", "location", "job_field", "work_type", "salary",
            "requirement", "posted", "image", "link", "kategori",
        ],
    )
    df["date_posted"] = date_posted_str

    # Cleanup + level inference
    def clean_noise(s):
        if is_noise(s, 200):
            return ""
        return s

    for col in ["company", "location", "job_field", "work_type", "salary"]:
        df[col] = df[col].apply(lambda x: clean_noise(x))

    df["level"] = df["title"].apply(infer_level)

    # Save Excel
    date_scrape = datetime.date.today().strftime("%Y-%m-%d")
    out_path = f"data_csv/jobs_data_jobstreet({date_scrape} {len(df.index)}).xlsx"

    df_for_csv = df.copy()
    df_for_csv = df_for_csv.replace(r"\t|\r", "", regex=True)
    df_for_csv["requirement"] = df_for_csv["requirement"].replace(r"\s{3,}", "  ", regex=True)

    try:
        df_for_csv.to_excel(out_path, index=False)
        print(f"[OK] Tersimpan: {out_path}")
    except Exception as e:
        print(f"[WARN] Gagal simpan Excel: {e}")

    # ---- save to DB (optional) ----
    try:
        import db_mysql  # local import
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
    # Tanpa batas jumlah, tanpa batas halaman/keyword
    scrapeData("public.scrape_items", max_jobs=None, max_pages_per_kw=None)
