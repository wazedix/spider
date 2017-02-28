京东图片拉取爬虫
=============

拉取京东指定类目下的图片

### Run

### Test

```
python spider.py
python store.py
python proxy.py
```

### Code

* jd_img.py 抓取京东沙发类别图片
* spider.py 基于 Gevent 的一个简易爬虫框架
* store.py 封装存储相关的类
* proxies.py 获取代理，暂未用到

### TODO

* 支持解析用户评论中的图片
* 使用 Celery 支持分布式部署
* 支持其他图片存储方案
* 自动获取 Cookie
