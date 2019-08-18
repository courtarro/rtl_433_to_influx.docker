#!/usr/bin/env python3

import datetime
import io
import json
import subprocess
import time

from influxdb import InfluxDBClient
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

    dbclient = InfluxDBClient(**config['influxdb'])

    cmd_line_raw = "rtl_433 -g 20 -d :12 -F json -M utc -M newmodel -M level"
    cmd_line = cmd_line_raw.split(' ')
    print(cmd_line)

    print("Starting subprocess", flush=True)
    proc = subprocess.Popen(cmd_line, stdout=subprocess.PIPE)

    try:
        while True:
            line_raw = proc.stdout.readline()
            try:
                #print(line_raw, flush=True)
                if not line_raw:
                    break
                line = json.loads(line_raw)
            except Exception as e:
                print("Unable to convert line: {}".format(e), flush=True)
                continue

            try:
                #print(line, flush=True)
                tags, fields = convert_values(line)
            except Exception as e:
                print("Unable to convert values: {}".format(e), flush=True)
                continue

            try:
                write_values(dbclient, tags, fields)
            except ConnectionError as e:
                print("Unable to write to DB: ({})".format(e), flush=True)
                continue

    except KeyboardInterrupt:
        pass

    print("Shutting down subprocess", flush=True)
    proc.send_signal(subprocess.signal.SIGINT)
    proc.wait()
