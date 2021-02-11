"""Tests for health metrics module"""
from unittest import mock
import re
import time
import os
from kafka import KafkaProducer
import pytest
import schedule
from host_metrics import producer
from host_metrics.utils import HostMetric, get_kafka_config, KafkaConfig

@pytest.fixture(scope='function', autouse=True)
def schedule_fix():
    """Clear scheduled jobs before every test"""
    schedule.clear()

class MockResponse:
    """Response class similar requests.Response"""
    def __init__(self, text: str = 'hello world', status_code: int = 200):
        self._text = text
        self.status_code = status_code

    @property
    def text(self):
        """returns _text field"""
        return self._text

@pytest.fixture(scope='function', autouse=True)
def mock_get():
    """Fixture to mock requests.get with a MockResponse class"""
    with mock.patch('requests.get', return_value=MockResponse()) as _fixture:
        yield _fixture

@pytest.fixture(scope='function')
def kafka_mock():
    """Create a mock object used as a KafkaProducer object"""
    return mock.MagicMock(spec=KafkaProducer)

@pytest.fixture(autouse=True)
def schedule_run_pending_fixture():
    """Stub schedule.run_pending, to run all existing jobs regardless of their schedule
    This enables quicker testing since it is not necessary to wait untill the scheduled
    time comes.
    """
    def side_effect():
        schedule.run_all()
        schedule.clear()
    with mock.patch('schedule.run_pending', side_effect=side_effect) as run_pending_mock:
        yield run_pending_mock


def test_get_health_status():
    """Test the basic function get_health_status"""
    health_metric = producer.get_health_metric('example.com')
    assert health_metric.status_code == 200

def test_get_host_health_and_publish_metric(kafka_mock):
    """Test get_host_health_and_publish_metric which wraps get_health_status and
    and pushes a metric to the Kafka client"""
    producer.get_host_health_and_publish_metric(
        kafka_mock,
        'test-topic',
        'example.com'
    )
    expected_metric = HostMetric('example.com', mock.ANY, 200, True)
    kafka_mock.send.assert_called_once_with(
        'test-topic',
        key=b'example.com',
        value=expected_metric
    )

def test_get_health_status_with_validation():
    """Test getting a health metric and validating the response content with a regex"""
    validation_regex = mock.MagicMock(wraps=re.compile(".*")) # Match anything
    metric = producer.get_health_metric('example.com', validation_regex)
    validation_regex.match.assert_called_once()
    assert metric.is_valid

def test_parse_config():
    """Test config parsing"""
    with open('src/tests/data/test_config', 'r') as file:
        host_configs = producer.parse_config(file)
    assert len(host_configs) == 2
    assert host_configs[0].address == 'example.com'
    assert host_configs[0].frequency == 5

def test_get_kafka_config(monkeypatch):
    monkeypatch.setenv('KAFKA_BOOTSTRAP_SERVERS', 'test-kafka:12358')
    monkeypatch.setenv('KAFKA_TOPIC', 'test_topic')
    monkeypatch.setenv('KAFKA_SSL_CA_FILE', 'test_ca_file')
    monkeypatch.setenv('KAFKA_SSL_CERT_FILE', 'test_cert_file')
    monkeypatch.setenv('KAFKA_SSL_KEY_FILE', 'test_key_file')

    kafka_config = get_kafka_config()
    expected_kafka_config = KafkaConfig(
        'test-kafka:12358',
        'test_topic',
        'test_ca_file',
        'test_cert_file',
        'test_key_file'
    )
    assert kafka_config == expected_kafka_config

def test_get_kafka_config_without_env(monkeypatch):
    monkeypatch.setattr(os, 'environ', {})
    
    with pytest.raises(Exception):
        get_kafka_config()

def test_main(kafka_mock):
    """Test the producer's main founction"""
    host_config = producer.HealthCheckConfig('example.com', 5)
    producer.produce(kafka_mock, 'test-topic', [host_config])
    kafka_mock.send.assert_called_once()

def test_slow_website(kafka_mock, mock_get):
    """Test when a website takes long to reply"""
    def slow_response(*args):
        if args[0] == 'slow-website.com':
            time.sleep(1)
        return MockResponse()
    mock_get.side_effect = slow_response
    host_configs = [
        producer.HealthCheckConfig('example.com', 5),
        producer.HealthCheckConfig('slow-website.com', 5)
    ]

    producer.produce(kafka_mock, 'test-topic', host_configs)
    time.sleep(2) # Allow time for the request to slow-website.com to return

    assert kafka_mock.send.call_count == 2
    exapmple_com_metric = kafka_mock.send.call_args_list[0][1]['value']
    slow_website_com_metric = kafka_mock.send.call_args_list[1][1]['value']

    assert exapmple_com_metric.latency < 1
    assert slow_website_com_metric.latency >= 1
