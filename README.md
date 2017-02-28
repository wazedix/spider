京东图片拉取爬虫
=============

拉取京东指定类目下的图片

### Run

运行前先用浏览器访问京东，获取 Cookie，替换 jd\_img.py 里的变量

```
python jd_img.py
```

或者只拉取图片链接，不下载图片:
```
python jd_img.py --NODOWN
```

### Test

```
python spider.py
python store.py
python proxy.py
```

### Code

* jd\_img.py 抓取京东沙发类别图片，可以更改分类变量拉取其他类目图片
* spider.py 基于 Gevent 的一个简易爬虫框架
* store.py 封装存储相关的类
* proxies.py 获取代理，暂未用到

### TODO

* 支持解析用户评论中的图片
* 使用 Celery 支持分布式部署
* 支持其他图片存储方案
* 自动获取 Cookie
