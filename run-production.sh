#!/bin/bash

source config.sh

sudo python manage.py collectstatic --noinput

sudo mkdir -p $NGINX_SERVERS_DIR
sudo ln -sf $PROJECT_DIR/$MAIN_APP/nginx.conf $NGINX_SERVERS_DIR/$MAIN_APP.conf
sudo systemctl start nginx

sudo uwsgi --ini $MAIN_APP/uwsgi.ini --uid=$USER --gid=$USER
sudo rm -f $SOCKET_PATH
