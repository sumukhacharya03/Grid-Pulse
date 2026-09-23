import csv
import os
import sys

# Reads the output of scraper.py from stdin; run using "python scraper.py | python output.py"
data = sys.stdin.read()
lines = data.splitlines()

# To put all these values in csv file, we need it in the form of list of tuples like [(driver_name,baseline_value)..]
result = []
driver_name = None
baseline_value = None

for line in lines:
    if line.startswith("Driver Name:"):
        driver_name = line.replace("Driver Name:", "").strip()
    elif line.startswith("Baseline Value:"):
        baseline_value = line.replace("Baseline Value:", "").strip()
    elif line.startswith("---"):
        if driver_name and baseline_value:
            result.append((driver_name, baseline_value))
        driver_name = None
        baseline_value = None

if driver_name and baseline_value:
    result.append((driver_name, baseline_value))

if not result:
    sys.exit("No drivers found on stdin; run: python scraper.py | python output.py")

# Always written next to this script (it used to land in whatever directory
# you ran it from, so producer1.py never saw the update).
csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "drivers_baseline_value.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["Driver Name", "Baseline Value"])
    writer.writerows(result)

print(f"CSV File of Drivers Baseline Value successfully created at {csv_path}")
