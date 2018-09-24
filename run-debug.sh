#!/bin/bash

source config.sh

./manage.py runperiodic &
periodic_pid=$!
DJANGO_DEBUG=True ./manage.py runserver 0.0.0.0:8000
kill -s INT $periodic_pid 2>/dev/null >/dev/null
