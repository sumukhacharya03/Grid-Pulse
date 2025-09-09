import streamlit as st
import json
import pandas as pd
from kafka import KafkaConsumer
from datetime import datetime
import time
import threading
import uuid
import base64
import os

KAFKA_BROKER = 'localhost:9092'
STOCK_VALUES_TOPIC = 'driver-stock-values'

drivers_data = {}
data_lock = threading.Lock()
initial_load_complete = threading.Event()

def get_image_as_base64(driver_code):
    image_path = os.path.join('assets', f'{driver_code}.jpg')
    if not os.path.exists(image_path):
        return "https://placehold.co/100x100/808080/FFFFFF?text=N/A"

    with open(image_path, "rb") as image_file:
        return f"data:image/jpeg;base64,{base64.b64encode(image_file.read()).decode()}"

def kafka_consumer_thread():
    print("Dashboard consumer thread started...")
    try:
        consumer = KafkaConsumer(
            STOCK_VALUES_TOPIC,
            bootstrap_servers=KAFKA_BROKER,
            auto_offset_reset='earliest',
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            group_id=f'dashboard-consumer-{uuid.uuid4()}'
        )
        print("Dashboard consumer connected. Reading final stock values...")

        for message in consumer:
            data = message.value
            driver_code = data.get('driver_code')
            if driver_code:
                with data_lock:
                    data['image_url'] = get_image_as_base64(driver_code)
                    drivers_data[driver_code] = data

            if len(drivers_data) >= 20 and not initial_load_complete.is_set():
                print("Initial stock values fully loaded.")
                initial_load_complete.set()

    except Exception as e:
        print(f"CRITICAL ERROR in dashboard consumer thread: {e}")

def main():
    st.set_page_config(page_title="GridPulse F1 Stock Market", layout="wide")

    st.markdown("""
        <style>
            .st-emotion-cache-18ni7ap {
                font-size: 2.5rem;
                font-weight: bold;
            }
            .st-emotion-cache-1g6gooi {
                font-size: 1.1rem;
                color: #A0A0A0;
            }
            .st-emotion-cache-1ht1j8u {
                font-size: 2rem;
                font-weight: bold;
            }
            .driver-card {
                background-color: #1E1E1E;
                border-radius: 10px;
                padding: 15px;
                margin: 10px 0;
                border: 1px solid #333;
                display: flex;
                align-items: center;
                transition: transform 0.2s;
            }
            .driver-card:hover {
                transform: scale(1.02);
                border-color: #00D2BE;
            }
            .driver-image {
                width: 75px;
                height: 75px;
                border-radius: 50%;
                margin-right: 15px;
                object-fit: cover;
            }
            .driver-info {
                flex-grow: 1;
            }
            .driver-name {
                font-size: 1.5rem;
                font-weight: bold;
                margin: 0;
            }
            .driver-value {
                font-size: 1.75rem;
                margin: 0;
            }
            .driver-change {
                font-size: 1.2rem;
                margin: 0;
            }
            .positive { color: #2ECC71; }
            .negative { color: #E74C3C; }
        </style>
    """, unsafe_allow_html=True)

    st.title("GridPulse F1 Stock Market")

    if 'consumer_thread_started' not in st.session_state:
        thread = threading.Thread(target=kafka_consumer_thread, daemon=True)
        thread.start()
        st.session_state['consumer_thread_started'] = True

    if not initial_load_complete.wait(timeout=30):
        st.error(
            "Data load timed out. Please run the `calculation_service.py` script and ensure it completes successfully.")
        return

    placeholder = st.empty()

    while True:
        with data_lock:
            df = pd.DataFrame.from_dict(drivers_data, orient='index')

        df['change'] = df['current_value'] - df['baseline_value']
        df['change_pct'] = (df['change'] / df['baseline_value']) * 100
        df = df.sort_values(by='current_value', ascending=False)

        with placeholder.container():
            st.subheader(f"Market Snapshot (Live Update: {datetime.now().strftime('%H:%M:%S')})")
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Market Cap", f"${df['current_value'].sum():,.2f}")
            top_gainer = df.loc[df['change_pct'].idxmax()]
            col2.metric("Top Gainer", f"{top_gainer['driver_name']}", f"{top_gainer['change_pct']:.2f}%")
            top_loser = df.loc[df['change_pct'].idxmin()]
            col3.metric("Top Loser", f"{top_loser['driver_name']}", f"{top_loser['change_pct']:.2f}%")

            st.markdown("---")

            for i in range(0, len(df), 2):
                cols = st.columns(2)
                for j in range(2):
                    if i + j < len(df):
                        driver = df.iloc[i + j]
                        change_pct = driver['change_pct']
                        change_class = "positive" if change_pct >= 0 else "negative"

                        card_html = f"""
                            <div class="driver-card">
                                <img src="{driver['image_url']}" class="driver-image">
                                <div class="driver-info">
                                    <p class="driver-name">{driver['driver_name']} ({driver['driver_code']})</p>
                                    <p class="driver-value">${driver['current_value']:,.2f}</p>
                                    <p class="driver-change {change_class}">{change_pct:+.2f}%</p>
                                </div>
                            </div>
                        """
                        cols[j].markdown(card_html, unsafe_allow_html=True)

        time.sleep(2)

if __name__ == "__main__":
    main()
