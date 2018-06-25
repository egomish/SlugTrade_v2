#!/usr/bin/env bash

PORT="$1"

if [ PORT == "" ]; then
    $PORT="8000"
fi

source env/bin/activate
python3 manage.py makemigrations
python3 manage.py migrate
python3 manage.py runserver $PORT
