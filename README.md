# Host Checker

This project contains a Python module that perform basic
health checks on a list of configured web hosts, on a 
specified schedule, and optionally with a reuglar expression
for validation (experimental), and push metrics to a data
store.

This module consists of 2 components, a data producer
and a data consumer. The data producer manages making
requests to configured web hosts and produce the metrics
about the hosts health, then these metrics are pushed
to a Kafka topic.

The data consumer, consumes said Kafka topic and persists
the data to a PostgreSQL database.

The module is called host-checker, it can be installed
and used as a command line tool, although the recommended
approach is to use docker to run 2 containers to carry
out the producing and consuming of health metrics.

## Running in Docker

### Pre-requisites

* A Kafka service with a topic ready
* A PostgreSQL database and a table with the following
  columns:
  * status_code (smallint)
  * latency (number)
  * address (text)
  * is_valid (boolean)

### Env setup

Run `make config` to create the necessary env files from
templates.

#### env file
Edit `env` adding the necessary values for your Kafka
service, topic, and PostgreSQL database.

**Note** leave the values for the variables `KAFKA_SSL_*`
as they are specified from the template. The certs will
be added in the next step.

#### certs
Download the SSL client certificates for your Kafka service and
place them in the `certs` directory with the following names:
* ssl_ca_file.pem
* ssl_key_file.key
* ssl_cert_file.cert

#### producer_config
Add to the `producer_config` file one line for each web host
you want to monitor with the following format

`DOMAIN_NAME FREQUENCY (REGEX)`

For example: `https://google.com 5` to monitor google.com every
5 minutes.

**Note**. The regex validation is experimental, only simple regex
values in one line were tested.

#### Run the service
Run the service with `make start`. This will build the images and
start a consumer and a producer container with the environment
and config previously set.

After a short time you should see data arriving into the configured
table. Use a small value for the env variable `DB_BATCH_SIZE` to
see data quicker in the db.

## Stand alone usage
The module can also be used as a stand alone cli tool.
### Installation
First you sould install the module from source.
`python3 -m pip install src`

Regardless of the operation (produce or consume) you
will need to set the following env variables:

* KAFKA_TOPIC
* KAFKA_BOOTSTRAP_SERVERS
* KAFKA_SSL_CA_FILE=[path to ca file]
* KAFKA_SSL_KEY_FILE=[path to key file]
* KAFKA_SSL_CERT_FILE=[path to cert file]
* DB_BATCH_SIZE=[size of buffer to batch db operations]
* LOG_LEVEL=[INFO, DEBUG]
### Running the producer as stand alone
First, create a config file, similar to the one defined
for a Dockerized deployment. Then run
`host-metrics produce -c <path_to_config_file>`

### Running the consumer as stand alone
Additionally to the Kafka env variables, the consumer
needs your DB's info to write the metrics to. Set the 
following en vvariables in your shell:

* DB_PASSWORD
* DB_USER
* DB_PORT
* DB_TABLE
* DB_NAME
* DB_HOST

Run `host-metrics consume`
## ToDo

There is realy a lot to further improve in this project to make it
prod ready. This is a list of potential improvement actions.

* Improve deployment process
  * Currently there are too many config steps  
* Explore scaling issues with this solution
  * There is no partitioning for the Kafka topic, perhaps it should
    be considered.
* Add a comprehensive integration test
  * Possibly using a dockerized Kafka topic and PostgreSQL
    to deploy the service in a local env and observe its
    behaviour.
* Improve test coverage
* Initialize database if necessary
  * Having a `db_init` service that creates the table if it
    does not exist.
* Review data input strategies. Currently the module
  relies too much on env variables to get the necessary
  config values, perhaps it is better to use command line
  args.
