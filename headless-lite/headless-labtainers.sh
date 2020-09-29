#!/bin/bash
while [[ -n "$1" ]]; do
    if [[ "$1" == -h ]]; then
        echo "-d to use your local yml file"
        echo "-n to supress updates on the container, e.g. if you created your own labtainer.tar"
        exit 0
    fi
    if [[ "$1" == -n ]]; then
        export LABTAINER_UPDATE="FALSE"
        shift
    fi
    if [[ "$1" == -d ]]; then
        LABTAINER_DEV="TRUE"
        shift
    fi
done

if [[ -d ./mystuff ]]; then
    echo "Running Headless Labtainers."
    docker-compose up
else
    echo "Installing and running Headless Labtainers."
    mkdir -p ~/headless-labtainers
    SCRIPTPATH="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
    cp $SCRIPTPATH/headless-labtainers.sh ~/headless-labtainers
    cd ~/headless-labtainers
    mkdir -p mystuff
    mkdir -p labtainer_xfer
    mkdir -p labtainers
    if [[ "$LABTAINER_DEV"=="TRUE" ]];then
        echo "Using local yml"
        cp $LABTAINER_DIR/headless-lite/docker-compose.yml .
    else
        curl https://raw.githubusercontent.com/mfthomps/Labtainers/premaster/headless-lite/docker-compose.yml > docker-compose.yml 
    fi
    docker-compose up
    HEADLESS_DIR=`pwd`
    echo "Add $HEADLESS_DIR to your PATH environment variable and run headless-labtainers from there in the future."
fi
