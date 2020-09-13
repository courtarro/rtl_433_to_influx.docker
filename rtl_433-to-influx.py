#!/usr/bin/env python3

import datetime
import io
import json
import subprocess
import sys
import time

from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBServerError, InfluxDBClientError
from requests.exceptions import ConnectionError
import yaml

CONFIG_FILE_DEFAULT = "config.yaml"


def eprint(*args, **kwargs):
    # Print to stderr
    print(*args, file=sys.stderr, **kwargs)

def create_point(tags, fields):
    point = {
        "measurement": "rtl433",
        "time": datetime.datetime.utcnow().isoformat() + 'Z',
        "tags": tags,
        "fields": fields
    }

    return point

def convert_values(line):
    line.pop('time', None)
    tags = {}
    for tag_name in ['brand', 'OS', 'model', 'id', 'channel']:
        tags[tag_name] = line.pop(tag_name, None)

    fields = line
    return tags, fields


if __name__ == "__main__":
    if len(sys.argv) == 2:
        config_filename = sys.argv[1]
    else:
        config_filename = CONFIG_FILE_DEFAULT

    try:
        with io.open(config_filename) as config_file:
            config = yaml.safe_load(config_file)
    except Exception as e:
        eprint('Unable to read config file: {} (Error: {})'.format(config_filename, e))
        eprint('If the file does not exist, please copy config.yaml.example and modify it to match your system.')
        sys.exit(1)

    exit_code = 0
    dbclient = None
    while dbclient is None:
        try:
            dbclient = InfluxDBClient(**config['influxdb'])
        except InfluxDBServerError:
            eprint('Unable to connect to InfluxDB. Waiting 5 seconds, then retrying...')
            time.sleep(5)

    cmd_line_raw = 'rtl_433 -F json -M utc -M newmodel -M level -Y classic'
    cmd_line = cmd_line_raw.split(' ')

    if 'rtlsdr' in config:
        rtl_cfg = config['rtlsdr']
        if 'gain' in rtl_cfg:
            cmd_line += ['-g', str(rtl_cfg['gain'])]

        if 'device_serial' in rtl_cfg:
            cmd_line += ['-d', ':{}'.format(rtl_cfg['device_serial'])]
        elif 'device_index' in rtl_cfg:
            cmd_line += ['-d', str(rtl_cfg['device_index'])]

        if 'frequency' in rtl_cfg:
            cmd_line += ['-f', str(rtl_cfg['frequency'])]

        if 'sample_rate' in rtl_cfg:
            cmd_line += ['-s', str(rtl_cfg['sample_rate'])]

    print('Starting subprocess: {}'.format(' '.join(cmd_line)), flush=True)
    proc = subprocess.Popen(cmd_line, stdout=subprocess.PIPE)

    if 'custom_tags' in config:
        custom_tags = config['custom_tags']
    else:
        custom_tags = None

    try:
        try:
            while True:
                line_raw = proc.stdout.readline()
                try:
                    if not line_raw:
                        break
                    line = json.loads(line_raw)
                except Exception as e:
                    eprint('Unable to convert line: {}'.format(e), flush=True)
                    continue

                try:
                    tags, fields = convert_values(line)
                except Exception as e:
                    eprint('Unable to convert values: {}'.format(e), flush=True)
                    continue

                if custom_tags is not None:
                    tags.update(custom_tags)

                point = create_point(tags, fields)
                try:
                    dbclient.write_points([point])
                except (ConnectionError, InfluxDBServerError, InfluxDBClientError) as e:
                    eprint('Unable to write to DB: ({})'.format(e), flush=True)
                    eprint('Tried to write: {}'.format(json.dumps(point)))
                    continue

        except KeyboardInterrupt:
            # This will break us out of the loop, but continue execution to shut things down
            pass
    except Exception as e:
        # Something serious happened and we don't know how to recover
        eprint('An unhandled exception occurred: {}'.format(e), flush=True)
        exit_code = 1

    print('Shutting down subprocess', flush=True)
    proc.send_signal(subprocess.signal.SIGINT)
    proc.wait(timeout=5)
    sys.exit(exit_code)
