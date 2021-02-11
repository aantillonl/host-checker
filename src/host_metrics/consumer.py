"""Health metrics consumer"""
import json
from json.decoder import JSONDecodeError
import logging
import os
from typing import Dict
from psycopg2 import extras
import psycopg2
from kafka import KafkaConsumer
from jsonschema import validate, ValidationError

logger = logging.getLogger('HostChecker')
logging.basicConfig(level=os.environ.get('LOG_LEVEL', 'INFO'))

message_schema = {
    "type" : "object",
    "properties" : {
        "status_code" : {"type" : "number"},
        "address" : {"type" : "string"},
        "latency" : {"type" : "number"},
        "is_valid": {"type" : "boolean"}
    },
    "required": ["status_code", "address", "latency", "is_valid"],
    "additionalProperties": False
}

def message_iter(kafka_consumer: KafkaConsumer)->Dict:
    """Iterator that polls the a Kafka topic regularily for metric data
    Args:
        kafka_consumer (kafka.KafkaConsumer): An initialized KafkaConsumer object
    """
    while True:
        logger.info('Polling Kafka topics')
        raw_msgs = kafka_consumer.poll(timeout_ms=1000*60) # Wait for a min
        logger.info('Got response for %s topics', len(raw_msgs.keys()))
        for topic, msgs in raw_msgs.items():
            logger.info('Processing %s messages for topic %s', len(msgs), topic)
            for msg in msgs:
                try:
                    logger.info('Processing message %s', msg.value)
                    msg_dict = json.loads(msg.value)
                except JSONDecodeError:
                    logger.error('Could JSON parse the message %s', msg)
                try:
                    validate(msg_dict, schema=message_schema)
                    yield msg_dict
                except ValidationError:
                    logger.error('Incorrect schema in message %s', msg_dict)

def consume(cursor, kafka_consumer: KafkaConsumer, table: str, batch_size: int)->None:
    """Poll kafka_counsumer continously and write to DB

    Args:
        cursor: A psycopg2 cursor previously initialized
        kafka_consumer (kafka.KafkaConsumer): A previously intialized KafkaConsumer obj.

    """
    while True:
        try:
            extras.execute_batch(cursor,
                f"""
                    INSERT INTO {table}(address, latency, is_valid, status_code)
                    VALUES(
                        %(address)s,
                        %(latency)s,
                        %(is_valid)s,
                        %(status_code)s
                    )
                """,
                message_iter(kafka_consumer),
                page_size=batch_size
            )
            kafka_consumer.commit()
        except psycopg2.DataError as ex:
            logger.error(ex)

def main(kafka_config, db_config):
    """Initialize kafka consumer and db config object and run consume"""
    _kafka_consumer = KafkaConsumer(
        kafka_config.topic,
        bootstrap_servers=kafka_config.bootstrap_servers,
        security_protocol="SSL",
        ssl_cafile=kafka_config.ssl_cafile,
        ssl_certfile=kafka_config.ssl_certfile,
        ssl_keyfile=kafka_config.ssl_keyfile,
    )

    with psycopg2.connect(
        dbname=db_config.name,
        user=db_config.user,
        password=db_config.password,
        host=db_config.host,
        port=db_config.port,
        sslmode='require'
    ) as conn:
        conn.autocommit=True
        with conn.cursor() as _cursor:
            _batch_size = int(os.environ.get('DB_BATCH_SIZE', '100'))
            _table = os.environ.get('DB_TABLE')
            consume(_cursor, _kafka_consumer, _table, _batch_size)
