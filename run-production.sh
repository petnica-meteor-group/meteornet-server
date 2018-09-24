#!/bin/bash

source config.sh

sudo ./manage.py collectstatic --noinput

sudo mkdir -p $NGINX_SERVERS_DIR
sudo ln -sf $PROJECT_DIR/$MAIN_APP/nginx.conf $NGINX_SERVERS_DIR/$MAIN_APP.conf
sudo systemctl restart nginx

if [[ $USER == root ]]; then
    user=$SUDO_USER
else
    user=$USER
fi

sudo ./manage.py runperiodic &
periodic_pid=$!
sudo uwsgi --ini $MAIN_APP/uwsgi.ini --uid=$user --gid=$user
sudo kill -s INT $periodic_pid 2>/dev/null >/dev/null
sudo rm -f $SOCKET_PATH
