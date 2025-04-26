import os
import serial.tools.list_ports

import threading
import time
import keyboard  


class SerialConnection:
    def __init__(self, baudrate=115200):
        self.serialInst = serial.Serial()
        self.baudrate = baudrate
        self.port = None
    
    def list_ports(self):
        '''List all ports to connect to, change as needed'''
        print("---- PRINTING PORTS AVALIABLE ----")
        ports = serial.tools.list_ports.comports()
        # Extract names of ports
        portsList = [str(port).split()[0] for port in ports]
        for port in portsList:
            print(port)
        return portsList

    def select_port(self):
        """Prompt user to select a valid COM port and establish connection."""
        ports_list = self.list_ports()
        
        if not ports_list:
            return False  # No ports available

        port_number = input("Select COM Port (just the number): ").strip()
        self.port = None  # Reset port selection

        for port_desc in ports_list:
            if port_desc.startswith("COM" + port_number):
                self.port = "COM" + port_number
                print(f"Selected port: {self.port}")
                break

        if self.port is None:
            print("Error: Selected COM port not found.")
            return False  # Exit on invalid selection

        # Configure serial instance
        self.serialInst.baudrate = self.baudrate
        self.serialInst.port = self.port

        try:
            self.serialInst.open()
            print(f"Connected to {self.port}")
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    def disconnect(self):
        '''Close the serial connection'''
        if self.serialInst.is_open:
            self.serialInst.close()
            print("Connection closed")


# Create a SerialConnection instance
serial_conn = SerialConnection(baudrate=115200)

if not serial_conn.select_port():
    print("Failed to establish connection. Exiting.")
    exit()

serialInst = serial_conn.serialInst


# !--------------------- MANUAL INPUT ---------------------!
# This section allows the user to manually input data using the keyboard.
# While collecting data from the sensor, the user can press the SPACEBAR to indicate that there is a vibration.
# We will treat this data as the "true" data for the sensor and use it for confusion matrix stuff in the notebook.
# Had to multithread this to get it working lol
manual_data = []
running = True
running_UI = True

def record_manual_input():
    global running

    print("Press and hold SPACEBAR to mark a vibration (1s resolution). Press ESC to stop.")
    last_timestamp = int(time.time())

    while running:
        current_timestamp = int(time.time())
        if keyboard.is_pressed('esc'):
            print("ESC pressed. Stopping input...")
            running = False
            break

        if current_timestamp != last_timestamp:  # Only log once per second
            if keyboard.is_pressed('space'):
                manual_data.append((current_timestamp, 1))
                print(f"[Manual] vibration at {current_timestamp}")
            else:
                manual_data.append((current_timestamp, 0))
            last_timestamp = current_timestamp
        time.sleep(0.1)  # Check 10 times a second

# get data from stm32
# data has both a timestamp and a value
# Show live if the sensor detects something (value will be 1 or 0)
# save data for later in csv for analysis
# Somehow include actual values so we can do confusion matrix (true positive, false positive, true negative, false negative)

def main():
    global running
    global running_UI

    while running_UI:
        # Initialize data storage
        manual_data.clear()
        data = []
        running = True

        # Ask if manual input should be enabled
        enable_manual_input = input("Enable manual input recording (spacebar)? (y/n): ").strip().lower() == 'y'
        input_thread = None  # fixes error later 

        # Signal STM32 to prepare
        serialInst.write("SX".encode('utf-8'))
        serialInst.flush()
        print("Waiting for STM32 to be ARMED (press the button)...")

        # Wait for the STM32 to send "START"
        while True:
            if serialInst.in_waiting:
                line = serialInst.readline().decode('utf-8').strip()
                if line == "ARMED":
                    print("STM32 started. Beginning data collection.")
                    break

        # Start manual input thread
        if enable_manual_input:
            input_thread = threading.Thread(target=record_manual_input)
            input_thread.start()

        try:
            while running:
                line = serialInst.readline().decode('utf-8').strip()
                if line:
                    try:
                        timestamp, value = line.split(",")
                        data.append((float(timestamp), int(value)))
                        if value == "1":
                            print("Detection: Vibration detected!")
                    except ValueError:
                        if line != "DISARMED":
                            print(f"Ignored malformed line: {line}")
                if line == "DISARMED":
                    print("STM32 DISARMED. Stopping data collection.")
                    running = False
        except Exception as e:
            print(f"Error: {e}")

        
        running = False

        # Stop the manual input thread if it was running
        if input_thread:
            input_thread.join()

        # Save sensor data with timestamp in the filename
        current_time = time.strftime("%H-%M-%S")
        sensor_data_filename = f"./sensor_data_{current_time}.csv"
        with open(sensor_data_filename, "w") as f:
            for timestamp, value in data:
                f.write(f"{timestamp},{value}\n")
        print(f"Sensor data saved to {sensor_data_filename}")

        # Save manual input data if enabled, with timestamp in the filename
        if enable_manual_input:
            true_data_filename = f"./true_data_{current_time}.csv"
            with open(true_data_filename, "w") as f:
                for timestamp, value in manual_data:
                    f.write(f"{timestamp},{value}\n")
            print(f"True data (manual input) saved to {true_data_filename}")
        else:
            print("Manual input was disabled. No true data saved.")

        # Ask if the user wants to run again
        run_again = input("Run again? (y/n): ").strip().lower() == 'y'
        if not run_again:
            running_UI = False
            serial_conn.disconnect()
            print("Exiting...")
            break

if __name__ == "__main__":
    main()

