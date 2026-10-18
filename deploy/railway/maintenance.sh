#!/bin/sh
set -eu
python manage.py purge_personal_data
exec python manage.py clearsessions
