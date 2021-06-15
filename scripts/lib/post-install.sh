#!/usr/bin/env bash
DATA_DIR=/opt/zimbra/data/zulip/

# change postgres data path 
echo "Update postgress data dir to $DATA_DIR"
systemctl stop postgresql
rsync -av /var/lib/postgresql $DATA_DIR
systemctl start postgresql

# change rabbitmq data path
echo "Update rabbitmq data dir to $DATA_DIR"
systemctl stop rabbitmq-server
sed -zi '/RABBITMQ_MNESIA_BASE=\/rabbitmq/!s/$/\nRABBITMQ_MNESIA_BASE=\/opt\/zimbra\/data\/zulip\/rabbitmq\n/' /etc/rabbitmq/rabbitmq-env.conf
mkdir -p $DATA_DIR/rabbitmq
chown rabbitmq:rabbitmq $DATA_DIR/rabbitmq
systemctl start rabbitmq-server
