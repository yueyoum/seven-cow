# -*- coding: utf-8 -*-

import os
from urlparse import urlparse
from urllib import urlencode
from base64 import urlsafe_b64encode
from hashlib import sha1
import functools
import hmac
import time
import json
import mimetypes

import requests


RS_HOST = 'http://rs.qbox.me'
UP_HOST = 'http://up.qiniu.com'


class CowException(Exception): pass



def signing(secret_key, data):
    return urlsafe_b64encode(
        hmac.new(secret_key, data, sha1).digest()
    )

def requests_error_handler(func):
    @functools.wraps(func)
    def deco(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AssertionError as e:
            req = e.args[0]
            raise CowException(
                "{0}: Url {1}, Status code {2}, Reason {3}, Content {4}".format(
                    func.func_name, req.url, req.status_code, req.reason, req.content
                )
            )
    return deco



class UploadToken(object):
    def __init__(self, access_key, secret_key, scope, ttl=3600):
        self.access_key = access_key
        self.secret_key = secret_key
        self.scope = scope
        self.ttl = ttl
        self._token = None
        self.generated = int(time.time())

    @property
    def token(self):
        if int(time.time()) - self.generated > self.ttl:
            # expired
            # make new token
            self._token = self._make_token()
        if not self._token:
            self._token = self._make_token()
        return self._token

    def _make_token(self):
        self.generated = int(time.time())
        info = {
            'scope': self.scope,
            'deadline': self.generated + self.ttl
        }

        info = urlsafe_b64encode(json.dumps(info))
        token = signing(self.secret_key, info)
        return '%s:%s:%s' % (self.access_key, token, info)
        



class Cow(object):
    def __init__(self, access_key, secret_key):
        self.access_key = access_key
        self.secret_key = secret_key
        self.upload_tokens = {}
        
        self.stat = functools.partial(self._handler, 'stat')
        self.delete = functools.partial(self._handler, 'delete')


    def generate_access_token(self, url, params=None):
        uri = urlparse(url)
        token = uri.path
        if uri.query:
            token = '%s?%s' % (token, uri.query)
        token = '%s\n' % token
        if params:
            if isinstance(params, basestring):
                token += params
            else:
                token += urlencode(params)
        return '%s:%s' % (self.access_key, signing(self.secret_key, token))

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
        return res.json()


    def list_buckets(self):
        url = 'http://rs.qbox.me/buckets'
        res = self.api_call(url)
        return res.json()

    def create_bucket(self, name):
        """不建议使用API建立bucket
        测试发现API建立的bucket默认无法设置<bucket name>.qiniudn.com的二级域名
        请直接到web界面建立
        """
        url = 'http://rs.qbox.me/mkbucket/' + name
        res = self.api_call(url)
        return res.status_code

    def generate_upload_token(self, scope, ttl=3600):
        if scope not in self.upload_tokens:
            self.upload_tokens[scope] = UploadToken(self.access_key, self.secret_key, scope, ttl=ttl)
            print 'generate_upload_token'
        return self.upload_tokens[scope].token


    @requests_error_handler
    def put(self, scope, filename):
        """上传文件
        filename 如果是字符串，表示上传单个文件，
        如果是list或者tuple，表示上传多个文件
        """
        url = 'http://up.qbox.me/upload'
        token = self.generate_upload_token(scope)
        
        def _put(filename):
            files = {
                'file': (filename, open(filename, 'rb')),
            }
            action = '/rs-put/%s' % urlsafe_b64encode('%s:%s' % (scope, os.path.basename( filename )))
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
        
        if isinstance(filename, basestring):
            # 单个文件
            return _put(filename)
        
        if isinstance(filename, (list, tuple)):
            # 多文件
            return [_put(f) for f in filename]
        
        raise TypeError("put, filename should be string, list or tuple. Unsupported type: {0}".format(filename))


    def cp(self, src_bucket, src_filename, des_bucket, des_filename):
        url = 'http://rs.qbox.me/copy/%s/%s' % (urlsafe_b64encode('%s:%s' % (src_bucket, src_filename)), urlsafe_b64encode(des_bucket, des_filename))
        return self.api_call(url)

    def mv(self, src_bucket, src_filename, des_bucket, des_filename):
        url = 'http://rs.qbox.me/move/%s/%s' % (urlsafe_b64encode('%s:%s' % (src_bucket, src_filename)), urlsafe_b64encode(des_bucket, des_filename))
        return self.api_call(url)



    def _handler(self, action, bucket, filename):
        if isinstance(filename, basestring):
            return self.single(action, bucket, filename)
        if isinstance(filename, (list, tuple)):
            return self.batch(action, bucket, filename)
        raise TypeError(
            "filename should be string, list or tuple."
            "Unsupported type: {0}".format(filename)
        )


    def single(self, action, bucket, filename):
        url = '%s/%s/%s' % (
            RS_HOST, action, urlsafe_b64encode('%s:%s' % (bucket, filename))
        )
        return self.api_call(url)


    def batch(self, action, bucket, filenames):
        url = '%s/batch' % RS_HOST
        param = [
            'op=/%s/%s' % (
                action, urlsafe_b64encode('%s:%s' % (bucket, f))
            ) for f in filenames
        ]
        param = '&'.join(param)
        return self.api_call(url, param)



    def drop_bucket(self, bucket):
        url = 'http://rs.qbox.me/drop/%s' % bucket
        return self.api_call(url)

    def list(self, bucket, marker=None, limit=None, prefix=None):
        query = ['bucket=%s' % bucket]
        if marker:
            query.append('marker=%s' % marker)
        if limit:
            query.append('limit=%s' % limit)
        if prefix:
            query.append('prefix=%s' % prefix)
        url = 'http://rsf.qbox.me/list?%s' % '&'.join(query)
        return self.api_call(url)
        

import config
cow = Cow(config.ACCESS_KEY, config.SECRET_KEY)
