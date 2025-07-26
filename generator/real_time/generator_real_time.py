import time
import json
import random
import os
import uuid
import sys
from datetime import datetime

QUEUE_DIRECTORY = os.path.join(os.path.dirname(__file__), 'live_events_queue')

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

SPRINT_WEEKENDS = ["United States Grand Prix", "Brazilian Grand Prix", "Qatar Grand Prix"]

MASTER_DRIVER_LIST = {
    'VER': {'code': 'VER', 'team': 'Red Bull', 'tier': 1}, 
    'LEC': {'code': 'LEC', 'team': 'Ferrari', 'tier': 1}, 
    'HAM': {'code': 'HAM', 'team': 'Ferrari', 'tier': 1}, 
    'NOR': {'code': 'NOR', 'team': 'McLaren', 'tier': 1}, 
    'PIA': {'code': 'PIA', 'team': 'McLaren', 'tier': 1}, 
    'RUS': {'code': 'RUS', 'team': 'Mercedes', 'tier': 2}, 
    'ANT': {'code': 'ANT', 'team': 'Mercedes', 'tier': 3}, 
    'ALO': {'code': 'ALO', 'team': 'Aston Martin', 'tier': 2}, 
    'STR': {'code': 'STR', 'team': 'Aston Martin', 'tier': 2}, 
    'GAS': {'code': 'GAS', 'team': 'Alpine', 'tier': 2}, 
    'DOO': {'code': 'DOO', 'team': 'Alpine', 'tier': 3}, 
    'ALB': {'code': 'ALB', 'team': 'Williams', 'tier': 2}, 
    'SAI': {'code': 'SAI', 'team': 'Williams', 'tier': 2}, 
    'TSU': {'code': 'TSU', 'team': 'RB', 'tier': 2}, 
    'LAW': {'code': 'LAW', 'team': 'Red Bull', 'tier': 3}, 
    'HAD': {'code': 'HAD', 'team': 'RB', 'tier': 3}, 
    'HUL': {'code': 'HUL', 'team': 'Sauber', 'tier': 2}, 
    'BOR': {'code': 'BOR', 'team': 'Sauber', 'tier': 3},
    'OCO': {'code': 'OCO', 'team': 'Haas', 'tier': 2}, 
    'BEA': {'code': 'BEA', 'team': 'Haas', 'tier': 3},
    'COL': {'code': 'COL', 'team': 'Alpine', 'tier': 3}
}

def get_drivers_for_round(round_number):
    lineup = {
        'VER': MASTER_DRIVER_LIST['VER'].copy(), 
        'LAW': MASTER_DRIVER_LIST['LAW'].copy(), 
        'LEC': MASTER_DRIVER_LIST['LEC'].copy(),
        'HAM': MASTER_DRIVER_LIST['HAM'].copy(), 
        'NOR': MASTER_DRIVER_LIST['NOR'].copy(), 
        'PIA': MASTER_DRIVER_LIST['PIA'].copy(),
        'RUS': MASTER_DRIVER_LIST['RUS'].copy(), 
        'ANT': MASTER_DRIVER_LIST['ANT'].copy(), 
        'ALO': MASTER_DRIVER_LIST['ALO'].copy(),
        'STR': MASTER_DRIVER_LIST['STR'].copy(), 
        'GAS': MASTER_DRIVER_LIST['GAS'].copy(), 
        'DOO': MASTER_DRIVER_LIST['DOO'].copy(),
        'ALB': MASTER_DRIVER_LIST['ALB'].copy(), 
        'SAI': MASTER_DRIVER_LIST['SAI'].copy(), 
        'TSU': MASTER_DRIVER_LIST['TSU'].copy(),
        'HAD': MASTER_DRIVER_LIST['HAD'].copy(), 
        'HUL': MASTER_DRIVER_LIST['HUL'].copy(), 
        'BOR': MASTER_DRIVER_LIST['BOR'].copy(),
        'OCO': MASTER_DRIVER_LIST['OCO'].copy(), 
        'BEA': MASTER_DRIVER_LIST['BEA'].copy(),
    }
    if round_number >= 3:
        lineup['TSU']['team'] = 'Red Bull'; lineup['LAW']['team'] = 'RB'
    if round_number >= 7:
        if 'DOO' in lineup: 
            del lineup['DOO']
        lineup['COL'] = MASTER_DRIVER_LIST['COL'].copy()
    return list(lineup.values())

