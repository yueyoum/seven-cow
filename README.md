# Seven Cow 七牛

另一个七牛云存储Python SDK

这是一个比官方更易用的SDK。 官方SDK请见 
[![官方SDK](http://qiniutek.com/images/logo-2.png)](https://github.com/qiniu/python-sdk)

## Install

```bash
pip install sevencow
```


## Usage

#### 初始化

在你需要的地方
```python
from sevencow import Cow
cow = Cow(<ACCESS_KEY>, <SECRET_KEY>)
```

然后就可以通过 `cow.stat(<BUCKET>, <FILENAME>)` 这样来进行操作.
但为了简化操作，并且考虑到大多数都是在一个bucket中进行文件操作，
所以建议再做一步：

```python
b = cow.get_bucket(<BUCKET>)
```

后面都用这个`b`对象来操作。 它代表了`<BUCKET>`

#### 列出所有的bucket
```python
cow.list_buckets()
```

#### 列出一个bucket中的所有文件
```python
b.list_files()
```
这个方法还有 marker, limit, prefix这三个可选参数，详情参考官方文档


#### 上传

```python
# Bucket.put(filename, data=None, keep_name=False, override=True)
# filename:  文件名。 或者是从磁盘文件上传，就是文件路径
# data:      如果从buffer中上传数据，就需要此参数。表示文件内容。
# keep_name: 上传后的文件是否保持和filename一样。默认为False，用文件内容的MD5值
# override:  上传同名文件，是否强制覆盖
b.put('a')                    # 上传本地文件a，并且用a内容的MD5值作为上传后的名字
b.put('a'， keep_name=True)   # 上传本地文件a，并且用a作为上传后的名字
b.put('a', data=data)         # 把`data`数据上传，用`data`的MD5值作为上传后的名字
                                这种的使用场景是你直接有了一个file-like的对象在内存中，
                                比如通过浏览器上传的文件，
                                此时你就不用把文件先写入磁盘，而是直接把文件内容读出，直接上传
```


#### 删除，查看文件信息
```python
b.stat('a')                 # 查看单个文件信息
b.delete('a')               # 删除单个文件
```


#### 拷贝，移动（改名）

这两个操作需要提供源文件名和目标文件名

```python
b.copy('a', 'b')                            # 将'a' 拷贝至'b'
b.move('a', 'b')                            # 将'a' 改名为'b'
```

有没有觉得比官方SDK容易使用多呢？

--------

#### 异常

以上操作任何错误都会引发异常， 只要请求api返回的不是200

所以安全的做法是这样：

```python
from sevencow import CowException

try:
    b.put('a')
except CowException as e:
    print e.url         # 出错的url
    print e.status_code # 返回码
    print e.content     # api 错误的原因
```


## 测试

1.  首先从github clone项目到本地
2.  测试需要三个环境变量

    ```bash
    export QINIU_ACCESS_KEY=<...>
    export QINIU_SECRET_KEY=<...>
    export QINIU_BUCKET=<...>
    ```

    `QINIU_BUCKET` 要先在web中建立

3.  在项目目录中直接运行 `nosetests`
