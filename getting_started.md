# Getting Started

Zocalo requires both ActiveMQ and Graylog to be setup and running. The easiest way of setting these up is via docker.

## Active MQ
Pull and run the following image https://hub.docker.com/r/rmohr/activemq
Follow the steps on docker hub for extracting the config and data into local mounts

Configure DLQ locations, see https://activemq.apache.org/message-redelivery-and-dlq-handling for more info.

In `conf/activemq.xml` under `policyEntries` add:
```xml
<policyEntry queue=">">
  <deadLetterStrategy>
    <individualDeadLetterStrategy queuePrefix="DLQ." useQueueForQueueMessages="true"/>
  </deadLetterStrategy>
</policyEntry>
```

Make sure to enable scheduling, in `conf/activemq.xml` in the `broker` tag add the following property:
```
schedulerSupport="true"
```

Then start ActiveMQ:
```bash
docker run --name activemq -p 61613:61613 -p 8161:8161 \
           -v "$(pwd)/conf:/opt/activemq/conf" \
           -v "$(pwd)/data:/opt/activemq/data" \
           rmohr/activemq
```

The container exposes the following ports:

Port | Description
--- | ---
61613 | Stomp transport
8161 | Web Console / Jolokia REST API

## Graylog

This can be started easily with a docker-compose.yml. See https://docs.graylog.org/en/3.3/pages/installation/docker.html for full details.

```yaml
version: '3'
services:
  # MongoDB: https://hub.docker.com/_/mongo/
  mongo:
    image: mongo:4.2
    networks:
      - graylog
  # Elasticsearch: https://www.elastic.co/guide/en/elasticsearch/reference/6.x/docker.html
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch-oss:7.10.0
    environment:
      - http.host=0.0.0.0
      - transport.host=localhost
      - network.host=0.0.0.0
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ulimits:
      memlock:
        soft: -1
        hard: -1
    deploy:
      resources:
        limits:
          memory: 1g
    networks:
      - graylog
  # Graylog: https://hub.docker.com/r/graylog/graylog/
  graylog:
    image: graylog/graylog:4.0
    environment:
      - GRAYLOG_PASSWORD_SECRET=mysecret
      # Password: admin
      - GRAYLOG_ROOT_PASSWORD_SHA2=8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918
      - GRAYLOG_HTTP_EXTERNAL_URI=http://localhost:9000/
    networks:
      - graylog
    restart: always
    depends_on:
      - mongo
      - elasticsearch
    ports:
      # Graylog web interface and REST API
      - 9000:9000
      # Syslog TCP
      - 1514:1514
      # Syslog UDP
      - 1514:1514/udp
      # GELF TCP
      - 12201:12201
      # GELF UDP
      - 12201:12201/udp
networks:
  graylog:
    driver: bridge
```

Then start with:
```bash
docker-compose up
```

Graylog admin console should be available on http://localhost:9000
Port 12201 is available for python GELF logging. Configure an input in the graylog web console to enable recieving messages.


# Zocalo

For developing create a new conda / virtual enviroment, clone zocalo, and install:
```bash
conda create -n zocalo python=3.7
conda activate zocalo
git clone https://github.com/DiamondLightSource/python-zocalo
cd python-zocalo
pip install -e .
```

For production, install with pip:
```bash
pip install zocalo
```

## Configure

Copy `examples/zocalo.yml` to `zocalo.yml`. At minimum `graylog` and `activemq` must be configured. Environments should be defined for `live` and `test`. Paths to recipes and drop files must also be specified. Messages are written to drop files if ActiveMQ is unavailable.

The config file to use is specified from the environment variable `ZOCALO_CONFIG`, if this is empty it will look for `zocalo.yml` in the current directory

Sample recipes can be used:
```yaml
recipe_path: .../python-zocalo/examples/recipes
```

### ISPyB

If ISPyB is available an [ispyb-api](https://github.com/DiamondLightSource/ispyb-api) config file can be provided, and pointed at from `zocalo.yml`. Both the `ispyb_mariadb_sp ` and `ispyb` keys need to be completed (with subtly different parameters).

```
[ispyb_mariadb_sp]
user = test
pw = test
host = localhost
port = 3306
db = test
reconn_attempts = 6
reconn_delay = 1

[ispyb]
username = test
password = test
host = localhost
port = 3306
database = test
```

This will enable passing ispyb information into the zocalo message parameters, and allow the `ISPyB` service to ingest ISPyB udpates.

### JMX

To make use of `zocalo.queue_monitor` and `zocalo.status_monitor` JMX needs to be configured. The JMX configuration points to the Jolokia REST API. When starting ActiveMQ the logs will tells you where the REST API is running

```bash
 INFO | ActiveMQ Jolokia REST API available at http://0.0.0.0:8161/api/jolokia/
```

So configuration should be 
```yaml
port: 8161
host: localhost
base_url: api/jolokia
```

Username and password are the same as the web console and defined in `users.properties`


# Starting Up

`--test` will make use of the test environment

Start the dispatcher
```bash
conda activate zocalo
zocalo.service -s Dispatcher (--test)
```

Start the process runner
```bash
zocalo.service -s Runner (--test)
```

Optionally start the IPSyB processor
```bash
zocalo.service -s ISPyB (--test)
```

Run the test recipe:
```bash
zocalo.go -r example -s workingdir="$(pwd)" 1234 (--test)
```


# Dead Letter Queue (DLQ)

The dead letter queue is where rejected messages end up. One dlq is available per topic to easily identify where messages are being rejected. For details on dlq see https://activemq.apache.org/message-redelivery-and-dlq-handling

Messages can be purged using:
```bash
zocalo.dlq_purge --output-directory=/path/to/dlq (--test)
```

And reinjected with:
```bash
zocalo.dlq_reinject dlq_file (--test)
```