def generate_lap_time(previous_seconds, tier_diff):
    delta = random.uniform(0.020, 0.350) + (tier_diff * 0.05)
    new_seconds = previous_seconds + delta
    minutes = int(new_seconds // 60)
    seconds = new_seconds % 60
    return f"{minutes}:{seconds:06.3f}", new_seconds

def simulate_timed_session(drivers, track_info, base_lap_seconds, session_type="practice"):
    results = []
    tiers = {1: [], 2: [], 3: []}
    for d in drivers:
        if d['tier'] in tiers: tiers[d['tier']].append(d)
    [random.shuffle(t) for t in tiers.values()]
    final_order = tiers.get(1, []) + tiers.get(2, []) + tiers.get(3, [])
    last_lap_seconds = track_info['base_minutes'] * 60 + base_lap_seconds
    for i, driver in enumerate(final_order):
        tier_difference = driver['tier'] - final_order[i-1]['tier'] if i > 0 else 0
        time_str, last_lap_seconds = generate_lap_time(last_lap_seconds, tier_difference)
        result = {"position": i + 1, "driverCode": driver['code'], "team": driver['team']}
        time_key = "fastest_time" if "practice" in session_type.lower() else "time"
        result[time_key] = time_str
        if "practice" in session_type.lower(): result["fastestLap"] = False
        results.append(result)
    if "practice" in session_type.lower() and results:
        results[0]['fastestLap'] = True
    return results

def run_realistic_race_simulation(starting_grid, drivers, track_info, is_sprint=False):
    driver_map = {d['code']: d for d in drivers}
    race_data = {}
    for i, driver_code in enumerate(starting_grid):
        race_data[driver_code] = { "driverCode": driver_code, "team": driver_map[driver_code]['team'], "startingPosition": i + 1, "finishingPosition": None, "overtakes": 0, "positionsLost": 0, "overtakesWithDRS": 0, "overtakesWithoutDRS": 0, "crashes": 0, "collisions": 0, "pitstops": [], "status": "Finished", "fastestLap": False, "points": 0 }
    finishing_order = list(starting_grid)
    num_dnfs = random.randint(0, 2) if is_sprint else random.randint(1, 4)
    dnf_events = []
    for _ in range(num_dnfs):
        if len(finishing_order) < 2: break
        dnf_type = random.choice(["Collision", "Crash", "Mechanical"])
        dnf_lap = random.randint(1, track_info['laps'] - 5)
        if dnf_type == "Collision" and len(finishing_order) >= 2:
            d1_idx = random.randint(0, len(finishing_order) - 2)
            d1_code, d2_code = finishing_order[d1_idx], finishing_order[d1_idx + 1]
            dnf_events.append({'type': dnf_type, 'lap': dnf_lap, 'drivers': [d1_code, d2_code]})
            if d1_code in finishing_order: finishing_order.remove(d1_code)
            if d2_code in finishing_order: finishing_order.remove(d2_code)
        else:
            driver_to_retire = random.choice(finishing_order)
            dnf_events.append({'type': dnf_type, 'lap': dnf_lap, 'drivers': [driver_to_retire]})
            finishing_order.remove(driver_to_retire)
    for event in dnf_events:
        if event['type'] == 'Collision':
            d1, d2 = event['drivers']
            race_data[d1]['status'] = f"Collision with {d2}"; race_data[d1]['collisions'] = 1; race_data[d1]['dnf_lap'] = event['lap']
            race_data[d2]['status'] = f"Collision with {d1}"; race_data[d2]['collisions'] = 1; race_data[d2]['dnf_lap'] = event['lap']
        else:
            driver = event['drivers'][0]
            race_data[driver]['status'] = "Crashed" if event['type'] == "Crash" else "Mechanical Failure"
            if event['type'] == 'Crash': race_data[driver]['crashes'] = 1
            race_data[driver]['dnf_lap'] = event['lap']
    num_race_events = 25 if is_sprint else 70
    for _ in range(num_race_events):
        if len(finishing_order) < 2: break
        attacker_pos = random.randint(1, len(finishing_order) - 1)
        defender_pos = attacker_pos - 1
        attacker_code, defender_code = finishing_order[attacker_pos], finishing_order[defender_pos]
        attacker_tier, defender_tier = driver_map[attacker_code]['tier'], driver_map[defender_code]['tier']
        overtake_chance = 0.60 if attacker_tier < defender_tier else (0.30 if attacker_tier == defender_tier else 0.05)
        if random.random() < overtake_chance:
            finishing_order[attacker_pos], finishing_order[defender_pos] = finishing_order[defender_pos], finishing_order[attacker_pos]
    for i, driver_code in enumerate(finishing_order):
        race_data[driver_code]['finishingPosition'] = i + 1
        position_change = race_data[driver_code]['startingPosition'] - race_data[driver_code]['finishingPosition']
        if position_change > 0:
            race_data[driver_code]['overtakes'] = position_change; drs_overtakes = round(position_change * random.uniform(0.6, 0.8)); race_data[driver_code]['overtakesWithDRS'] = drs_overtakes; race_data[driver_code]['overtakesWithoutDRS'] = position_change - drs_overtakes
        else:
            race_data[driver_code]['positionsLost'] = abs(position_change)
    if is_sprint:
        sprint_points = [8, 7, 6, 5, 4, 3, 2, 1]
        for i, driver_code in enumerate(finishing_order):
            if i < len(sprint_points): race_data[driver_code]['points'] = sprint_points[i]
    else:
        race_points = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]
        for i, driver_code in enumerate(finishing_order):
            if i < len(race_points): race_data[driver_code]['points'] = race_points[i]
    num_safety_cars = random.randint(0, 2) if not is_sprint else 0
    if not is_sprint:
        for driver_code in finishing_order:
            pit_chance = 0.8 + (num_safety_cars * 0.1)
            if random.random() < pit_chance:
                for _ in range(random.randint(1, 2)): race_data[driver_code]['pitstops'].append(round(random.uniform(2.1, 4.5), 2))
        if finishing_order:
            fastest_lap_driver = random.choice(finishing_order[:10])
            race_data[fastest_lap_driver]['fastestLap'] = True
            if race_data[fastest_lap_driver].get('finishingPosition', 99) <= 10:
                race_data[fastest_lap_driver]['points'] += 1
    final_results = sorted([v for v in race_data.values() if v['finishingPosition'] is not None], key=lambda x: x['finishingPosition'])
    dnf_results = [v for v in race_data.values() if v['finishingPosition'] is None]
    return final_results + dnf_results, {"yellow_flags": random.randint(2,6), "safety_cars": num_safety_cars, "red_flags": 1 if random.random() < 0.1 else 0}

