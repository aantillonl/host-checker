"""Checks health of an http host according to its configuration"""
import argparse
from dataclasses import dataclass
import functools
import threading
import time
import re
import requests
import schedule
from kafka import KafkaProducer

def _run_threaded(job_func, **args):
    job_thread = threading.Thread(target=job_func, **args)
    job_thread.start()

@dataclass
class HealthStatus:
    status_code: int
    latency: float
    validated: bool = False
    is_valid: bool = None

def validate(content: str):
    return True

def get_health_status(host:str, validation_regex: re.Pattern = None) -> HealthStatus:
    """Send health check request to host"""
    start = time.thread_time()
    res = requests.get(host)
    end = time.thread_time()
    latency = end - start
    if validation_regex:
        return HealthStatus(
            res.status_code, latency, validated=True,
            is_valid=True if validation_regex.match(res.text) else False
        )
    return HealthStatus(res.status_code, latency)

def check_and_publish_metric(host: str, kafka_client: KafkaProducer, topic:str) -> None:
    metric = get_health_status(host)
    kafka_client.send(topic, metric)

def _init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        usage="%(prog)s [OPTION] [HOST]...",
        description="Schedule periodic health checks for a web host."
    )
    parser.add_argument(
        "-v", "--version", action="version",
        version = f"{parser.prog} version 1.0.0"
    )
    parser.add_argument(
        "-k", "--kafka-server",
        help='Address of the Kafka stream where metrics are pushed to.',
        type=str
    )
    parser.add_argument(
        "-f", "--frequency", default=10,
        help='Frequency to perform health checks in minutes.',
        type=int
    )
    parser.add_argument('hosts', nargs=argparse.REMAINDER)
    return parser


def main(hosts, frequency, kafka_client):
    for host in hosts:
        schedule.every(frequency).minutes.do(_run_threaded, check_and_publish_metric, host)

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    parser = _init_argparse()
    args = parser.parse_args()    
    kafka_client = KafkaProducer(bootstrap_servers=args.kafka_server)    
    main(args.hosts, args.frequency, kafka_client)
