#!/bin/sh

# Quickly delete all traces of a user from the database and filesystem
# usage: ./deluser.sh username

[ $# -eq 0 ] && { echo "Usage: $0 username"; exit 1; }

USER=$1
USERID=`sqlite3 ../database.db "select id from users where username = '${USER}'"`
for table in albums comments images posts; do
	sqlite3 ../database.db "delete from ${table} where userid = ${USERID}"
done
sqlite3 ../database.db "delete from users where id = ${USERID}"
rm -r ../content/${USER}/
