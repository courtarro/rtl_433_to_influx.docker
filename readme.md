InfluxDB monitor for rtl_433
============================

This Docker configuration builds an image that contains everything needed to run `rtl_433` and
record its messages into an InfluxDB instance. Inside the container, `supervisord` starts a Python
script, which executes a subprocess instance of `rtl_433` in JSON mode. When `rtl_433` reports
data, the message is packaged into an InfluxDB measurement and sent to the database. It runs as a
non-privileged user inside the container, so you'll need to have access to `/dev/bus/usb` inside
the container (see below).

## Building

To build the image:

    docker build .

Or, using Docker Compose:

    docker-compose build

## Running

1. Create `config.yaml` from the example:

        cp config.yaml.example config.yaml

2. Edit the `config.yaml` file to include any InfluxDB parameters needed. These will be passed
   directly to the `InfluxDBClient` in Python, so you can use any parameters expected by that
   class, including `host`, `port`, `username`, `password`, `database`, etc. See the full list
   [here](https://github.com/influxdata/influxdb-python/blob/master/influxdb/client.py).

3. If necessary, set the RTL-SDR parameters in `config.yaml`. Only a small set of options are
   supported by this script. If you want to add more, just look in the script for where `cmd_line`
   is defined.

4. The first time, start the container with Docker Compose in foreground mode to see if there are
   any errors that need to be resolved:

        docker-compose up

5. If everything works, press Ctrl-C to stop, then run in daemon mode:

        docker-compose up -d

The `docker-compose.yaml` file included with the project sets up access to the `RTL-SDR` device by
passing in `/dev/bus/usb`. 
