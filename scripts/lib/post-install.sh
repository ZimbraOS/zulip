#!/usr/bin/env bash

DATA_DIR=/opt/zimbra/data/zulip
POSTGRESQL_DIR=$DATA_DIR/postgresql
RABBITMQ_DIR=$DATA_DIR/rabbitmq

POSTGRESQL_DATA_DIR=$POSTGRES_DIR/13/data

RABBITMQ_CONF_PATH=/etc/rabbitmq/rabbitmq-env.conf

for ARGUMENT in "$@"
do
    KEY=$(echo $ARGUMENT | cut -f1 -d=)
    VALUE=$(echo $ARGUMENT | cut -f2 -d=)
    case "$KEY" in
            -OS_ID) OS_ID=${VALUE} ;;
            -OS_VERSION) OS_VERSION=${VALUE} ;;
            -POSTGRESQL_VERSION) POSTGRESQL_VERSION=${VALUE} ;;
            *)
    esac
done

POSTGRESQL_CONF_PATH=/etc/postgresql/$POSTGRESQL_VERSION/main/postgresql.conf


if [ ! -d "$DATA_DIR" ]; then
    echo "Create directory $DATA_DIR"
    mkdir -p "$DATA_DIR"
fi

if [ ! -d "$POSTGRESQL_DIR" ]; then
    echo "Create directory $POSTGRESQL_DIR"
    mkdir -p "$POSTGRESQL_DIR"
fi

if [ ! -d "$RABBITMQ_DIR" ]; then
    echo "Create directory $RABBITMQ_DIR"
    mkdir -p "$RABBITMQ_DIR"
fi


# change postgres data path 
echo "Update postgress data dir to $POSTGRESQL_DIR"
sed -zi 's/data_directory =[^\n]*/data_directory = ${POSTGRESQL_DATA_DIR}/g' $POSTGRESQL_CONF_PATH
systemctl stop postgresql
rsync -av /var/lib/postgresql/$POSTGRESQL_VERSION $POSTGRESQL_DIR
systemctl start postgresql

# change rabbitmq data path
echo "Update rabbitmq data dir to $RABBITMQ_DIR"
systemctl stop rabbitmq-server
sed -zi '/RABBITMQ_MNESIA_BASE=\/rabbitmq/!s/$/\nRABBITMQ_MNESIA_BASE=\/opt\/zimbra\/data\/zulip\/rabbitmq\n/' $RABBITMQ_CONF_PATH
chown rabbitmq:rabbitmq $RABBITMQ_DIR
systemctl start rabbitmq-server