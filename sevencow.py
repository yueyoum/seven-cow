from urlparse import urlparse
from urllib import urlencode
from base64 import urlsafe_b64encode
from hashlib import sha1
import hmac
import time
import json
import mimetypes

import requests

def signing(secret_key, data):
    return urlsafe_b64encode(
        hmac.new(secret_key, data, sha1).digest()
    )
    

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
        self.buckets = self.list_buckets()
        self.upload_tokens = {}


    def generate_token(self, url, params=None):
        uri = urlparse(url)
        token = uri.path
        if uri.query:
            token = '%s?%s' % (token, uri.query)
        token = '%s\n' % token
        if params:
            token += urlencode(params)
        return '%s:%s' % (self.access_key, signing(self.secret_key, token))

    def build_requests_headers(self, token):
        return {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': 'QBox %s' % token
        }

    def api_call(self, url, data=None, params=None):
        token = self.generate_token(url, params=params)
        if data:
            return requests.post(url, data=data,  headers=self.build_requests_headers(token))
        return requests.post(url, headers=self.build_requests_headers(token))


    def list_buckets(self):
        url = 'http://rs.qbox.me/buckets'
        res = self.api_call(url)
        return res.json()

    def create_bucket(self, name):
        url = 'http://rs.qbox.me/mkbucket/' + name
        res = self.api_call(url)
        return res.status_code

    def generate_upload_token(self, scope, ttl=3600):
        if scope not in self.upload_tokens:
            self.upload_tokens[scope] = UploadToken(self.access_key, self.secret_key, scope, ttl=ttl)
            print 'generate_upload_token'
        return self.upload_tokens[scope].token

    def put(self, scope, filename):
        url = 'http://up.qbox.me/upload'
        token = self.generate_upload_token(scope)
        print token
        x = '%s:%s' % (scope, filename)
        files = {
            'file': (filename, open(filename, 'rb')),
        }
        action = '/rs-put/%s' % urlsafe_b64encode(x)
        _type, _encoding = mimetypes.guess_type(filename)
        if _type:
            action += '/mimeType/%s' % urlsafe_b64encode(_type)
        print action
        data = {
            'auth': token,
            'action': action,
        }

        res = requests.post(url, files=files, data=data)
        return res

    def stat(self, bucket, filename):
        url = 'http://rs.qbox.me/stat/%s' % urlsafe_b64encode('%s:%s' % (bucket, filename))
        return self.api_call(url)

    def cp(self, src_bucket, src_filename, des_bucket, des_filename):
        url = 'http://rs.qbox.me/copy/%s/%s' % (urlsafe_b64encode('%s:%s' % (src_bucket, src_filename)), urlsafe_b64encode(des_bucket, des_filename))
        return self.api_call(url)

    def mv(self, src_bucket, src_filename, des_bucket, des_filename):
        url = 'http://rs.qbox.me/move/%s/%s' % (urlsafe_b64encode('%s:%s' % (src_bucket, src_filename)), urlsafe_b64encode(des_bucket, des_filename))
        return self.api_call(url)

    def rm(self, bucket, filenames):
        if isinstance(filenames, basestring):
            url = 'http://rs.qbox.me/delete/%s' % urlsafe_b64encode('%s:%s' % (bucket, filenames))
            return self.api_call(url)
        if isinstance(filenames, (list, tuple)):
            url = 'http://rs.qbox.me/batch'
            body = []
            for f in filenames:
                body.append('op=/delete/%s' % urlsafe_b64encode('%s:%s' % (bucket, f)))
            body = '' '&'.join(body)
            print body

            token = self.generate_token(url)
            headers = self.build_requests_headers(token)
            return requests.post(url, headers=headers)


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
