# -*- coding: utf-8 -*-

import os
import hmac
import time
import json
import mimetypes
import functools
import hashlib
from urlparse import urlparse
from urllib import urlencode
from base64 import urlsafe_b64encode


import requests

version_info = (0, 2, 0)
VERSION = __version__ = '.'.join( map(str, version_info) )


"""
Usage:
cow = Cow(ACCESS_KEY, SECRET_KEY)
b = cow.get_bucket(BUCKET)
b.put('a')
b.stat('a')
b.delete('a')
b.copy('a', 'c')
b.move('a', 'c')
"""



RS_HOST = 'http://rs.qbox.me'
UP_HOST = 'http://up.qbox.me'
RSF_HOST = 'http://rsf.qbox.me'


class CowException(Exception):
    def __init__(self, url, status_code, content):
        self.url = url
        self.status_code = status_code
        self.content = content
        Exception.__init__(self, content)



def signing(secret_key, data):
    return urlsafe_b64encode(
        hmac.new(secret_key, data, hashlib.sha1).digest()
    )

def requests_error_handler(func):
    @functools.wraps(func)
    def deco(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AssertionError as e:
            req = e.args[0]
            raise CowException(
                    req.url, req.status_code, req.content
                )
    return deco


class UploadToken(object):
    def __init__(self, access_key, secret_key, scope, ttl=3600):
        self.access_key = access_key
        self.secret_key = secret_key
        self.scope = scope
        self.ttl = ttl
        self._token = None
        self.generated_at = int(time.time())

    @property
    def token(self):
        if int(time.time()) - self.generated_at > self.ttl - 60:
            # 还有一分钟也认为过期了， make new token
            self._token = None

        if not self._token:
            self._token = self._make_token()

        return self._token

    def _make_token(self):
        self.generated_at = int(time.time())
        info = {
            'scope': self.scope,
            'deadline': self.generated_at + self.ttl
        }

        info = urlsafe_b64encode(json.dumps(info))
        token = signing(self.secret_key, info)
        return '%s:%s:%s' % (self.access_key, token, info)


class AccessToken(object):
    def __init__(self, access_key, secret_key, url, params=None):
        self.access_key = access_key
        self.secret_key = secret_key
        self.url = url
        self.params = params

        self.token = self.build_token()

    def build_token(self):
        uri = urlparse(self.url)
        token = uri.path
        if uri.query:
            token = '%s?%s' % (token, uri.query)
        token = '%s\n' % token
        if self.params:
            if isinstance(self.params, basestring):
                token += self.params
            else:
                token += urlencode(self.params)
        return '%s:%s' % (self.access_key, signing(self.secret_key, token))



class Cow(object):
    def __init__(self, access_key, secret_key):
        self.access_key = access_key
        self.secret_key = secret_key
        self.upload_tokens = {}

        self.stat = functools.partial(self._stat_rm_handler, 'stat')
        self.delete = functools.partial(self._stat_rm_handler, 'delete')
        self.copy = functools.partial(self._cp_mv_handler, 'copy')
        self.move = functools.partial(self._cp_mv_handler, 'move')

    def get_bucket(self, bucket):
        """对一个bucket的文件进行操作，
        推荐使用此方法得到一个bucket对象,
        然后对此bucket的操作就只用传递文件名即可
        """
        return Bucket(self, bucket)


    def generate_access_token(self, url, params=None):
        return AccessToken(self.access_key, self.secret_key, url, params=params).token


    def generate_upload_token(self, scope, ttl=3600):
        """上传文件的uploadToken"""
        if scope not in self.upload_tokens:
            self.upload_tokens[scope] = UploadToken(self.access_key, self.secret_key, scope, ttl=ttl)
        return self.upload_tokens[scope].token


    def build_requests_headers(self, token):
        return {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': 'QBox %s' % token
        }

    @requests_error_handler
    def api_call(self, url, params=None):
        token = self.generate_access_token(url, params=params)
        if params:
            res = requests.post(url, data=params, headers=self.build_requests_headers(token))
        else:
            res = requests.post(url, headers=self.build_requests_headers(token))
        assert res.status_code == 200, res
        return res.json() if res.text else ''


    def list_buckets(self):
        """列出所有的buckets"""
        url = '%s/buckets' % RS_HOST
        return self.api_call(url)


    def create_bucket(self, name):
        """不建议使用API建立bucket
        测试发现API建立的bucket默认无法设置<bucket_name>.qiniudn.com的二级域名
        请直接到web界面建立
        """
        # url = '%s/mkbucket/%s' % (RS_HOST, name)
        # return self.api_call(url)
        raise RuntimeError("Please create bucket in web")


    def drop_bucket(self, bucket):
        """删除整个bucket"""
        url = '%s/drop/%s' % (RS_HOST, bucket)
        return self.api_call(url)


    def list_files(self, bucket, marker=None, limit=None, prefix=None):
        """列出bucket中的文件"""
        query = ['bucket=%s' % bucket]
        if marker:
            query.append('marker=%s' % marker)
        if limit:
            query.append('limit=%s' % limit)
        if prefix:
            query.append('prefix=%s' % prefix)
        url = '%s/list?%s' % (RSF_HOST, '&'.join(query))
        return self.api_call(url)


    @requests_error_handler
    def put(self, scope, filename, data=None, keep_name=False, override=True):
        """
        上传文件
        :param scope: bucket name
        :param filename: file name
        :param data: file data
        :param keep_name: if True, use file name, otherwise use the file data's md5 value
        :param override: if True, override the same key file.
        :return:
        """
        if not data:
            with open(filename, 'rb') as f:
                data = f.read()

        if keep_name:
            upload_name = filename
        else:
            upload_name = hashlib.md5(data).hexdigest()
            _, ext = os.path.splitext(filename)
            upload_name += ext

        url = '%s/upload' % UP_HOST
        if override:
            token = self.generate_upload_token('%s:%s' % (scope, upload_name))
        else:
            token = self.generate_upload_token(scope)


        files = {'file': data}
        action = '/rs-put/%s' % urlsafe_b64encode(
            '%s:%s' % (scope, upload_name)
        )
        _type, _encoding = mimetypes.guess_type(filename)
        if _type:
            action += '/mimeType/%s' % urlsafe_b64encode(_type)
        data = {
            'auth': token,
            'action': action,
        }
        res = requests.post(url, files=files, data=data)
        assert res.status_code == 200, res
        return res.json()


    def _cp_mv_handler(self, action, args):
        src_bucket, src_filename, des_bucket, des_filename = args
        url = '%s/%s/%s/%s' % (
            RS_HOST,
            action,
            urlsafe_b64encode('%s:%s' % (src_bucket, src_filename)),
            urlsafe_b64encode('%s:%s' % (des_bucket, des_filename)),
        )
        return self.api_call(url)


    def _stat_rm_handler(self, action, bucket, filename):
        url = '%s/%s/%s' % (
            RS_HOST, action, urlsafe_b64encode('%s:%s' % (bucket, filename))
        )
        return self.api_call(url)


class Bucket(object):
    def __init__(self, cow, bucket):
        self.cow = cow
        self.bucket = bucket

    def put(self, filename, data=None, keep_name=False, override=True):
        return self.cow.put(self.bucket, filename, data=data, keep_name=keep_name, override=override)

    def stat(self, filename):
        return self.cow.stat(self.bucket, filename)

    def delete(self, filename):
        return self.cow.delete(self.bucket, filename)

    def copy(self, *args):
        return self.cow.copy(self._build_cp_mv_args(*args))

    def move(self, *args):
        return self.cow.move(self._build_cp_mv_args(*args))

    def list_files(self, marker=None, limit=None, prefix=None):
        return self.cow.list_files(self.bucket, marker=marker, limit=limit, prefix=prefix)

    def _build_cp_mv_args(self, *args):
        return [self.bucket, args[0], self.bucket, args[1]]

