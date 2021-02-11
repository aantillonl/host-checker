"""Tests for consumer.py"""
from unittest import mock
from dataclasses import dataclass
import json
import pytest
from kafka import KafkaConsumer
from host_metrics import consumer

@dataclass
class KafkaRecord:
    """Mock class for Kafka records"""
    value:str

@pytest.fixture
def kafka_msg():
    """"Text kafka message fixutre"""
    test_metric = {
        'latency': 0.1,
        'status_code': 200,
        'is_valid': True,
        'address': 'example.com'
    }
    return KafkaRecord(json.dumps(test_metric))

@pytest.fixture
def kafka_consumer():
    """Kafka consumer fixture"""
    return mock.MagicMock(spec=KafkaConsumer)

def test_message_iter(kafka_msg):
    """Test the messages iterator"""
    kafka_consumer = mock.MagicMock(spec=KafkaConsumer)

    test_response = {'test_topic': [kafka_msg]}
    kafka_consumer.poll = mock.MagicMock(return_value=test_response)

    metric = next(consumer.message_iter(kafka_consumer))
    assert metric['latency'] == 0.1
    assert metric['status_code'] == 200
    assert metric['is_valid'] == True
    assert metric['address'] == 'example.com'

def test_message_iter_handle_invalid_schema(kafka_msg, caplog):
    """Test message iterator skips messages with invalid schema"""
    test_response = {'test_topic': [
        KafkaRecord(json.dumps({"invalidProp": "invalidValue"})),
        kafka_msg
    ]}
    kafka_consumer.poll = mock.MagicMock(return_value=test_response)

    metric = next(consumer.message_iter(kafka_consumer))
    assert metric['status_code'] == 200
    assert 'Incorrect schema' in caplog.text
