#!/bin/bash

PROJECT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
MAIN_APP=meteor_network_server
DOMAIN_NAME=meteori.petnica.rs

STATIC_DIR=/srv/http/$MAIN_APP/static
MEDIA_DIR=/srv/http/$MAIN_APP/media

SECRET_KEY_PATH=$PROJECT_DIR/$MAIN_APP/secret_key
DB_PASS_PATH=$PROJECT_DIR/$MAIN_APP/db_password

SSL_KEY_PATH=/etc/ssl/private/nginx-selfsigned.key
SSL_CERT_PATH=/etc/ssl/certs/nginx-selfsigned.crt
SSL_DHPARAM_PATH=/etc/ssl/certs/dhparam.pem
UWSGI_PARAMS_PATH=/etc/nginx/uwsgi_params
NGINX_SERVERS_DIR=/etc/nginx/sites-enabled
SOCKET_PATH=/tmp/$MAIN_APP.sock
NGINX_USER=www-data

DB_NAME=mndb

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
            | sed "s~<ssl_key_path>~$SSL_KEY_PATH~g" \
            | sed "s~<ssl_cert_path>~$SSL_CERT_PATH~g" \
            | sed "s~<ssl_dhparam_path>~$SSL_DHPARAM_PATH~g" \
            | sed "s~<uwsgi_params_path>~$UWSGI_PARAMS_PATH~g" \
            | sed "s~<db_name>~$DB_NAME~g" \
            )

    echo "$content" >$PROJECT_DIR/$MAIN_APP/$config

    ((counter++))
done;

if [ ! -f $SECRET_KEY_PATH ]; then
    echo $(uuidgen) >$SECRET_KEY_PATH
fi

if [ ! -f $DB_PASS_PATH ]; then
    echo -n "DB Password: "
    read -s db_pass
    echo
    echo $db_pass >$DB_PASS_PATH
fi

mkdir -p logs
touch logs/system.log
touch logs/system.log.1
