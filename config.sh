#!/bin/bash

PROJECT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
MAIN_APP=meteor_network_server
DOMAIN_NAME=mns.rs
STATIC_DIR=/srv/http/$MAIN_APP/static
MEDIA_DIR=/srv/http/$MAIN_APP/media

NGINX_SERVERS_DIR=/etc/nginx/sites-enabled
SOCKET_PATH=/tmp/$MAIN_APP.sock
NGINX_USER=http

templates=("nginx_template.conf" "uwsgi_template.ini" "settings_template.py")
configs=("nginx.conf" "uwsgi.ini" "settings.py")
counter=0
for template in ${templates[@]}; do
    config=${configs[$counter]}

    content=$(cat $PROJECT_DIR/$MAIN_APP/$template)

    content=$(echo "$content" \
            | sed "s~<project_dir>~$PROJECT_DIR~g" \
            | sed "s~<main_app>~$MAIN_APP~g" \
            | sed "s~<domain_name>~$DOMAIN_NAME~g" \
            | sed "s~<static_dir>~$STATIC_DIR~g" \
            | sed "s~<media_dir>~$MEDIA_DIR~g" \
            | sed "s~<socket_path>~$SOCKET_PATH~g" \
            | sed "s~<nginx_user>~$NGINX_USER~g" \
            )

    echo "$content" >$PROJECT_DIR/$MAIN_APP/$config

    ((counter++))
done;

mkdir -p logs
touch logs/system.log
touch logs/system.log.1
