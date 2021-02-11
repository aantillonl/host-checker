"""Utility classes and functions for health_checker"""
import os
from dataclasses import dataclass

@dataclass
class KafkaConfig:
    """Holds config data to initiate a KafkaConsumer or KafkaProducer"""
    bootstrap_servers: str
    topic: str
    ssl_cafile: str
    ssl_certfile: str
    ssl_keyfile: str

@dataclass
class DbConfig:
    """Holds config data to initiate a db connection"""
    host: str
    name: str
    user: str
    password: str
    table: str
    port: int
@dataclass
class HostMetric:
    """Data class to hold health metric data"""
    address: str
    latency: float
    status_code: int
    is_valid: bool = False

def get_kafka_config()->KafkaConfig:
    """Validates all necessary env variables exist to create a KafkaConfig object"""
    kafka_env_variables = [
        'KAFKA_BOOTSTRAP_SERVERS',
        'KAFKA_TOPIC',
        'KAFKA_SSL_CA_FILE',
        'KAFKA_SSL_CERT_FILE',
        'KAFKA_SSL_KEY_FILE'
    ]
    if not all([os.environ.get(var, False) for var in kafka_env_variables]):
        raise Exception('Unset Kafka config environment variables')
    return KafkaConfig(
        os.environ.get('KAFKA_BOOTSTRAP_SERVERS'),
        os.environ.get('KAFKA_TOPIC'),
        os.environ.get('KAFKA_SSL_CA_FILE'),
        os.environ.get('KAFKA_SSL_CERT_FILE'),
        os.environ.get('KAFKA_SSL_KEY_FILE')
    )

def get_db_config()->DbConfig:
    """Check DB env variables and return a DbConfig object"""
    db_env_variables = [
        'DB_HOST',
        'DB_NAME',
        'DB_TABLE',
        'DB_USER',
        'DB_PASSWORD',
        'DB_PORT',
    ]

    if not all([os.environ.get(var, False) for var in db_env_variables]):
        raise Exception('Unset db config environment variables')
    return DbConfig(
        os.environ.get('DB_HOST'),
        os.environ.get('DB_NAME'),
        os.environ.get('DB_USER'),
        os.environ.get('DB_PASSWORD'),
        os.environ.get('DB_TABLE'),
        os.environ.get('DB_PORT')
    )
