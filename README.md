# Grid-Pulse: Real-Time Stock Market for F1 Drivers 

Grid-Pulse is a real-time data processing project that simulates a stock market for Formula 1 drivers. A driver's stock value is determined by a baseline market value and is dynamically updated based on their performance in historical and live-simulated race weekends.

The project uses a data pipeline built with **Python**, **Apache Kafka**, and **Streamlit** to generate, process, and visualize data in real-time.

## Architecture

The application is built on a distributed messaging architecture using Apache Kafka to decouple the data generation, processing, and visualization components.

The data flows through the system in two main phases:

1.  **Batch Processing (Historical Data):** Establishes the initial market state by processing baseline values and a full season of simulated historical race data.
2.  **Stream Processing (Real-time Data):** A long-running service listens for live race weekend events (triggered by a cron job) and applies incremental updates to the market.

<img width="883" height="855" alt="Screenshot from 2025-09-09 18-26-52" src="https://github.com/user-attachments/assets/0dcf5dab-ea91-4503-b267-619d1d60ee87" />


## Grid-Pulse Dashboard 

<img width="1855" height="935" alt="Screenshot from 2025-09-09 17-36-30" src="https://github.com/user-attachments/assets/451baf0e-43f3-4d8a-b2a9-5629ea9a4c80" />


## How to Run the Project?

Follow these steps to set up and run the Grid-Pulse application from scratch on a Linux machine.

### 1. Prerequisites
* **Git:** To clone the repository.
* **Python 3.8+:** To run the application scripts.
* **Apache Kafka:** To handle the data streams. Ensure both Zookeeper and the Kafka Broker are running.

### 2. Clone the Repository
```bash
git clone https://github.com/sumukhacharya03/Grid-Pulse.git
cd Grid-Pulse
```

### 3. Install Dependencies
Install the required Python packages.
```bash
pip install -r requirements.txt
```

### 4. Setup Kafka
Make sure Zookeeper and your Kafka broker are running. Then, create all the necessary Kafka topics with the following commands (run from your Kafka installation directory):

```bash
# Delete topics if they exist for a clean slate
./bin/kafka-topics.sh --delete --topic drivers-baseline-value --bootstrap-server localhost:9092
./bin/kafka-topics.sh --delete --topic historical-performance-practice --bootstrap-server localhost:9092
# ... (add delete commands for all other topics)

# Create all topics
./bin/kafka-topics.sh --create --topic drivers-baseline-value --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
./bin/kafka-topics.sh --create --topic historical-performance-practice --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
./bin/kafka-topics.sh --create --topic historical-performance-qualifying --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
./bin/kafka-topics.sh --create --topic historical-performance-race --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
./bin/kafka-topics.sh --create --topic realtime-performance-practice --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
./bin/kafka-topics.sh --create --topic realtime-performance-qualifying --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
./bin/kafka-topics.sh --create --topic realtime-performance-race --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
./bin/kafka-topics.sh --create --topic driver-stock-values --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
```

### 5. Run the One-Time Historical Setup
These scripts generate and process all the historical data to establish the initial market state.

```bash
# 1. Scrape and generate the baseline values CSV
python baseline_market_value/scraper.py | python baseline_market_value/output.py

# 2. Generate historical race data JSON files
python generator/historical/generator_historical.py

# 3. Produce baseline and historical data to Kafka
python baseline_market_value/producer1.py
python generator/historical/producer2.py

# 4. Run the batch calculation service to set the initial market state
python calculation_service.py
```

### 6. Launch the Live Application
Now, start the long-running services. You will need **two separate terminals**.

* **Terminal 1: Start the Real-time Service**
    This service loads the historical state and listens for live race events.
    ```bash
    python realtime_service.py
    ```

* **Terminal 2: Start the Streamlit Dashboard**
    This will launch the web application.
    ```bash
    streamlit run stock_market.py
    ```

### 7. Automate Real-time Generation (Optional)
To have the simulation run automatically on scheduled race days, set up a cron job.

1.  Open crontab: `crontab -e`
2.  Add this line, replacing the path with the absolute path to your project:
    ```
    0 9 * * * /usr/bin/python3 /path/to/your/project/grid-pulse/generator/real_time/schedule_manager.py
    ```

The system is now live! The cron job will trigger the data generation on race days, and the dashboard will update automatically.
