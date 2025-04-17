import csv
import random
import argparse
import json
from datetime import datetime, timedelta

'''
This script generates fake sensor data. Define sensor values by ranges and time periods with array of dicts.
Example usage:
python sensor_data_simulator.py '[{"time":30,"temperature":[19,21],"humidity":[0.8,0.8],"light":[2000,2010],"error":0.1},{"time":60,"temperature":[30,35],"humidity":[0.8,0.8],"light":[2000,2010],"error":0}]' --output data.csv
'''


def generate_sensor_data(periods, output_file='sensor_data.csv'):
    current_time = datetime.now()
    rows = []

    for period in periods:
        duration = period.get('time', 0)
        temp_range = period.get('temperature', (0, 0))
        humid_range = period.get('humidity', (0, 0))
        light_range = period.get('light', (0, 0))
        error_rate = period.get('error', 0)

        for _ in range(duration):
            is_error = random.random() < error_rate
            if is_error:
                row = [current_time.strftime('%Y-%m-%d %H:%M:%S'), None, None, None]
            else:
                temp = round(random.uniform(*temp_range), 2)
                humid = round(random.uniform(*humid_range), 2)
                light = round(random.uniform(*light_range), 2)
                row = [current_time.strftime('%Y-%m-%d %H:%M:%S'), temp, humid, light]
            rows.append(row)
            current_time += timedelta(minutes=1)

    with open(output_file, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Time', 'Temperature', 'Humidity', 'Light'])
        writer.writerows(rows)

    print(f"Data written to {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Simulate sensor data and output to a CSV file.')
    parser.add_argument('config', type=str, help='JSON string or path to JSON file with configuration')
    parser.add_argument('--output', type=str, default='sensor_data.csv', help='Output CSV file name')

    args = parser.parse_args()

    try:
        if args.config.endswith('.json'):
            with open(args.config, 'r') as f:
                periods = json.load(f)
        else:
            periods = json.loads(args.config)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return

    generate_sensor_data(periods, args.output)

if __name__ == '__main__':
    main()

