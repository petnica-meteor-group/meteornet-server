#!/bin/bash

source config.sh

DJANGO_DEBUG=True ./manage.py runserver 0.0.0.0:8000
