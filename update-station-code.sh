#!/bin/bash

cd meteornet_server/stations/station_code && git pull --recurse-submodules origin master && cd .. \
   && rm -rf station_code.zip && zip -r station_code.zip station_code
