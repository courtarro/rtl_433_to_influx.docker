#!/usr/bin/env python3

import datetime
import io
import json
import subprocess
import time

from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBServerError
from requests.exceptions import ConnectionError
import yaml

CONFIG_FILE = "config.yaml"


def write_values(dbclient, tags, fields):
    points = [{
        "measurement": "rtl433",
        "time": datetime.datetime.utcnow().isoformat() + 'Z',
        "tags": tags,
        "fields": fields
    }]

    dbclient.write_points(points)

def convert_values(line):
    line.pop('time', None)
    tags = {}
    for tag_name in ['brand', 'OS', 'model', 'id', 'channel']:
        tags[tag_name] = line.pop(tag_name, None)

    fields = line
    return tags, fields


if __name__ == "__main__":
    try:
        with io.open(CONFIG_FILE) as config_file:
            config = yaml.safe_load(config_file)
    except Exception as e:
        print("Unable to read config file: {} (Error: {})".format(CONFIG_FILE, e))
        print("If the file does not exist, please copy config.yaml.example and modify it to match your system.")
        exit(1)

    dbclient = None
    while dbclient is None:
        try:
            dbclient = InfluxDBClient(**config['influxdb'])
        except InfluxDBServerError:
            print("Unable to connect to InfluxDB. Waiting 5 seconds, then retrying...")
            time.sleep(5)

    cmd_line_raw = "rtl_433 -F json -M utc -M newmodel -M level"
    cmd_line = cmd_line_raw.split(' ')

    if 'rtlsdr' in config:
        rtl_cfg = config['rtlsdr']
        if 'gain' in rtl_cfg:
            cmd_line += ['-g', str(rtl_cfg['gain'])]

        if 'device_serial' in rtl_cfg:
            cmd_line += ['-d', ':{}'.format(rtl_cfg['device_serial'])]
        elif 'device_index' in rtl_cfg:
            cmd_line += ['-d', str(rtl_cfg['device_index'])]

    print("Starting subprocess: {}".format(cmd_line), flush=True)
    proc = subprocess.Popen(cmd_line, stdout=subprocess.PIPE)

    try:
        try:
            while True:
                line_raw = proc.stdout.readline()
                try:
                    if not line_raw:
                        break
                    line = json.loads(line_raw)
                except Exception as e:
                    print("Unable to convert line: {}".format(e), flush=True)
                    continue

                try:
                    tags, fields = convert_values(line)
                except Exception as e:
                    print("Unable to convert values: {}".format(e), flush=True)
                    continue

                try:
                    write_values(dbclient, tags, fields)
                except (ConnectionError, InfluxDBServerError) as e:
                    print("Unable to write to DB: ({})".format(e), flush=True)
                    continue

        except KeyboardInterrupt:
            pass
    except Exception as e:
        print("An unhandled exception occurred: {}".format(e), flush=True)

    print("Shutting down subprocess", flush=True)
    proc.send_signal(subprocess.signal.SIGINT)
    proc.wait()
