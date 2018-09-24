#!/bin/bash

source config.sh

./manage.py runperiodic &
DJANGO_DEBUG=True ./manage.py runserver 0.0.0.0:8000
