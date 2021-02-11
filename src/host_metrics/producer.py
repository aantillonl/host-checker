"""Checks health of an http host according to its configuration"""
from dataclasses import dataclass, asdict
from functools import partial
import logging
import json
from queue import Queue
import threading
import time
import re
import os
from typing import List, TextIO
import requests
import schedule
from kafka import KafkaProducer
from .utils import HostMetric

logger = logging.getLogger('HostChecker')
logging.basicConfig(level=os.environ.get('LOG_LEVEL', 'INFO'))
default_regex = re.compile('.*')

@dataclass
class HealthCheckConfig:
    """Data class to hold the configuration for a scheduled health check"""
    address: str
    frequency: int
    validation_regex: re.Pattern = re.compile('.*')


def get_health_metric(
        address: str,
        validation_regex: re.Pattern = default_regex
    ) -> HostMetric:
    """Send health check request to host
    Args:
        address (str): Address of the web host to check and get health metrics for
        validation_regex (re.Pattern): A Re.Pattern compiled regex to validate the response content.

    Returns:
        bool: The return value. True for success, False otherwise.
    """
    start = time.time()
    logger.info('Requesting content from %s', address)
    res = requests.get(address)
    latency = time.time() - start
    logger.info(
        'Response from %s received after %s, with status_code %s',
        address, latency, res.status_code
    )
    metric = HostMetric(address, latency, res.status_code)
    metric.is_valid = bool(validation_regex.match(res.text))

    return metric

def get_host_health_and_publish_metric(
        kafka_client: KafkaProducer,
        topic: str,
        address: str,
        validation_regex: re.Pattern = default_regex
    ) -> None:
    """Get a web host status and push a health metric to the kafka client
    Args:
        kafka_client (KafkaProducer): An initialized Kafka producer object
        topic (str): Name of the topic to publish the metrics to
        address (str): Address of the web host to check and get health metrics for
        validation_regex (re.Pattern): A Re.Pattern compiled regex to validate the response content.
    """
    metric = get_health_metric(address, validation_regex)
    logger.info('Sending metric of %s to Kafka topic %s', address, topic)
    kafka_client.send(topic, key=address.encode('utf-8'), value= metric)

def worker_main(jobqueue: Queue)-> None:
    """Checks a queue periodically jor scheduled jobs and executes jobs in a separate thread
    Args:
        jobqueue (queue.Queue): A queue where jobs are pushed to by the scheduler function
    """
    while 1:
        job_func = jobqueue.get()
        threading.Thread(target=job_func).start()
        jobqueue.task_done()
        time.sleep(1)

def produce(kafka_client: KafkaProducer, topic: str, host_configs: List[HealthCheckConfig])->None:
    """Schedule health checks and run a worker in a daemon to perform the health checks
    Args:
        kafka_client (KafkaProducer): An initialized Kafka producer object
        topic (str): Name of the topic to publish the metrics to
        host_configs (List[HealthCheckConfig]): A list with health check configuration objects
    """
    jobqueue: Queue = Queue()
    for host_config in host_configs:
        logger.info(
            'Scheduling checks for %s every %s minutes',
            host_config.address, host_config.frequency
        )
        schedule.every(host_config.frequency).minutes.do(
            jobqueue.put,
            partial(
                get_host_health_and_publish_metric,
                kafka_client=kafka_client,
                topic=topic,
                address=host_config.address,
                validation_regex=host_config.validation_regex
            )
        )

    worker_thread = threading.Thread(target=worker_main, args=[jobqueue], daemon=True)
    worker_thread.start()

    try:
        while schedule.jobs:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Keyboard Interrupt detected, flushing and exiting program")
    finally:
        kafka_client.flush()

def parse_config(file: TextIO) -> List[HealthCheckConfig]:
    """Parses a config file from a file object

    The config file should contain on each line the following values:
    * Web host addres with protocol. e.g. 'https://google.com'
    * A frequency value in minutes, used to scheduled health checks. e.g. '5'
      to schedule a check every 5 minutes
    * Optionally a regex to check against the host response's content
      e.g '<title>Google</title>'
    Args:
        file (typing.TextIO): A file-like object to read configuration lines from
    """
    host_configs = []
    for line in file:
        values = line.split()
        host_config = HealthCheckConfig(
            values[0],
            int(values[1])
        )
        if len(values) == 3:
            host_config.validation_regex = re.compile(values[2])
        else:
            host_config.validation_regex = default_regex
        host_configs.append(host_config)

    return host_configs

def main(kafka_config, host_configs):
    """Init producer and run produce"""
    kafka_producer = KafkaProducer(
        bootstrap_servers=kafka_config.bootstrap_servers,
        value_serializer=lambda metric: json.dumps(asdict(metric)).encode('utf-8'),
        security_protocol='SSL',
        ssl_check_hostname=True,
        ssl_cafile=kafka_config.ssl_cafile,
        ssl_certfile=kafka_config.ssl_certfile,
        ssl_keyfile=kafka_config.ssl_keyfile
    )
    produce(kafka_producer, os.environ.get('KAFKA_TOPIC'), host_configs)
