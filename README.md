# Seven Cow 七牛

另一个七牛云存储Python SDK

此SDK目标是更容易的使用，完整功能的SDK请见 ![官方SDK](https://github.com/qiniu/python-sdk)

## Install

```bash
pip install sevencow
```

#### 与官方SDK使用对比

<table>
<tr><td></td><td>sevencow</td><td>官方SDK</td></tr>
<tr>
    <td>初始化</td>
    <td>
    ```python
    from sevencow import Cow
    cow = Cow(<ACCESS_KEY>, <SECRET_KEY>)
    b = cow.get_bucket(<BUCKET_NAME>)
    ```
    </td>
    <td>
    ```python
    import qiniu.config
    qiniu.config.ACCESS_KEY = <ACCESS_KEY>
    qiniu.config.SECRET_KEY = <SECRET_KEY>
    ```
    </td>
</tr>
<tr>
    <td>单个文件上传</td>
    <td>
    ```python
    b.put('a')
    ```
    </td>
    <td>
    ```python
    import qiniu.rs
    import qiniu.io
    policy = qiniu.rs.PutPolicy(<BUCKET_NAME>)
    uptoken = policy.token()
    extra = qiniu.io.PutExtra(<BUCKET_NAME>)
    qiniu.io.put_file(uptoken, key, localfile, extra)
    ```
    </td>
</tr>
</table>
