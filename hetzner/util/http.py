import ssl
import socket

from tempfile import NamedTemporaryFile

try:
    from httplib import HTTPSConnection
except ImportError:
    from http.client import HTTPSConnection


class ValidatedHTTPSConnection(HTTPSConnection):
    # Thawte Premium Server CA
    CA_ROOT_CERT = '''
    -----BEGIN CERTIFICATE-----
    MIIDJzCCApCgAwIBAgIBATANBgkqhkiG9w0BAQQFADCBzjELMAkGA1UEBhMCWkExFTATBgNVBAg
    TDFdlc3Rlcm4gQ2FwZTESMBAGA1UEBxMJQ2FwZSBUb3duMR0wGwYDVQQKExRUaGF3dGUgQ29uc3
    VsdGluZyBjYzEoMCYGA1UECxMfQ2VydGlmaWNhdGlvbiBTZXJ2aWNlcyBEaXZpc2lvbjEhMB8GA
    1UEAxMYVGhhd3RlIFByZW1pdW0gU2VydmVyIENBMSgwJgYJKoZIhvcNAQkBFhlwcmVtaXVtLXNl
    cnZlckB0aGF3dGUuY29tMB4XDTk2MDgwMTAwMDAwMFoXDTIwMTIzMTIzNTk1OVowgc4xCzAJBgN
    VBAYTAlpBMRUwEwYDVQQIEwxXZXN0ZXJuIENhcGUxEjAQBgNVBAcTCUNhcGUgVG93bjEdMBsGA1
    UEChMUVGhhd3RlIENvbnN1bHRpbmcgY2MxKDAmBgNVBAsTH0NlcnRpZmljYXRpb24gU2VydmljZ
    XMgRGl2aXNpb24xITAfBgNVBAMTGFRoYXd0ZSBQcmVtaXVtIFNlcnZlciBDQTEoMCYGCSqGSIb3
    DQEJARYZcHJlbWl1bS1zZXJ2ZXJAdGhhd3RlLmNvbTCBnzANBgkqhkiG9w0BAQEFAAOBjQAwgYk
    CgYEA0jY2aovXwlue2oFBYo847kkEVdbQ7xwblRZH7xhINTpS9CtqBo87L+pW46+GjZ4X9560ZX
    UCTe/LCaIhUdib0GfQug2SBhRz1JPLlyoAnFxODLz6FVL88kRu2hFKbgifLy3j+ao6hnO2RlNYy
    IkFvYMRuHM/qgeN9EJN50CdHDcCAwEAAaMTMBEwDwYDVR0TAQH/BAUwAwEB/zANBgkqhkiG9w0B
    AQQFAAOBgQAmSCwWwlj66BZ0DKqqX1Q/8tfJeGBeXm43YyJ3Nn6yF8Q0ufUIhfzJATj/Tb7yFkJ
    D57taRvvBxhEf8UqwKEbJw8RCfbz6q1lu1bdRiBHjpIUZa4JMpAwSremkrj/xw0llmozFyD4lt5
    SZu5IycQfwhl7tUCemDaYj+bvLpgcUQg==
    -----END CERTIFICATE-----
    '''

    def connect(self):
        sock = socket.create_connection((self.host, self.port),
                                        self.timeout,
                                        self.source_address)
        ca_certs = NamedTemporaryFile()
        ca_certs.write('\n'.join(
            map(str.strip, self.CA_ROOT_CERT.splitlines())
        ).encode('ascii'))
        ca_certs.flush()
        self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file,
                                    cert_reqs=ssl.CERT_REQUIRED,
                                    ca_certs=ca_certs.name)
        ca_certs.close()
