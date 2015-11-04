import os
import ssl
import socket

from tempfile import NamedTemporaryFile

try:
    from httplib import HTTPSConnection
except ImportError:
    from http.client import HTTPSConnection


class ValidatedHTTPSConnection(HTTPSConnection):
    # GeoTrust Global CA
    CA_ROOT_CERT_FALLBACK = '''
    -----BEGIN CERTIFICATE-----
    MIIDVDCCAjygAwIBAgIDAjRWMA0GCSqGSIb3DQEBBQUAMEIxCzAJBgNVBAYTAlVTMRYwFAYDVQQ
    KEw1HZW9UcnVzdCBJbmMuMRswGQYDVQQDExJHZW9UcnVzdCBHbG9iYWwgQ0EwHhcNMDIwNTIxMD
    QwMDAwWhcNMjIwNTIxMDQwMDAwWjBCMQswCQYDVQQGEwJVUzEWMBQGA1UEChMNR2VvVHJ1c3QgS
    W5jLjEbMBkGA1UEAxMSR2VvVHJ1c3QgR2xvYmFsIENBMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A
    MIIB CgKCAQEA2swYYzD99BcjGlZ+W988bDjkcbd4kdS8odhM+KhDtgPpTSEHCIjaWC9mOSm9BX
    iLnTjoBbdqfnGk5sRgprDvgOSJKA+eJdbtg/OtppHHmMlCGDUUna2YRpIuT8rxh0PBFpVXLVDvi
    S2Aelet 8u5fa9IAjbkU+BQVNdnARqN7csiRv8lVK83Qlz6cJmTM386DGXHKTubU1XupGc1V3sj
    s0l44U+VcT4wt/lAjNvxm5suOpDkZALeVAjmRCw7+OC7RHQWa9k0+bw8HHa8sHo9gOeL6NlMTOd
    ReJivbPagUvTLrGAMoUgRx5aszPeE4uwc2hGKceeoWMPRfwCvocWvk+QIDAQABo1MwUTAPBgNVH
    RMBAf8EBTADAQH/MB0GA1UdDgQWBBTAephojYn7qwVkDBF9qn1luMrMTjAfBgNVHSMEGDAWgBTA
    ephojYn7qwVkDBF9qn1luMrMTjANBgkqhkiG9w0BAQUFAAOCAQEANeMpauUvXVSOKVCUn5kaFOS
    PeCpilKInZ57QzxpeR+nBsqTP3UEaBU6bS+5Kb1VSsyShNwrrZHYqLizz/Tt1kL/6cdjHPTfStQ
    WVYrmm3ok9Nns4d0iXrKYgjy6myQzCsplFAMfOEVEiIuCl6rYVSAlk6l5PdPcFPseKUgzbFbS9b
    ZvlxrFUaKnjaZC2mqUPuLk/IH2uSrW4nOQdtqvmlKXBx4Ot2/Unhw4EbNX/3aBd7YdStysVAq45
    pmp06drE57xNNB6pXE0zX5IJL4hmXXeXxx12E6nV5fEWCRE11azbJHFwLJhWC9kXtNHjUStedej
    V0NxPNO3CBWaAocvmMw==
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
