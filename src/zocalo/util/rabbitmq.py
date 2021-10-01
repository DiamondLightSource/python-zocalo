import urllib.request

import zocalo.configuration


def http_api_request(
    zc: zocalo.configuration.Configuration,
    api_path: str,
) -> urllib.request.Request:
    """
    Return a urllib.request.Request to query the RabbitMQ HTTP API.

    Credentials are obtained via zocalo.configuration.

    Args:
        zc (zocalo.configuration.Configuration): Zocalo configuration object
        api_path (str): The path to be combined with the base_url defined by
            the Zocalo configuration object to give the full path to the API
            endpoint.
    """
    if not zc.rabbitmqapi:
        raise zocalo.ConfigurationError(
            "There are no RabbitMQ API credentials configured in your environment"
        )
    password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    password_mgr.add_password(
        realm=None,
        uri=zc.rabbitmqapi["base_url"],
        user=zc.rabbitmqapi["username"],
        passwd=zc.rabbitmqapi["password"],
    )
    handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
    opener = urllib.request.build_opener(handler)
    urllib.request.install_opener(opener)
    return urllib.request.Request(f"{zc.rabbitmqapi['base_url']}{api_path}")
