FROM ubuntu:bionic

ARG UID=1000
ARG GID=1000

# APT Packages
RUN apt-get update &&\
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends libusb-1.0-0-dev pkg-config libtool cmake build-essential supervisor &&\
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends librtlsdr-dev rtl-sdr socat &&\
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3 python3-influxdb python3-yaml &&\
    apt-get clean &&\
    rm -rf /var/lib/apt/lists/*

RUN mkdir /docker

# Set up rtl_433
ADD rtl_433 /docker/rtl_433
WORKDIR /docker/rtl_433
RUN mkdir build &&\
    cd build &&\
    cmake .. &&\
    make -j4 &&\
    make install

# Limited user setup
RUN groupadd -g ${GID} docker &&\
    useradd -r -d /docker -u ${UID} -g docker docker
RUN chown docker:docker /docker

# Supervisor
ADD supervisor /etc/supervisor

WORKDIR /docker
ENTRYPOINT ["supervisord"]
CMD ["-c", "/etc/supervisor/supervisord.conf"]
