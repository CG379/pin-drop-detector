import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

f = pd.read_csv('sensor_data_22-23-08.csv', header=None)
f.columns = ['timestamp', 'value']
f['timestamp'] = f['timestamp'].astype(float)
f['value'] = f['value'].astype(int)
f['value'] = f['value'].replace(0, np.nan)  # Replace 0 with NaN for better visualization

plt.figure(figsize=(10, 5))
plt.scatter(f['timestamp'], f['value'], marker='.', markersize=2, color='blue')
plt.title('Sensor Data Over Time')
plt.xlabel('Timestamp (s)')
plt.ylabel('Sensor Value')
plt.grid(True)
plt.ylim(0, 1.5)  # Set y-axis limits to better visualize the data
plt.xticks(np.arange(0, f['timestamp'].max(), step=1))  # Set x-ticks to every second
plt.show()