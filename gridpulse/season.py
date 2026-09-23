"""The 2025 season calendar and session formats.

Rounds 1-14 ship as pre-generated historical data; rounds 15-24 are the
"live" part of the season that the real-time pipeline simulates."""
from datetime import datetime, timedelta, timezone

SEASON = 2025
HISTORICAL_ROUNDS = 14

# name must match the raceName used in the generated data.
RACES = [
    # round, name, short, country, circuit, first day, sprint, base lap (s), laps
    (1, "Australian Grand Prix", "Australia", "AUS", "Albert Park", "2025-03-14", False, 75.25, 58),
    (2, "Chinese Grand Prix", "China", "CHN", "Shanghai", "2025-03-21", True, 90.25, 56),
    (3, "Japanese Grand Prix", "Japan", "JPN", "Suzuka", "2025-04-04", False, 87.00, 53),
    (4, "Bahrain Grand Prix", "Bahrain", "BHR", "Sakhir", "2025-04-11", False, 90.00, 57),
    (5, "Saudi Arabia Grand Prix", "Saudi Arabia", "KSA", "Jeddah", "2025-04-18", False, 87.50, 50),
    (6, "Miami Grand Prix", "Miami", "USA", "Miami", "2025-05-02", True, 86.25, 57),
    (7, "Emilia-Romagna Grand Prix", "Imola", "ITA", "Imola", "2025-05-16", False, 74.75, 63),
    (8, "Monaco Grand Prix", "Monaco", "MON", "Monte Carlo", "2025-05-23", False, 70.00, 78),
    (9, "Spanish Grand Prix", "Spain", "ESP", "Barcelona", "2025-05-30", False, 71.60, 66),
    (10, "Canada Grand Prix", "Canada", "CAN", "Montreal", "2025-06-13", False, 71.00, 70),
    (11, "Austrian Grand Prix", "Austria", "AUT", "Spielberg", "2025-06-27", False, 64.00, 71),
    (12, "British Grand Prix", "Britain", "GBR", "Silverstone", "2025-07-04", False, 85.00, 52),
    (13, "Belgium Grand Prix", "Belgium", "BEL", "Spa", "2025-07-25", True, 100.25, 44),
    (14, "Hungarian Grand Prix", "Hungary", "HUN", "Hungaroring", "2025-08-01", False, 75.00, 70),
    (15, "Dutch Grand Prix", "Netherlands", "NED", "Zandvoort", "2025-08-29", False, 70.50, 72),
    (16, "Italian Grand Prix", "Italy", "ITA", "Monza", "2025-09-05", False, 79.50, 53),
    (17, "Azerbaijan Grand Prix", "Azerbaijan", "AZE", "Baku", "2025-09-19", False, 101.50, 51),
    (18, "Singapore Grand Prix", "Singapore", "SGP", "Marina Bay", "2025-10-03", False, 89.50, 62),
    (19, "United States Grand Prix", "Austin", "USA", "COTA", "2025-10-17", True, 92.50, 56),
    (20, "Mexican Grand Prix", "Mexico", "MEX", "Hermanos Rodriguez", "2025-10-24", False, 75.60, 71),
    (21, "Brazilian Grand Prix", "Brazil", "BRA", "Interlagos", "2025-11-07", True, 69.50, 71),
    (22, "Las Vegas Grand Prix", "Las Vegas", "USA", "Las Vegas Strip", "2025-11-20", False, 92.50, 50),
    (23, "Qatar Grand Prix", "Qatar", "QAT", "Lusail", "2025-11-28", True, 80.00, 57),
    (24, "Abu Dhabi Grand Prix", "Abu Dhabi", "UAE", "Yas Marina", "2025-12-05", False, 82.50, 58),
]

# key, display name, kind, day of weekend (0-2), start time
STANDARD_FORMAT = [
    ("practice1", "Practice 1", "practice", 0, "11:30"),
    ("practice2", "Practice 2", "practice", 0, "15:00"),
    ("practice3", "Practice 3", "practice", 1, "10:30"),
    ("qualifying", "Qualifying", "qualifying", 1, "14:00"),
    ("race", "Race", "race", 2, "13:00"),
]
SPRINT_FORMAT = [
    ("practice1", "Practice 1", "practice", 0, "10:30"),
    ("sprint_qualifying", "Sprint Qualifying", "sprint_qualifying", 0, "14:30"),
    ("sprint_race", "Sprint", "sprint", 1, "10:00"),
    ("qualifying", "Qualifying", "qualifying", 1, "14:00"),
    ("race", "Race", "race", 2, "13:00"),
]

# Accept the display names the old real-time generator emitted too.
_SESSION_ALIASES = {
    "practice 1": "practice1", "practice 2": "practice2", "practice 3": "practice3",
    "sprint qualifying": "sprint_qualifying", "sprint": "sprint_race",
    "sprint race": "sprint_race",
}
SESSION_KIND = {key: kind for key, _, kind, _, _ in STANDARD_FORMAT + SPRINT_FORMAT}
SESSION_NAME = {key: name for key, name, _, _, _ in STANDARD_FORMAT + SPRINT_FORMAT}
# Chronological order of sessions inside a weekend (sprint and standard).
SESSION_ORDER = {"practice1": 0, "practice2": 1, "sprint_qualifying": 2, "practice3": 3,
                 "sprint_race": 4, "qualifying": 5, "race": 6}


class Race:
    def __init__(self, round_number, name, short, country, circuit, start, sprint, base_lap, laps):
        self.round = round_number
        self.name = name
        self.short = short
        self.country = country
        self.circuit = circuit
        self.start = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        self.sprint = sprint
        self.base_lap = base_lap
        self.laps = laps

    @property
    def dates(self):
        return [(self.start + timedelta(days=i)).date().isoformat() for i in range(3)]

    @property
    def sessions(self):
        return SPRINT_FORMAT if self.sprint else STANDARD_FORMAT

    @property
    def is_historical(self):
        return self.round <= HISTORICAL_ROUNDS

    def sessions_on_day(self, day_index):
        return [s for s in self.sessions if s[3] == day_index]

    def session_timestamp(self, session_key):
        for key, _, _, day, start in self.sessions:
            if key == session_key:
                hour, minute = map(int, start.split(":"))
                moment = self.start + timedelta(days=day, hours=hour, minutes=minute)
                return int(moment.timestamp())
        raise KeyError(f"{self.name} has no session '{session_key}'")

    def payload(self):
        return {
            "round": self.round, "name": self.name, "short": self.short,
            "country": self.country, "circuit": self.circuit, "dates": self.dates,
            "sprint": self.sprint, "historical": self.is_historical,
            "sessions": [{"key": k, "name": n, "kind": kind, "ts": self.session_timestamp(k)}
                         for k, n, kind, _, _ in self.sessions],
        }


CALENDAR = [Race(*r) for r in RACES]
BY_NAME = {r.name: r for r in CALENDAR}
BY_ROUND = {r.round: r for r in CALENDAR}


def race_by_name(name):
    race = BY_NAME.get(name)
    if race is None:
        raise KeyError(f"Unknown race '{name}'. Known races: {', '.join(BY_NAME)}")
    return race


def race_on_date(date_str):
    for race in CALENDAR:
        if date_str in race.dates:
            return race, race.dates.index(date_str)
    return None, None


def normalize_session(session_type):
    """Map any session label ('practice1', 'Practice 1', 'Sprint', ...) to its key."""
    s = (session_type or "").strip().lower()
    s = _SESSION_ALIASES.get(s, s)
    if s not in SESSION_KIND:
        raise ValueError(f"Unknown session type '{session_type}'")
    return s
