# -*- coding: utf-8 -*-

import gevent

import gevent.monkey
import gevent.pool
import gevent.queue

import random
import requests
import fake_useragent
import functools
import unittest
import os
import logging

# for create random UserAgent
UA = fake_useragent.UserAgent(
    path="fake_useragent_%s.json" % fake_useragent.VERSION)


class retry_on_error(object):
    """decorator. retry for specific exception, record log for others"""

    def __init__(self, retry_exception, retry_cnt=3):
        """
        :param retry_exception: type tuple, which exception should be catched
        :param retry_cnt: how many times will by retring if raise exception
        """
        self.retry_exception = retry_exception
        self.retry_cnt = retry_cnt
        self.logger = logging.getLogger("Request")

    def __call__(self, task_definition):
        @functools.wraps(task_definition)
        def wrapper(*args, **kwargs):
            for cnt in range(self.retry_cnt):
                try:
                    return task_definition(*args, **kwargs)
                except self.retry_exception as e:
                    self.logger.warning("retry %s: %s time(s)", e, cnt + 1)
            raise
        return wrapper


class Request(object):

    def __init__(self, url):
        self.url = url


class Job(gevent.Greenlet):

    logger = logging.getLogger("Request")

    def __init__(self, request, spider):
        super(Job, self).__init__()
        self.request = request
        self.spider = spider

    @retry_on_error((requests.exceptions.ChunkedEncodingError,
                     requests.exceptions.ReadTimeout,
                     requests.exceptions.ConnectionError,
                     requests.exceptions.HTTPError))
    def fetcher(self, headers=None, proxies=None):
        """
        request url, fetch source code

        :param headers: dict
        :param proxies: dict
        """
        default_headers = {
            "User-Agent": UA.random,
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Cache-Control": "max-age=0",
        }
        default_headers.update(headers or {})
        r = requests.get(self.request.url, timeout=2,
                         headers=default_headers, proxies=proxies)
        r.raise_for_status()
        if (self.request.url != r.url):
            self.logger.error("FETCHER: %s TO %s", self.request.url, r.url)
        return r.text

    def parser(self, text):
        """
        if got a link, return a Request object, else return data

        :param text: HTML source code
        """
        self.logger.debug("PARSER: %s", self.request.url)
        return text

    def archiver(self, data):
        """
        store data

        :param data: the data which parser returned
        """
        self.logger.debug("ARCHIVER: %s", self.request.url)
        filename = self.request.url.split("/")[-1]
        with open(filename, "wb") as f:
            f.write(data.encode("UTF-8"))

    def _run(self):
        self.logger.debug("RUN Request: %s", self.request.url)
        headers = self.spider.get_headers()
        proxies = self.spider.get_proxies()
        try:
            text = self.fetcher(headers, proxies)
        except Exception:
            self.logger.exception("FETCH ERROR: %s", self.request.url)
            return self.stop()
        try:
            result = self.parser(text)
        except Exception:
            self.logger.exception("PARSER ERROR: %s", self.request.url)
            return self.stop()
        if isinstance(result, Request):
            self.spider.queue.put(result)
        elif result:
            try:
                self.archiver(result)
            except Exception:
                self.logger.exception("ARCHIVER ERROR: %s", result)
        self.stop()

    def stop(self):
        self.spider.job_finished.set()
        self.kill(block=False)


class Spider(object):

    logger = logging.getLogger("Spider")

    def __init__(self, urls, job_cls=Job,
                 headers=None, proxies_list=None, pool_size=10):
        gevent.monkey.patch_all()
        self._stop = gevent.event.Event()
        self.job_finished = gevent.event.Event()
        self.queue = gevent.queue.Queue()
        self.pool = gevent.pool.Pool(pool_size)
        self.proxies_list = proxies_list
        self.headers = headers
        self.job_cls = job_cls
        for url in urls:
            self.queue.put(Request(url))

    def get_headers(self):
        return self.headers or {}

    def get_proxies(self):
        return {} if not self.proxies_list else \
            random.choice(self.proxies_list)

    def stopped(self):
        return self._stop.is_set()

    def stop(self):
        self.logger.debug("SPIDER STOPING")
        self._stop.set()
        self.pool.join()
        self.queue.put(StopIteration)

    def run(self):
        while not self.stopped():
            for job in list(self.pool):
                if job.dead:
                    self.pool.discard(job)
            try:
                req = self.queue.get_nowait()
            except gevent.queue.Empty:
                if self.pool.free_count() != self.pool.size:
                    self.job_finished.wait()
                    self.job_finished.clear()
                    continue
                else:
                    self.stop()
            self.logger.info("GET req from queue: %s", req.url)
            job = self.job_cls(req, self)
            self.pool.start(job)


class SpiderTestCase(unittest.TestCase):

    def setUp(self):
        self.urls = ["http://www.baidu.com"]
        self.filename = self.urls[0].split("/")[-1]

    def test_spider(self):
        spider = Spider(self.urls)
        spider.run()
        assert os.path.getsize(self.filename) > 0

    def tearDown(self):
        os.remove(self.filename)


if __name__ == "__main__":
    logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s %(levelname)s %(message)s')
    unittest.main()
