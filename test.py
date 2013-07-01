import os

from sevencow import Cow


class Test(object):
    def setUp(self):
        ACCESS_KEY = os.environ['QINIU_ACCESS_KEY']
        SECRET_KEY = os.environ['QINIU_SECRET_KEY']
        bucket = os.environ['QINIU_BUCKET']
        cow = Cow(ACCESS_KEY, SECRET_KEY)
        self.b = cow.get_bucket(bucket)

        for i in range(3):
            with open('sevencow{0}'.format(i), 'w') as f:
                f.write('0000')

    def tearDown(self):
        for f in self._multi_files():
            try:
                os.unlink(f)
            except IOError:
                pass

    def _list_file_names(self):
        files = self.b.list_files()
        return [f['key'] for f in files['items']]

    def _multi_files(self):
        return ['sevencow{0}'.format(i) for i in range(3)]


    def testaPutSingle(self):
        key = 'sevencow0'
        res = self.b.put(key)
        assert key == res['key']
        assert key in self._list_file_names()

    def testaPutSingleChangeName(self):
        key = 'sevencow0'
        name = 'sevencow0c'
        res = self.b.put(key, names={key: name})
        assert name == res['key']
        assert name in self._list_file_names()


    def testbPutMulti(self):
        keys = self._multi_files()
        res = self.b.put(*keys)
        res_keys = [r['key'] for r in res]
        assert keys == res_keys

        files = self._list_file_names()
        for k in keys:
            assert k in files

    def testbPutMultiChangeName(self):
        keys = self._multi_files()
        names = {}
        for k in keys:
            names[k] = '{0}cc'.format(k)
        res = self.b.put(*keys, names=names)
        res_keys = [r['key'] for r in res]
        assert sorted(names.values()) == sorted(res_keys)

        files = self._list_file_names()
        for k in names.values():
            assert k in files


    def testcStatSingle(self):
        self.b.stat('sevencow0')

    def testdStatMulti(self):
        self.b.stat(*self._multi_files())


    def testeCopySingle(self):
        self.b.copy('sevencow0', 'sevencow01')
        assert 'sevencow01' in self._list_file_names()

    def testfCopyMulti(self):
        self.b.copy(('sevencow1', 'sevencow11'), ('sevencow2', 'sevencow21'))
        files = self._list_file_names()
        assert 'sevencow11' in files
        assert 'sevencow21' in files

    def testgMoveSingle(self):
        self.b.move('sevencow01', 'sevencow011')
        files = self._list_file_names()
        assert 'sevencow01' not in files
        assert 'sevencow011' in files

    def testhMoveMulti(self):
        self.b.move(('sevencow11', 'sevencow111'), ('sevencow21', 'sevencow211'))
        files = self._list_file_names()
        assert 'sevencow11' not in files and 'sevencow21' not in files
        assert 'sevencow111' in files and 'sevencow211' in files


    def testiDeleteSingle(self):
        self.b.delete('sevencow0')
        assert 'sevencow0' not in self._list_file_names()

    def testjDeleteMulti(self):
        keys = ['sevencow1', 'sevencow2', 'sevencow011', 'sevencow111', 'sevencow211',
            'sevencow0c', 'sevencow0cc', 'sevencow1cc', 'sevencow2cc',
        ]
        self.b.delete(*keys)
        files = self._list_file_names()
        for k in keys:
            assert k not in files

