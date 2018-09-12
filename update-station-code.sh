#!/bin/bash

cd meteor_network_server/stations/station_code && git pull && cd .. \
   && rm -rf station_code.zip && zip -r station_code.zip station_code
