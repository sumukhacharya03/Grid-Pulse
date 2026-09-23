import requests
from bs4 import BeautifulSoup

# Scrapes each driver's Salary/Winnings + Endorsements from their Forbes
# profile. Drivers without a profile use a hand-set estimate. Run using
# "python scraper.py | python output.py" to write the CSV.

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}

# (driver, Forbes profile slug or None, fallback value in $M)
# Fallbacks are the values scraped in Sept 2025, used when Forbes is
# unreachable or blocks the request.
DRIVERS = [
    ("Max Verstappen", "max-verstappen", 78),
    ("Lewis Hamilton", "lewis-hamilton", 80),
    ("Oscar Piastri", "oscar-piastri", 22),
    ("Lando Norris", "lando-norris", 35),
    ("Charles Leclerc", "charles-leclerc", 27),
    ("Fernando Alonso", "fernando-alonso", 27.5),
    ("George Russell", "george-russell-1", 23),
    ("Pierre Gasly", "pierre-gasly", 12),
    ("Carlos Sainz", "carlos-sainz", 19),
    ("Kimi Antonelli", None, 2),  # Rookie
    ("Ollie Bearman", None, 0.75),  # Rookie
    ("Gabriel Bortoleto", None, 1),  # Rookie
    ("Jack Doohan", None, 1),  # 2nd year Driver
    ("Franco Colapinto", None, 0.75),  # 2nd year Driver
    ("Yuki Tsunoda", None, 0.75),  # Experienced Driver
    ("Liam Lawson", None, 0.375),  # 2nd year Driver
    ("Isack Hadjar", None, 0.375),  # Rookie
    ("Lance Stroll", None, 2),  # Experienced Driver
    ("Nico Hulkenberg", None, 7),  # Experienced Driver
    ("Esteban Ocon", None, 6),  # Experienced Driver
    ("Alex Albon", None, 3),  # Experienced Driver
]


# Fetches the page once per driver (it used to be downloaded three times)
def fetch_profile(slug):
    try:
        response = requests.get(f"https://www.forbes.com/profile/{slug}/", headers=HEADERS, timeout=15)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except requests.RequestException as e:
        print(f"# Could not fetch Forbes profile '{slug}': {e}")
        return None


# This function is used to extract the drivers particular details like Salary etc.
def get_details(soup, target_detail):
    for dt in soup.find_all("dt"):
        if target_detail in dt.get_text():
            dd = dt.find_next_sibling("dd")
            return dd.get_text(strip=True) if dd else None
    return None


def to_millions(text):
    # "$27.5 M" -> 27.5 (keeps the decimals int() used to drop)
    if not text:
        return 0.0
    return float(text.replace(" ", "").replace("$", "").split("M")[0])


for driver, slug, fallback in DRIVERS:
    salary = endorsements = None
    soup = fetch_profile(slug) if slug else None
    if soup is not None:
        salary = get_details(soup, "Salary/Winnings")
        endorsements = get_details(soup, "Endorsements")
    total = to_millions(salary) + to_millions(endorsements) if salary else fallback

    print("Driver Name:", driver)
    if slug:
        print("Salary/Winnings:", salary)
        print("Endorsements:", endorsements)
    print(f"Baseline Value: ${total:g} M")
    print("-" * 50)
