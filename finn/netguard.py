"""Every connection the web API opens must go to a public address.

Installed by finn/webapi.py, so it guards the serverless functions only; the batch build never imports it.
It replaces urllib3's create_connection, which requests uses for every connection: the host is resolved
here (IPv4 only), every address must be public, and the socket is opened to the checked address itself,
so a name that resolves to a public address for the check and a private one for the connect can't slip
through. TLS still verifies the certificate against the host name, which urllib3 passes separately.
"""
import ipaddress, socket
import urllib3.util.connection as uconn


class Blocked(OSError):
    pass


resolve = socket.getaddrinfo   # swapped in tests
original = None                # urllib3's own create_connection, looked up at call time so tests can swap it


def create_connection(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None, socket_options=None):
    host, port = address
    try:
        infos = resolve(host, port, socket.AF_INET, socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise Blocked(f"cannot resolve {host} as IPv4") from e
    ips = [info[4][0] for info in infos]
    if not ips or not all(ipaddress.ip_address(ip).is_global for ip in ips):
        raise Blocked(f"{host} is not a public address")
    return original((ips[0], port), timeout, source_address, socket_options)


def install():
    global original
    if uconn.create_connection is not create_connection:
        original = uconn.create_connection
        uconn.create_connection = create_connection
