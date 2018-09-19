import os
import ssl
import socket

from tempfile import NamedTemporaryFile

try:
    from httplib import HTTPSConnection
except ImportError:
    from http.client import HTTPSConnection


class ValidatedHTTPSConnection(HTTPSConnection):
    CA_ROOT_CERT_FALLBACK = '''
        DigiCert Global Root G2
        -----BEGIN CERTIFICATE-----
        MIIDjjCCAnagAwIBAgIQAzrx5qcRqaC7KGSxHQn65TANBgkqhkiG9w0BAQsFADBh
        MQswCQYDVQQGEwJVUzEVMBMGA1UEChMMRGlnaUNlcnQgSW5jMRkwFwYDVQQLExB3
        d3cuZGlnaWNlcnQuY29tMSAwHgYDVQQDExdEaWdpQ2VydCBHbG9iYWwgUm9vdCBH
        MjAeFw0xMzA4MDExMjAwMDBaFw0zODAxMTUxMjAwMDBaMGExCzAJBgNVBAYTAlVT
        MRUwEwYDVQQKEwxEaWdpQ2VydCBJbmMxGTAXBgNVBAsTEHd3dy5kaWdpY2VydC5j
        b20xIDAeBgNVBAMTF0RpZ2lDZXJ0IEdsb2JhbCBSb290IEcyMIIBIjANBgkqhkiG
        9w0BAQEFAAOCAQ8AMIIBCgKCAQEAuzfNNNx7a8myaJCtSnX/RrohCgiN9RlUyfuI
        2/Ou8jqJkTx65qsGGmvPrC3oXgkkRLpimn7Wo6h+4FR1IAWsULecYxpsMNzaHxmx
        1x7e/dfgy5SDN67sH0NO3Xss0r0upS/kqbitOtSZpLYl6ZtrAGCSYP9PIUkY92eQ
        q2EGnI/yuum06ZIya7XzV+hdG82MHauVBJVJ8zUtluNJbd134/tJS7SsVQepj5Wz
        tCO7TG1F8PapspUwtP1MVYwnSlcUfIKdzXOS0xZKBgyMUNGPHgm+F6HmIcr9g+UQ
        vIOlCsRnKPZzFBQ9RnbDhxSJITRNrw9FDKZJobq7nMWxM4MphQIDAQABo0IwQDAP
        BgNVHRMBAf8EBTADAQH/MA4GA1UdDwEB/wQEAwIBhjAdBgNVHQ4EFgQUTiJUIBiV
        5uNu5g/6+rkS7QYXjzkwDQYJKoZIhvcNAQELBQADggEBAGBnKJRvDkhj6zHd6mcY
        1Yl9PMWLSn/pvtsrF9+wX3N3KjITOYFnQoQj8kVnNeyIv/iPsGEMNKSuIEyExtv4
        NeF22d+mQrvHRAiGfzZ0JFrabA0UWTW98kndth/Jsw1HKj2ZL7tcu7XUIOGZX1NG
        Fdtom/DzMNU+MeKNhJ7jitralj41E6Vf8PlwUHBHQRFXGU7Aj64GxJUTFy8bJZ91
        8rGOmaFvE7FBcf6IKshPECBV1/MUReXgRPTqh5Uykw7+U0b6LJ3/iyK5S9kJRaTe
        pLiaWN0bfVKfjllDiIGknibVb63dDcY3fe0Dkhvld1927jyNxF1WW6LZZm6zNTfl
        MrY=
        -----END CERTIFICATE-----
    '''

    def get_ca_cert_bundle(self):
        via_env = os.getenv('SSL_CERT_FILE')
        if via_env is not None and os.path.exists(via_env):
            return via_env
        probe_paths = [
            "/etc/ssl/certs/ca-certificates.crt",
            "/etc/ssl/certs/ca-bundle.crt",
            "/etc/pki/tls/certs/ca-bundle.crt",
        ]
        for path in probe_paths:
            if os.path.exists(path):
                return path
        return None

    def connect(self):
        sock = socket.create_connection((self.host, self.port),
                                        self.timeout,
                                        self.source_address)
        bundle = cafile = self.get_ca_cert_bundle()
        if bundle is None:
            ca_certs = NamedTemporaryFile()
            ca_certs.write('\n'.join(
                map(str.strip, self.CA_ROOT_CERT_FALLBACK.splitlines())
            ).encode('ascii'))
            ca_certs.flush()
            cafile = ca_certs.name
        self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file,
                                    cert_reqs=ssl.CERT_REQUIRED,
                                    ca_certs=cafile)
        if bundle is None:
            ca_certs.close()
