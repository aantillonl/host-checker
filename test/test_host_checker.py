from unittest import mock
import re
from host_checker import host_checker
from kafka import KafkaProducer

def mocked_requests_get(*args, **kwargs):
    class MockResponse:
        def __init__(self, text, status_code):
            self._text = text
            self.status_code = status_code
        
        @property
        def text(self):
            return self._text

    return MockResponse("{'content': 'test'}", 200)

@mock.patch('requests.get', side_effect=mocked_requests_get)
def test_get_health_status(mock_get):
    status = host_checker.get_health_status('https://test-host.com')
    assert type(status) == host_checker.HealthStatus

@mock.patch('requests.get', side_effect=mocked_requests_get)
def test_check_and_publish_metric(mock_get):
    kafka_mock = mock.MagicMock(spec=KafkaProducer)
    host_checker.check_and_publish_metric('https://test-host.com', kafka_mock, 'test-topic')
    kafka_mock.send.assert_called_once_with('test-topic', mock.ANY)


@mock.patch('requests.get', side_effect=mocked_requests_get)
def test_get_health_status_with_validation(mock_get):
    validation_regex = mock.MagicMock(wraps=re.compile(".*")) # Match anything
    status = host_checker.get_health_status('https://test-host.com', validation_regex)
    validation_regex.match.assert_called_once()
    assert status.is_valid
