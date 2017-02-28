# -*- coding: utf-8 -*-

import gevent.monkey
gevent.monkey.patch_all()

import re
import os
import sys
import logging
import requests

from spider import Spider
from spider import Request
from spider import Job
from spider import retry_on_error
from store import SqliteBackend

URL_ENTRY = ["https://list.jd.com/list.html?cat=9847,9849,9870"]
CAT_ENTRY = "9847,9849,9870"

LIST_P = re.compile("list.html\?cat=%s" % CAT_ENTRY)
LIST_PAGE_P = re.compile("list.html\?cat=%s&page=\d+" % CAT_ENTRY)
ITEM_P = re.compile("item.jd.com/\d+.html")
DESC_P = re.compile("dx.3.cn/desc/\d+\?cdn=\d+")
IMG_DESC_P = re.compile(
    "img\d+.360buyimg.com/popWareDetail/jfs/\w+/\w+/\w+/\w+/\w+/\w+.jpg")
IMG_HEAD_P = re.compile(
    "img\d+.360buyimg.com/n\d+/jfs/\w+/\w+/\w+/\w+/\w+/\w+.jpg")

# NOTES without this cookie which copy from browser, can't get real list page.
# TODO auto get cookie by program
HEADERS = {"Cookie": (
    "listck=cc4aba28048f8111a9493ecd7303ef43; "
    "__jda=122270672.14882548153701130410571."
    "1488254815.1488254815.1488254815.1")}

DB_FILE = "jd_img.db"
IMG_DIR = "./imgs"


class JDImgJob(Job):

    def __init__(self, *args, **kwargs):
        self.store = SqliteBackend(DB_FILE)
        return super(JDImgJob, self).__init__(*args, **kwargs)

    def parser(self, text):
        """
        html parser, find the list url, detail url, desc url, img url

        :param text: html source code
        :rtype list: list of img url
        """

        # if it's list page, find other list url and detail url
        if LIST_P.findall(self.request.url):
            self.parser_list(text)
            self.parser_detail(text)

        # if it's detail page, parse desc url and img url
        elif ITEM_P.findall(self.request.url):
            self.parser_desc(text)
            return self.parser_head_img(text)

        # if it's desc page, parse img url
        elif DESC_P.findall(self.request.url):
            return self.parser_desc_img(text)

        else:
            self.logger.error("PARSER UNKNOW URL: %s", self.request.url)

    def parser_list(self, text):
        """add next list page to queue"""
        find_list_url = LIST_PAGE_P.findall(text)
        for list_url in self.store.record_url(find_list_url):
            static_list_url = self.get_list_url(list_url)
            self.spider.queue.put(Request(static_list_url))

    def parser_detail(self, text):
        """add detail page to queue"""
        find_item_url = ITEM_P.findall(text)
        for item_url in self.store.record_url(find_item_url):
            static_item_url = self.get_static_url(item_url)
            self.spider.queue.put(Request(static_item_url))

    def parser_desc(self, text):
        """add detail page to queue"""
        find_desc_url = DESC_P.findall(text)
        for desc_url in self.store.record_url(find_desc_url):
            static_desc_url = self.get_static_url(desc_url)
            self.spider.queue.put(Request(static_desc_url))

    def parser_head_img(self, text):
        """return img url to download"""
        all_size_img_url_list = []
        img_url_list = IMG_HEAD_P.findall(text)
        for img_url in img_url_list:
            # get all size of img
            for size in range(10):
                img_url_sp = img_url.split("/")
                img_url_sp[1] = "n%s" % size
                replace_img_url = "/".join(img_url_sp)
                all_size_img_url_list.append(replace_img_url)

        return [self.get_static_url(img_url)
                for img_url in self.store.record_img(
                    all_size_img_url_list, self.request.url)]

    def parser_desc_img(self, text):
        """return img url to download"""
        img_url_list = IMG_DESC_P.findall(text)

        return [self.get_static_url(img_url)
                for img_url in self.store.record_img(
                    img_url_list, self.request.url)]

    @staticmethod
    def get_list_url(url):
        return "http://list.jd.com/%s" % url

    @staticmethod
    def get_static_url(url):
        return "http://%s" % url

    def archiver(self, data):
        """
        save img file from url

        :param data: img url
        """
        if "--NODOWN" in sys.argv:
            return

        if not os.path.exists(IMG_DIR):
            os.makedirs(IMG_DIR)

        for img_url in data:
            try:
                self._archiver(img_url)
            except Exception:
                self.logger.exception("DOWNLOAD IMG FAILURE: %s", img_url)

    @retry_on_error((requests.exceptions.ChunkedEncodingError,
                     requests.exceptions.ReadTimeout,
                     requests.exceptions.ConnectionError,
                     requests.exceptions.HTTPError))
    def _archiver(self, img_url):
        # use stream to save mem
        r = requests.get(img_url, stream=True, timeout=2)
        r.raise_for_status()

        # get filename
        img_url_sp = img_url.split("/")
        filename = "_".join([img_url_sp[3], img_url_sp[-1]])

        # write to file
        with open(os.path.join(IMG_DIR, filename), 'wb') as f:
            for chunk in r.iter_content(1024):
                f.write(chunk)
        # TODO use MD5 rename file


if __name__ == "__main__":
    # init logging conf
    logging.basicConfig(
            level=logging.WARNING,
            format='%(asctime)s %(levelname)s %(message)s')
    logger = logging.getLogger(__name__)

    try:
        spider = Spider(URL_ENTRY, JDImgJob,
                        headers=HEADERS, proxies_list=[])
        spider.run()
    except Exception as e:
        logger.exception(e)