def generate_day_specific_files():
    if len(sys.argv) < 3:
        print("Error: Missing arguments. Usage: python live_event_generator.py <race_name> <date_str>")
        return
        
    race_name = sys.argv[1]
    today_str = sys.argv[2]
    
    print(f"Starting Live Day Generator for '{race_name}' on {today_str}...")
    if not os.path.exists(QUEUE_DIRECTORY):
        os.makedirs(QUEUE_DIRECTORY)

    try:
        weekend_dates = F1_SCHEDULE_2025[race_name]
        day_index = weekend_dates.index(today_str)
    except (KeyError, ValueError):
        print(f"Warning: Could not find '{race_name}' in live schedule. Assuming today is Day 1 for testing.")
        day_index = 0 

    standard_schedule = [["Practice 1", "Practice 2"], ["Practice 3", "Qualifying"], ["Race"]]
    sprint_schedule = [["Practice 1", "Sprint Qualifying"], ["Sprint", "Qualifying"], ["Race"]]
    
    is_sprint = race_name in SPRINT_WEEKENDS
    sessions_today = sprint_schedule[day_index] if is_sprint else standard_schedule[day_index]
    
    print(f"Today is Day {day_index + 1}. Simulating sessions: {', '.join(sessions_today)}")
    
    drivers_for_this_race = get_drivers_for_round(12) 
    track_info = {"base_minutes": 1, "base_seconds": 21.00, "laps": 53}

    for session_name in sessions_today:
        print(f"\nGeneration Session: {session_name}")
        time.sleep(3)
        results = []
        if "Practice" in session_name:
            base_seconds = track_info['base_seconds'] + random.uniform(1.0, 2.0)
            results = simulate_timed_session(drivers_for_this_race, track_info, base_seconds, session_name)
        elif "Qualifying" in session_name:
            base_seconds = track_info['base_seconds']
            if "Sprint" in session_name: base_seconds += 0.250
            results = simulate_timed_session(drivers_for_this_race, track_info, base_seconds, session_name)
        elif "Race" in session_name:
            is_sprint_race = "Sprint" in session_name
            quali_results = simulate_timed_session(drivers_for_this_race, track_info, track_info['base_seconds'], "qualifying")
            race_grid = [res['driverCode'] for res in quali_results]
            results, _ = run_realistic_race_simulation(race_grid, drivers_for_this_race, track_info, is_sprint=is_sprint_race)

        for result in results:
            result.update({'raceName': race_name, 'session_type': session_name})
            filename = f"{datetime.now().timestamp()}_{uuid.uuid4()}.json"
            filepath = os.path.join(QUEUE_DIRECTORY, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result, f)
            print(f"Generated file for {result['driverCode']} in {session_name}")
            time.sleep(random.uniform(0.5, 1.5))
        print(f"Session Generation Complete: {session_name}")
    
    print(f"\nAll sessions for {today_str} are complete. Generator is exiting.")

if __name__ == "__main__":
    generate_day_specific_files()
