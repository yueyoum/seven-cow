Yet another qiniu cloud storeage Python SDK

Very Easy for use!

    from sevencow import Cow
    c = Cow(<ACCESS-KEY>, <SECRET-KEY>)
    b = c.get_bucket(<BUCKET-NAME>)

    b.put('a')              # put from file
    b.put('a', data=data)   # put from buffer
    b.stat('a')
    b.copy('a', 'b')
    b.move('a', 'c')
    b.delete('a')

github: https://github.com/yueyoum/seven-cow
