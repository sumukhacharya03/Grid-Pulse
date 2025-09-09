import datetime
import subprocess
import sys
import os
import time

F1_SCHEDULE_2025 = {
    "Hungary Grand Prix": ["2025-08-01",'2025-08-02','2025-08-03'],
    "Dutch Grand Prix": ["2025-08-29", "2025-08-30", "2025-08-31"],
    "Italian Grand Prix": ["2025-09-05", "2025-09-06", "2025-09-07"],
    "Azerbaijan Grand Prix": ["2025-09-19", "2025-09-20", "2025-09-21"],
    "Singapore Grand Prix": ["2025-10-03", "2025-10-04", "2025-10-05"],
    "United States Grand Prix": ["2025-10-17", "2025-10-18", "2025-10-19"],
    "Mexican Grand Prix": ["2025-10-24", "2025-10-25", "2025-10-26"],
    "Brazilian Grand Prix": ["2025-11-07", "2025-11-08", "2025-11-09"],
    "Las Vegas Grand Prix": ["2025-11-20", "2025-11-21", "2025-11-22"],
    "Qatar Grand Prix": ["2025-11-28", "2025-11-29", "2025-11-30"],
    "Abu Dhabi Grand Prix": ["2025-12-05", "2025-12-06", "2025-12-07"]
}

def check_and_launch_simulator():
    today_str = datetime.date.today().isoformat()
    is_race_day = False
    current_race = None

    for race, dates in F1_SCHEDULE_2025.items():
        if today_str in dates:
            is_race_day = True
            current_race = race
            break
            
    if is_race_day:
        print(f"Today is part of the {current_race} weekend! Starting live simulator...")
        
        python_executable = sys.executable
        script_dir = os.path.dirname(os.path.realpath(__file__))
        
        generator_path = os.path.join(script_dir, 'generator_real_time.py')
        producer_path = os.path.join(script_dir, 'producer3.py')

        try:
            print("Launching the live producer in the background...")
            subprocess.Popen([python_executable, producer_path])
            
            time.sleep(5) 
            
            print(f"Launching the live generator for '{current_race}' on date {today_str}...")
            subprocess.Popen([python_executable, generator_path, current_race, today_str])

            print("Both live simulator processes launched successfully.")
        except Exception as e:
            print(f"Error launching simulator processes: {e}")
            
    else:
        print(f"Today ({today_str}) is not an F1 session day. No simulation started.")

if __name__ == "__main__":
    check_and_launch_simulator()
