import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import csv
import time
import json
from datetime import datetime
from datetime import timedelta
from collections import OrderedDict


# outputs the data to a graph using matplotlib
# additionally an svg and png rendering of the graph are created
def plot(dataset):
    timestamps, power_map = zip(*sorted(dataset.items()))
    outdoor = [x[1::6] for x in power_map]
    is_cooling = [x[2::6] for x in power_map]
    target_temp = [x[3::6] for x in power_map]
    kwh_used = [x[4::6] for x in power_map]
    # unused: ambient = [x[::6] for x in power]
    # unused: elec_cost = [x[5::6] for x in power]

    # the timestamps were collected with GMT (0) offset. SRP was collected in MST.
    # the below hack only works because MST is awesome. Otherwise I'd have to properly track TZ offset changes though time
    timestamps = [datetime.fromtimestamp(x - time.timezone) for x in timestamps]

    fig = plt.figure()
    setpoint_delta_axis = fig.add_subplot(2, 1, 1)
    setpoint_delta_axis.set_xlabel('Time')
    setpoint_delta_axis.plot(timestamps, np.array(outdoor) - np.array(target_temp), 'b-', label='setpoint delta', linewidth=0.3)
    setpoint_delta_axis.plot(timestamps, target_temp, 'r-', label='setpoint', linewidth=0.3)

    power_used_axis = setpoint_delta_axis.twinx()
    power_used_axis.plot(timestamps, kwh_used, 'g-', label='KwH used', linewidth=0.5)

    is_cooling_axis = fig.add_subplot(2, 1, 2, sharex=setpoint_delta_axis)

    pandas_timestamps = pd.to_datetime(timestamps)
    timestamp_cooling_series = pd.Series(is_cooling, index=pandas_timestamps)

    timestamps_when_off = list(filter(lambda x: not timestamp_cooling_series[x][0], range(len(timestamp_cooling_series))))
    timestamps_when_on = list(filter(lambda x: timestamp_cooling_series[x][0], range(len(timestamp_cooling_series))))

    # calculate a 5 minute block in matplotlib's floating-point time format
    width = calculate_width_by_minutes(minutes=5)

    # plot the boolean vs time data as a broken bar graph, using 5 minute windows
    matplotlib_timestamps_off = mdates.date2num([pandas_timestamps[x] for x in timestamps_when_off])
    graph_broken_bar('red', 'not cooling', is_cooling_axis, matplotlib_timestamps_off, width)

    matplotlib_timestamps_on = mdates.date2num([pandas_timestamps[x] for x in timestamps_when_on])
    graph_broken_bar('green', 'cooling', is_cooling_axis, matplotlib_timestamps_on, width)

    setpoint_delta_axis.set_ylabel('Setpoint-outdoor delta (F)')
    setpoint_delta_axis.legend(loc=2)
    power_used_axis.set_ylabel('Kw/Hr')
    power_used_axis.legend()
    is_cooling_axis.get_yaxis().set_visible(False)
    is_cooling_axis.legend()
    is_cooling_axis.xaxis_date()

    plt.tight_layout()
    plt.show()
    plt.savefig('graph.svg')
    plt.savefig('graph.png')


# simple helper method to limit repeated code.
def graph_broken_bar(color, label, axis, timestamps, width):
    time_windows = list(zip(timestamps, [width] * len(timestamps)))
    axis.broken_barh(time_windows, (0, 1), color=color, label=label)


# generates a matplotlib-compliant time of specified length
def calculate_width_by_minutes(minutes):
    # matplotlib measures time in a proprietary floating point notation
    # because we're graphing the boolean-time data as a broken-bar graph, each segment needs a width
    # to specify the width, we must give it in matplotlib's format.
    start_time = datetime.now()
    start = mdates.date2num(start_time)
    end = mdates.date2num(start_time + timedelta(minutes=minutes))
    width = end - start
    return width


# reads `srp_data.csv` as a CSV file.  Header is assumed to be "Usage Date,Hour,kWh,Cost"
# returns a dict of power usage vs time, where time is a parsed datetime object
# NOTE: SRP's timestamp notation is all power used from the timestamp begin until the next timestamp
def get_power_usage():
    with open('srp_data.csv') as csvfile:
        reader = csv.DictReader(csvfile)
        time_usage_map = {}
        for row in reader:
            date = row['\ufeffUsage Date']
            hr_m = row['Hour'].split(':')
            if 'AM' in hr_m[1]:
                hr = int(hr_m[0])
            elif hr_m[0] == '12':  # 12 PM
                hr = int(hr_m[0])
            else:
                hr = int(hr_m[0]) + 12
            dt = datetime.strptime(date, "%m/%d/%Y").replace(hour=hr)
            epoch = int(time.mktime(dt.timetuple()))
            time_usage_map[epoch] = [float(row['kWh']), float(row['Cost'][1:])]
        return time_usage_map


# read the super-hacky output of NestLogger: Note, you must manually wrap the contents in `[` and `]` before usage.
# expected filename: `nest_data.txt`
# returns a dict: key is an integer indicating GMT Epoch time.
# value is a list of indoor-ambient, outdoor-ambient, cooling state, and temperature setpoint
def get_ac_usage():
    with open('nest_data.txt') as csvfile:
        reader = json.loads(csvfile.read().lower())
        pass
        time_usage_map = OrderedDict()
        prev = dict()
        for row in reader:
            try:
                epoch = int(row['timestamp'])
                time_usage_map[epoch] = [row['ambient_temperature_f'], float(row['outdoor_temp']), row['hvac_state'] == 'cooling', row['target_temperature_f']]
                prev = time_usage_map[epoch]
            except KeyError:
                time_usage_map[int(row['timestamp'])] = prev
        return time_usage_map


# Aligns SRP's hour-based data to NestLogger's 5-minute-based data
# SRP's data is considered master
# returns a dict: key is an integer indicating GMT Epoch time.  Roughly in 5-minute intervals
# value is a list of indoor-ambient, outdoor-ambient, cooling state, temperature setpoint, KwH used, and USD cost.
# Each datapoint within a 1-hour window will have repeated KwH and USD cost values. This is SRP's sampling rate limitation
def align_data(power_map, ac_map):
    dataset = OrderedDict()

    for measurement_epoch_begin, kwh_cost in power_map.items():
        # step 1: initial alignment of measurement epoch and kwh_cost.  Measurement epoch is primary.
        for ac_epoch, ac_data in ac_map.items():
            if ac_epoch < measurement_epoch_begin:
                continue
            # step 2: create an aligned dataset
            elif ac_epoch < measurement_epoch_begin + 3600:
                if ac_epoch in dataset:  # measurement_epoch_begin
                    dataset[ac_epoch] += ac_data + kwh_cost
                else:
                    dataset[ac_epoch] = ac_data + kwh_cost
            else:  # we've completed this time block. move to the next one.
                break
    return dataset


power = get_power_usage()
ac = get_ac_usage()
aligned_data = align_data(power, ac)

plot(aligned_data)
