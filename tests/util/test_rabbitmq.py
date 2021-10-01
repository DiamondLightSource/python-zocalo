import zocalo.configuration
from zocalo.util.rabbitmq import http_api_request


def test_http_api_request(mocker):
    zc = mocker.MagicMock(zocalo.configuration.Configuration)
    zc.rabbitmqapi = {
        "base_url": "http://rabbitmq.burrow.com:12345/api",
        "username": "carrots",
        "password": "carrots",
    }
    request = http_api_request(zc, api_path="/queues")
    assert request.get_full_url() == "http://rabbitmq.burrow.com:12345/api/queues"
