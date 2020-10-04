import logging

from datetime import datetime

__all__ = ['StorageBox', 'SubAccount', 'SubAccountManager']


class SubAccount(object):
    def __init__(self, conn, box_id_, result):
        self.conn = conn
        self.box_id_ = box_id_
        self.update_info(result)

    def update_info(self, result):
        """
        Update the information of the subaccount.
        """
        data = result['subaccount']

        self.username = data['username']
        self.accountid = data['accountid']
        self.server = data['server']
        self.homedirectory = data['homedirectory']
        self.samba = data['samba']
        self.ssh = data['ssh']
        self.external_reachability = data['external_reachability']
        self.webdav = data['webdav']
        self.readonly = data['readonly']
        self.createtime = datetime.strptime(data['createtime'], '%Y-%m-%d %H:%M:%S')
        self.comment = data['comment']

    def update(self, homedirectory, samba, ssh, external_reachability, webdav, readonly, comment):
        path = f'/storagebox/{self.box_id_}/subaccount/{self.username}'
        data = {'homedirectory': homedirectory,
             'samba': samba,
             'ssh': ssh,
             'external_reachability': external_reachability,
             'webdav': webdav,
             'readonly': readonly,
             'comment': comment}
        return self.conn.put(path, data)

    def reset_password(self):
        data = f'/storagebox/{self.box_id_}/subaccount/{self.username}/password'
        result = self.conn.post(data, None)
        return result['password']

    def delete(self):
        self.conn.delete('/storagebox/{0}/subaccount/{1}'.format(self.box_id_, self.username))

    def __repr__(self):
        return "<SubAccount {0}>".format(self.username)


class SubAccountManager(object):
    def __init__(self, conn, box_id_):
        self.conn = conn
        self.box_id_ = box_id_

    def create(self, homedirectory, samba, ssh, external_reachability, webdav, readonly, comment):
        result = self.conn.post('/storagebox/{0}/subaccount'.format(self.box_id_),
                                {'homedirectory': homedirectory,
                                 'samba': samba,
                                 'ssh': ssh,
                                 'external_reachability': external_reachability,
                                 'webdav': webdav,
                                 'readonly': readonly,
                                 'comment': comment})

        return result

    def delete(self, username):
        self.conn.delete('/storagebox/{0}/subaccount/{1}'.format(self.box_id_, username))

    def __iter__(self):
        return iter([SubAccount(self.conn, self.box_id_, s) for s in self.conn.get('/storagebox/{0}/subaccount'.format(self.box_id_))])


class StorageBox(object):
    def __init__(self, conn, result):
        self.conn = conn
        self.update_info(result)
        self.subaccounts = SubAccountManager(self.conn, self.id_)
        self.logger = logging.getLogger("StorageBox #{0}".format(self.id_))

    def update_info(self, result=None):
        """
        Updates the information of the current SubAccount instance either by
        sending a new GET request or by parsing the response given by result.
        """
        if result is None:
            result = self.conn.get('/storagebox/{0}'.format(self.id_))
        data = result['storagebox']

        self.id_ = data['id']
        self.login = data['login']
        self.name = data['name']
        self.product = data['product']
        self.cancelled = data['cancelled']
        self.locked = data['locked']
        self.location = data['location']
        self.linked_server = data['linked_server']
        self.paid_until = datetime.strptime(data['paid_until'], '%Y-%m-%d')
        if 'disk_quota' in data:
            self.disk_quota = data['disk_quota']
            self.disk_usage = data['disk_usage']
            self.disk_usage_data = data['disk_usage_data']
            self.disk_usage_snapshots = data['disk_usage_snapshots']
            self.webdav = data['webdav']
            self.samba = data['samba']
            self.ssh = data['ssh']
            self.external_reachability = data['external_reachability']
            self.zfs = data['zfs']
            self.server = data['server']
            self.host_system = data['host_system']

    def __repr__(self):
        return "<{0} (#{1} {2})>".format(self.login, self.id_, self.product)
