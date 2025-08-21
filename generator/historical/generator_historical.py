import json
import random
import datetime
import os

# Output directory where all the Race JSON files get saved
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'generated_historical_results')

# Core Data
TRACK_CHARACTERISTICS = {
    "Australian Grand Prix": {"base_minutes": 1, "base_seconds": 15.25, "laps": 58},
    "Chinese Grand Prix": {"base_minutes": 1, "base_seconds": 30.25, "laps": 56},
    "Japanese Grand Prix": {"base_minutes": 1, "base_seconds": 27.00, "laps": 53},
    "Bahrain Grand Prix": {"base_minutes": 1, "base_seconds": 30.00, "laps": 57},
    "Saudi Arabia Grand Prix": {"base_minutes": 1, "base_seconds": 27.50, "laps": 50},
    "Miami Grand Prix": {"base_minutes": 1, "base_seconds": 26.25, "laps": 57},
    "Emilia-Romagna Grand Prix": {"base_minutes": 1, "base_seconds": 14.75, "laps": 63},
    "Monaco Grand Prix": {"base_minutes": 1, "base_seconds": 10.00, "laps": 78},
    "Spanish Grand Prix": {"base_minutes": 1, "base_seconds": 11.60, "laps": 66},
    "Canada Grand Prix": {"base_minutes": 1, "base_seconds": 11.00, "laps": 70},
    "Austrian Grand Prix": {"base_minutes": 1, "base_seconds": 4.00, "laps": 71},
    "British Grand Prix": {"base_minutes": 1, "base_seconds": 25.00, "laps": 52},
    "Belgium Grand Prix": {"base_minutes": 1, "base_seconds": 40.250, "laps": 44},
    "Hungarian Grand Prix": {"base_minutes": 1, "base_seconds": 15, "laps":70}
}
SPRINT_WEEKENDS = ["Chinese Grand Prix", "Miami Grand Prix", "Belgium Grand Prix"]

MASTER_DRIVER_LIST = {
    'VER': {'code': 'VER', 'team': 'Red Bull', 'tier': 1}, 
    'LEC': {'code': 'LEC', 'team': 'Ferrari', 'tier': 1}, 
    'HAM': {'code': 'HAM', 'team': 'Ferrari', 'tier': 1}, 
    'NOR': {'code': 'NOR', 'team': 'McLaren', 'tier': 1}, 
    'PIA': {'code': 'PIA', 'team': 'McLaren', 'tier': 1}, 
    'RUS': {'code': 'RUS', 'team': 'Mercedes', 'tier': 1}, 
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

RACE_SCHEDULE_2025 = list(TRACK_CHARACTERISTICS.keys())

# To handle the case of mid-season driver changes
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
        lineup['TSU']['team'] = 'Red Bull'; 
        lineup['LAW']['team'] = 'RB'
    if round_number >= 7:
        if 'DOO' in lineup: 
            del lineup['DOO']
        lineup['COL'] = MASTER_DRIVER_LIST['COL'].copy()
    return list(lineup.values())

# To generate realistic timings sheet, like to make sure P2 has a greater time than P1 and so on
def generate_lap_time(previous_seconds, tier_diff):
    delta = random.uniform(0.020, 0.350) + (tier_diff * 0.05)
    new_seconds = previous_seconds + delta
    minutes = int(new_seconds // 60)
    seconds = new_seconds % 60
    return f"{minutes}:{seconds:06.3f}", new_seconds

# To create the final ordered results for any session
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
        if "practice" in session_type.lower(): 
            result["fastestLap"] = False
        results.append(result)
        
    if "practice" in session_type.lower() and results:
        results[0]['fastestLap'] = True
    return results

# This is the main logic which simulates the entire race story
def run_realistic_race_simulation(starting_grid, drivers, track_info, is_sprint=False):
    driver_map = {d['code']: d for d in drivers}
    race_data = {}
    for i, driver_code in enumerate(starting_grid):
        race_data[driver_code] = { 
            "driverCode": driver_code, 
            "team": driver_map[driver_code]['team'], 
            "startingPosition": i + 1, 
            "finishingPosition": None, 
            "overtakes": 0, 
            "positionsLost": 0, 
            "overtakesWithDRS": 0, 
            "overtakesWithoutDRS": 0, 
            "crashes": 0, 
            "collisions": 0, 
            "pitstops": [], 
            "status": "Finished", 
            "fastestLap": False, 
            "points": 0 
            }

    finishing_order = list(starting_grid)
    num_dnfs = random.randint(0, 2) if is_sprint else random.randint(1, 4)
    dnf_events = []
    
    for _ in range(num_dnfs):
        if len(finishing_order) < 2: 
            break
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

# Main script which acts as the builder responsible for building the entire historical data
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

for i, race_name in enumerate(RACE_SCHEDULE_2025):
    round_number = i + 1
    drivers_for_this_race = get_drivers_for_round(round_number)
    track_info = TRACK_CHARACTERISTICS[race_name]
    weekend_data = {"season": 2025, "round": round_number, "raceName": race_name}
    if race_name in SPRINT_WEEKENDS:
        practice_base_seconds = track_info['base_seconds'] + random.uniform(1.0, 2.0)
        sprint_quali_base_seconds = track_info['base_seconds'] + 0.250
        weekend_data["practice1Results"] = simulate_timed_session(drivers_for_this_race, track_info, practice_base_seconds, "practice1")
        sprint_quali_results = simulate_timed_session(drivers_for_this_race, track_info, sprint_quali_base_seconds, "qualifying")
        weekend_data["sprintQualifyingResults"] = sprint_quali_results
        sprint_grid = [res['driverCode'] for res in sprint_quali_results]
        weekend_data["sprintRaceResults"], weekend_data["sprintRaceEvents"] = run_realistic_race_simulation(sprint_grid, drivers_for_this_race, track_info, is_sprint=True)
        qualifying_results = simulate_timed_session(drivers_for_this_race, track_info, track_info['base_seconds'], "qualifying")
        weekend_data["qualifyingResults"] = qualifying_results
        main_race_grid = [res['driverCode'] for res in qualifying_results]
        weekend_data["raceResults"], weekend_data["raceEvents"] = run_realistic_race_simulation(main_race_grid, drivers_for_this_race, track_info, is_sprint=False)
    else:
        practice_base_seconds = track_info['base_seconds'] + random.uniform(1.0, 2.0)
        weekend_data["practice1Results"] = simulate_timed_session(drivers_for_this_race, track_info, practice_base_seconds, "practice1")
        weekend_data["practice2Results"] = simulate_timed_session(drivers_for_this_race, track_info, practice_base_seconds, "practice2")
        weekend_data["practice3Results"] = simulate_timed_session(drivers_for_this_race, track_info, practice_base_seconds, "practice3")
        qualifying_results = simulate_timed_session(drivers_for_this_race, track_info, track_info['base_seconds'], "qualifying")
        weekend_data["qualifyingResults"] = qualifying_results
        main_race_grid = [res['driverCode'] for res in qualifying_results]
        weekend_data["raceResults"], weekend_data["raceEvents"] = run_realistic_race_simulation(main_race_grid, drivers_for_this_race, track_info, is_sprint=False)
    filename = f"{race_name.lower().replace(' ', '_')}.json"
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(weekend_data, f, indent=2)
    print(f"Saved Results to {filepath}")
print("Generated all Races Historical Data")
