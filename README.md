# Seven Cow 七牛

另一个七牛云存储Python SDK

此SDK目标是更容易的使用，完整功能的SDK请见 ![官方SDK](https://github.com/qiniu/python-sdk)

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

#### 上传，删除，查看文件信息

这三种是一类操作，因为只要提供文件名即可

```python
b.put('a')                  # 上传单个文件
b.put('a', 'b', 'c')        # 批量上传
b.stat('a')                 # 查看单个文件信息
b.stat('a', 'b', 'c')       # 批量查看
b.delete('a')               # 删除单个文件
b.delete('a', 'b', 'c')     # 批量删除
```

#### 拷贝，移动（改名）

这两个操作都需要提供源文件名和目标文件名

```python
b.copy('a', 'b')                            # 将'a' 拷贝至'b'
b.copy(('a', 'b'), ('c', 'd'), ('e', 'f'))  # 批量拷贝 'a' => 'b', 'c' => 'd', 'e' => 'f'
b.move('a', 'b')                            # 将'a' 改名为'b'
b.move(('a', 'b'), ('c', 'd'), ('e', 'f'))  # 批量改名 'a' => 'b', 'c' => 'd', 'e' => 'f'
```

有没有觉得比官方SDK容易使用多呢？

#### 异常

以上操作任何错误都会引发异常， 只要请求api返回的不是200

所以安全的做法是这样：

```
from sevencow import CowException

try:
    b.copy(('a', 'b'), ('c', 'd'))
except CowException as e:
    print e.url         # 出错的url
    print e.status_code # 返回码
    print e.reason      # http error的原因
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
