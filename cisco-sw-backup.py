import datetime
import getpass
from netmiko import ConnectHandler
import os

# Create a directory to store the backups
backup_dir = "backups"
if not os.path.exists(backup_dir):
    os.makedirs(backup_dir)

# Prompt the user for credentials
username = input("Enter your SSH username: ")
password = getpass.getpass("Enter your SSH password: ")

# List of devices to back up (read from a file)
try:
    with open("devices.txt", "r") as f:
        devices = f.read().splitlines()
except FileNotFoundError:
    print("Error: devices.txt not found. Please create a file with a list of device IP addresses.")
    exit()

# Loop through each device
for device_ip in devices:
    print(f"Connecting to device: {device_ip}")
    try:
        # Define the device connection parameters
        device = {
            "device_type": "cisco_ios",
            "ip": device_ip,
            "username": username,
            "password": password,
        }

        # Establish a connection using Netmiko
        net_connect = ConnectHandler(**device)
        print(f"Successfully connected to {device_ip}")

        # Execute the command to get the running configuration
        output = net_connect.send_command("show running-config")

        # Get the device hostname from the prompt for the filename
        hostname = net_connect.base_prompt

        # Create a timestamped filename
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{backup_dir}/{hostname}/{hostname}_showrun_{timestamp}.txt"

        # Ensure the directory for the hostname exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        # Save the configuration to a file
        with open(filename, "w") as f:
            f.write(output)
            print(f"Configuration saved to {filename}\n")

        filename_int_status = f"{backup_dir}/{hostname}/{hostname}_show_int_status_{timestamp}.txt"
        output = net_connect.send_command("show interface status")
        with open(filename_int_status, "w") as f:
            f.write(output)
            print(f"Configuration saved to {filename_int_status}\n")
        
        filename_ip_route = f"{backup_dir}/{hostname}/{hostname}_show_ip_route_{timestamp}.txt"
        output = net_connect.send_command("show ip route")
        with open(filename_ip_route, "w") as f:
            f.write(output)
            print(f"Configuration saved to {filename_ip_route}\n")

        # Disconnect from the device
        net_connect.disconnect()

    except Exception as e:
        print(f"Error connecting to or backing up {device_ip}: {e}\n")
