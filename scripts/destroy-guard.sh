#!/bin/bash

set -e

echo "====================================="
echo "Destroy Guard"
echo "====================================="


if [ "${FORCE_DESTROY}" == "true" ]; then

    if [ "${FORCE_CONFIRMATION}" != "FORCE_DESTROY_EPHEMERAL_ENVIRONMENT" ]; then

        echo "BLOCKED"
        echo "Wrong force destroy confirmation."
        echo "STATUS=BLOCKED"

        exit 1
    fi


    echo "STATUS=FORCED"
    exit 0
fi


bash scripts/check-activity.sh

RESULT=$?


case $RESULT in

0)
    echo "Destroy decision: Allowed"
    exit 0
    ;;

1)
    echo "Destroy decision: Blocked"
    exit 1
    ;;

2)
    echo "Destroy decision: Not Required"
    exit 2
    ;;

esac