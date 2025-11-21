# Import modules
import os
import time
import datetime
 
# Define variables
xdays = 1
path  = 'backups\\'
now   = time.time()
 
# List all files newer than xdays
print("\nList all files newer than " + str(xdays) + " days")
print("==========================" + "=" * len(str(xdays)) + "=====")
for root, dirs, files in os.walk(path):
  for name in files:
    filename = os.path.join(root, name)
    if os.stat(filename).st_mtime > now - (xdays * 86400):
      print(filename)
    file_mode_time = datetime.datetime.fromtimestamp(os.path.getmtime(filename))
    file_age_seconds = now - file_mode_time.timestamp()
    file_age_days = int(file_age_seconds // 86400)
    file_age_hours = int((file_age_seconds % 86400) // 3600)
    file_age = now - file_mode_time.timestamp()
    print(f"{name} - Age: {file_age_days} days, {file_age_hours} hours")
    if file_age_days >= xdays:
        print(f"{name} is older than {xdays} days and should be achived.")
