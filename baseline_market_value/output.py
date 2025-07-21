import sys

# Uploading the output from the scraper.py into data variable; run using "python scraper.py | python output.py"
data=sys.stdin.read()
# print("Output from Scraper:",data)

# Since data will be a string, we will convert into list of strings
lines=data.splitlines()
# print(lines)

# To put all these values in csv file, we need it in the form of list of tuples like [(driver_name,baseline_value)..]
result=[]
driver_name=None
baseline_value=None

for line in lines:
    if line.startswith("Driver Name:"):
        driver_name=line.replace("Driver Name:","").strip()
    elif line.startswith("Baseline Value:"):
        baseline_value=line.replace("Baseline Value:","").strip()
    elif line.startswith("---"):
        if driver_name and baseline_value:
            result.append((driver_name,baseline_value))
        driver_name=None
        baseline_value=None
    
if driver_name and baseline_value:
    result.append((driver_name,baseline_value))

# print(result)

# Putting driver name and baseline value in a csv file
import csv

with open('drivers_baseline_value.csv','w') as csvfile:
    writer=csv.writer(csvfile)
    writer.writerow(['Driver Name','Baseline Value'])
    writer.writerows(result)

print("CSV File of Drivers Baseline Value succesfully created")
