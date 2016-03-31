#!/bin/sh

source /opt/bin/activate
cd /opt/ori

for JSON_FILE in ocd_backend/sources/*.json
do
  MUNI=`basename $JSON_FILE .json`
  UPDATABLE_SOURCES="${MUNI}_committees ${MUNI}_popit_organizations ${MUNI}_popit_persons ${MUNI}_meetings ${MUNI}_reports ${MUNI}_resolutions ${MUNI}_videotulen"

  for UPDATE_SOURCE in $UPDATABLE_SOURCES
  do
    echo `date` $UPDATE_SOURCE
    ./manage.py extract start $UPDATE_SOURCE --sources_config=$JSON_FILE
    sleep 60
  done

  sleep 1800
done
echo `date` "All done"
