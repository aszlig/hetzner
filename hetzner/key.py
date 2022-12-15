import datetime


class Key:
    name: str
    fingerprint: str
    size: int
    data: str
    created_at: datetime.datetime

    def __init__(self, conn, fingerprint: str = None, data: dict = None):
        super(Key, self).__init__()
        self._conn = conn

        if data is None:
            self.fingerprint = fingerprint
        else:
            self.update_info(data)

    def update_info(self, result=None):
        if result is None:
            result = self._conn.request("get", f"/key/{self.fingerprint}")

        data = result["key"]

        for key in ("name", "fingerprint", "size", "data"):
            setattr(self, key, data[key])
        self.created_at = datetime.datetime.strptime(data['created_at'], '%Y-%m-%dT%H:%M:%S.%fZ')

    def rename(self, new_name: str):
        return self._conn.request('POST', f"/key/{self.fingerprint}", {"name": new_name})

    def __repr__(self):
        return f"<Key {self.name}:{self.fingerprint}>"
