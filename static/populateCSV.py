import serial
import time
import csv
from datetime import datetime

# --- Configuration ---
COM_PORT = 'COM3'      # Change to your COM port (e.g., 'COM3' on Windows or '/dev/ttyUSB0' on Linux)
BAUD_RATE = 115200       # Adjust the baud rate as needed
CSV_FILENAME = 'eeg_data.csv'

# --- Open Serial Port ---
try:
    ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)
    print(f"Opened {COM_PORT} at {BAUD_RATE} baud.")
except serial.SerialException as e:
    print(f"Error opening {COM_PORT}: {e}")
    exit(1)

# --- Write CSV header ---
with open(CSV_FILENAME, mode='w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['timestamp', 'value'])

print("Starting to read from the COM port. Press Ctrl+C to stop.")

# --- Main Loop: Read and write every 2 seconds ---
try:
    while True:
        # Read a line from the serial port
        raw_line = ser.readline()
        try:
            # Decode bytes to string and strip newline characters
            data = raw_line.decode('utf-8').strip()
        except UnicodeDecodeError:
            # Skip lines that can’t be decoded
            data = None

        if data:
            # Get the current timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Append the timestamp and data to the CSV file
            with open(CSV_FILENAME, mode='a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([timestamp, data])
            print(f"{timestamp}: {data}")
        else:
            print("No data received.")

        # Wait for 2 seconds before next read
        time.sleep(0.405)
except KeyboardInterrupt:
    print("\nExiting program.")
finally:
    ser.close()
    print("Closed serial port.")
