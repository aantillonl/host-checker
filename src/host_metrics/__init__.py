"""Main hook for cli commands"""
import argparse
import sys
from .utils import get_db_config, get_kafka_config
from . import consumer
from . import producer

def run():
    """Run cli"""
    parser = argparse.ArgumentParser(
        usage="%(prog)s command [CONFIG]...",
        description="Schedule periodic health checks for a web host."
    )
    parser.add_argument(
        "-v", "--version", action="version",
        version = f"{parser.prog} version 1.0.0"
    )

    parser.add_argument(
        "command", type=str, choices=['produce', 'consume'],
        help='produce or consume metrics'
    )

    parser.add_argument(
        "-c", "--config", type=str,
        help='Path to config file. Set to "-" for stdin'
    )

    args = parser.parse_args()
    kafka_config = get_kafka_config()

    if args.command == 'produce':
        if args.config == '-':
            host_configs = producer.parse_config(sys.stdin)
        else:
            with open(args.config, 'r') as file:
                host_configs = producer.parse_config(file)
        producer.main(kafka_config, host_configs)

    if args.command == 'consume':
        db_config = get_db_config()
        consumer.main(kafka_config, db_config)
