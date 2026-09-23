import fastf1
session = fastf1.get_session(2025, 'Bahrain', 'R')
session.load()
results = session.results  # full race result DataFrame
laps = session.laps        # every lap from every driver