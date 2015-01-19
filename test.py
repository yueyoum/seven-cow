import os
import random
import hashlib
from sevencow import Cow


class Test(object):
    def setUp(self):
        ACCESS_KEY = os.environ['QINIU_ACCESS_KEY']
        SECRET_KEY = os.environ['QINIU_SECRET_KEY']
        bucket = os.environ['QINIU_BUCKET']
        cow = Cow(ACCESS_KEY, SECRET_KEY)
        self.b = cow.get_bucket(bucket)

        self.files = {'sevencow' + str(i) : i for i in range(2)}
        for k, v in self.files.items():
            with open(k, 'w') as f:
                f.write('v')

    def tearDown(self):
        for f in self.files:
            try:
                os.unlink(f)
            except IOError:
                pass

    def _list_file_names(self):
        files = self.b.list_files()
        return [f['key'] for f in files['items']]

    def _get_file_md5(self, f):
        _, ext = os.path.splitext(f)
        with open(f, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest() + ext

    def testaPutFromFileKeepName(self):
        f = 'sevencow0'
        res = self.b.put(f, keep_name=True)
        assert f == res['key']
        assert f in self._list_file_names()

    def testbPutFromFileNotKeepName(self):
        f = 'sevencow0'
        md5 = self._get_file_md5(f)
        res = self.b.put(f)
        assert md5 == res['key']
        assert md5 in self._list_file_names()

    def testcPutFromBuffer(self):
        f = 'sevencow1'
        md5 = self._get_file_md5(f)

        with open(f, 'rb') as x:
            data = x.read()

        res = self.b.put(f, data=data)
        assert md5 == res['key']
        assert md5 in self._list_file_names()


    def testdStat(self):
        self.b.stat('sevencow0')


    def testeCopy(self):
        self.b.copy('sevencow0', 'cp0')
        assert 'cp0' in self._list_file_names()


    def testfMove(self):
        self.b.move('cp0', 'mv0')
        files = self._list_file_names()
        assert 'cp0' not in files
        assert 'mv0' in files


    def testgDelete(self):
        self.b.delete('sevencow0')
        self.b.delete(self._get_file_md5('sevencow1'))
        self.b.delete('mv0')
        assert 'sevencow0' not in self._list_file_names()
        assert 'mv0' not in self._list_file_names()

