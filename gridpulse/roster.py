"""The 2025 grid: one source of truth for driver codes, names, teams and the
performance tier the simulator uses. Previously this lived (and drifted) in
four different files."""

TEAMS = {
    "Red Bull": {"name": "Red Bull Racing", "color": "#3671C6"},
    "Ferrari": {"name": "Scuderia Ferrari", "color": "#E8002D"},
    "McLaren": {"name": "McLaren", "color": "#FF8000"},
    "Mercedes": {"name": "Mercedes-AMG", "color": "#27F4D2"},
    "Aston Martin": {"name": "Aston Martin", "color": "#229971"},
    "Alpine": {"name": "Alpine", "color": "#FF87BC"},
    "Williams": {"name": "Williams", "color": "#64C4FF"},
    "RB": {"name": "Racing Bulls", "color": "#6692FF"},
    "Sauber": {"name": "Kick Sauber", "color": "#52E252"},
    "Haas": {"name": "Haas", "color": "#B6BABD"},
}

# tier: 1 = front-runner, 2 = midfield, 3 = rookie / backmarker.
# first_round / last_round bound when the driver is on the grid.
DRIVERS = {
    "VER": {"name": "Max Verstappen", "number": 1, "country": "NED", "team": "Red Bull", "tier": 1},
    "LAW": {"name": "Liam Lawson", "number": 30, "country": "NZL", "team": "Red Bull", "tier": 3},
    "LEC": {"name": "Charles Leclerc", "number": 16, "country": "MON", "team": "Ferrari", "tier": 1},
    "HAM": {"name": "Lewis Hamilton", "number": 44, "country": "GBR", "team": "Ferrari", "tier": 1},
    "NOR": {"name": "Lando Norris", "number": 4, "country": "GBR", "team": "McLaren", "tier": 1},
    "PIA": {"name": "Oscar Piastri", "number": 81, "country": "AUS", "team": "McLaren", "tier": 1},
    "RUS": {"name": "George Russell", "number": 63, "country": "GBR", "team": "Mercedes", "tier": 1},
    "ANT": {"name": "Kimi Antonelli", "number": 12, "country": "ITA", "team": "Mercedes", "tier": 3},
    "ALO": {"name": "Fernando Alonso", "number": 14, "country": "ESP", "team": "Aston Martin", "tier": 2},
    "STR": {"name": "Lance Stroll", "number": 18, "country": "CAN", "team": "Aston Martin", "tier": 2},
    "GAS": {"name": "Pierre Gasly", "number": 10, "country": "FRA", "team": "Alpine", "tier": 2},
    "DOO": {"name": "Jack Doohan", "number": 7, "country": "AUS", "team": "Alpine", "tier": 3, "last_round": 6},
    "COL": {"name": "Franco Colapinto", "number": 43, "country": "ARG", "team": "Alpine", "tier": 3, "first_round": 7},
    "ALB": {"name": "Alex Albon", "number": 23, "country": "THA", "team": "Williams", "tier": 2},
    "SAI": {"name": "Carlos Sainz", "number": 55, "country": "ESP", "team": "Williams", "tier": 2},
    "TSU": {"name": "Yuki Tsunoda", "number": 22, "country": "JPN", "team": "RB", "tier": 2},
    "HAD": {"name": "Isack Hadjar", "number": 6, "country": "FRA", "team": "RB", "tier": 3},
    "HUL": {"name": "Nico Hulkenberg", "number": 27, "country": "GER", "team": "Sauber", "tier": 2},
    "BOR": {"name": "Gabriel Bortoleto", "number": 5, "country": "BRA", "team": "Sauber", "tier": 3},
    "OCO": {"name": "Esteban Ocon", "number": 31, "country": "FRA", "team": "Haas", "tier": 2},
    "BEA": {"name": "Ollie Bearman", "number": 87, "country": "GBR", "team": "Haas", "tier": 3},
}

# Tsunoda and Lawson swapped seats from round 3 (Japan).
TEAM_SWAPS = {3: {"TSU": "Red Bull", "LAW": "RB"}}

NAME_TO_CODE = {d["name"]: code for code, d in DRIVERS.items()}
# Spellings seen in scraped / hand-edited data.
NAME_ALIASES = {"Esteben Ocon": "OCO", "Alexander Albon": "ALB", "Andrea Kimi Antonelli": "ANT",
                "Oliver Bearman": "BEA", "Nico Hülkenberg": "HUL"}

FINAL_ROUND = 10 ** 6


def code_for_name(name):
    if not name:
        return None
    name = name.strip()
    return NAME_TO_CODE.get(name) or NAME_ALIASES.get(name)


def is_active(code, round_number):
    d = DRIVERS[code]
    return d.get("first_round", 1) <= round_number <= d.get("last_round", FINAL_ROUND)


def team_for_round(code, round_number):
    team = DRIVERS[code]["team"]
    for start, swaps in sorted(TEAM_SWAPS.items()):
        if round_number >= start and code in swaps:
            team = swaps[code]
    return team


def current_team(code):
    return team_for_round(code, FINAL_ROUND)


def drivers_for_round(round_number):
    """The field for a given round, in the shape the simulator expects."""
    return [
        {"code": code, "team": team_for_round(code, round_number), "tier": d["tier"]}
        for code, d in DRIVERS.items()
        if is_active(code, round_number)
    ]


def roster_payload():
    """Driver + team metadata for the dashboard."""
    return {
        "drivers": {
            code: {
                "code": code,
                "name": d["name"],
                "number": d["number"],
                "country": d["country"],
                "team": current_team(code),
                "active": is_active(code, FINAL_ROUND),
            }
            for code, d in DRIVERS.items()
        },
        "teams": TEAMS,
    }
