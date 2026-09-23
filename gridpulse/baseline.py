"""Reading driver baseline values ("$78 M", "$0.375 M", "1500000", ...)."""
import csv

from . import roster
from .config import BASELINE_CSV


def parse_money(text):
    s = str(text).strip().replace("$", "").replace(",", "").replace(" ", "").upper()
    multiplier = 1
    if s.endswith("B"):
        multiplier, s = 1_000_000_000, s[:-1]
    elif s.endswith("M"):
        multiplier, s = 1_000_000, s[:-1]
    elif s.endswith("K"):
        multiplier, s = 1_000, s[:-1]
    return float(s) * multiplier


def read_baselines(path=BASELINE_CSV):
    """Returns ({code: (name, value)}, [problems])."""
    baselines, problems = {}, []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = (row.get("Driver Name") or "").strip()
            code = roster.code_for_name(name)
            if code is None:
                problems.append(f"Unknown driver '{name}'")
                continue
            try:
                baselines[code] = (roster.DRIVERS[code]["name"], parse_money(row["Baseline Value"]))
            except (KeyError, ValueError) as e:
                problems.append(f"Bad value for {name}: {e}")
    return baselines, problems
