# -*- coding: utf-8 -*-

import sqlite3
import unittest
import logging
import os


class SqliteBackend(object):

    PAGE_TABLE_NAME = "jd_page"
    IMG_TABLE_NAME = "jd_img"

    def __init__(self, filename):
        self.filename = filename
        self.init_table()

    def init_table(self):
        conn = sqlite3.connect(self.filename)
        c = conn.cursor()
        c.execute('SELECT * FROM sqlite_master WHERE type="table"')
        if len(c.fetchall()) != 2:
            c.execute(
                'CREATE TABLE %s (id integer PRIMARY KEY, url text UNIQUE)' %
                self.PAGE_TABLE_NAME)
            c.execute(('CREATE TABLE %s (id integer PRIMARY KEY, '
                       'url text UNIQUE, page_url text)') %
                      self.IMG_TABLE_NAME)
        conn.commit()
        conn.close()

    def record_url(self, url_list):
        result = []
        conn = sqlite3.connect(self.filename)
        c = conn.cursor()
        for url in url_list:
            try:
                c.execute('INSERT OR FAIL INTO %s (url) VALUES ("%s")' %
                          (self.PAGE_TABLE_NAME, url))
                result.append(url)
            except sqlite3.IntegrityError:
                continue
        conn.commit()
        conn.close()
        return result

    def record_img(self, url_list, page_url):
        result = []
        conn = sqlite3.connect(self.filename)
        c = conn.cursor()
        for url in url_list:
            url_sp = url.split("/")
            filename = "_".join([url_sp[1], url_sp[-1]])
            try:
                c.execute(('INSERT OR FAIL INTO %s '
                           '(url, page_url) VALUES ("%s", "%s")') %
                          (self.IMG_TABLE_NAME, filename, page_url))
                result.append(url)
            except sqlite3.IntegrityError:
                continue
        conn.commit()
        conn.close()
        return result


class SqliteBackendTestCase(unittest.TestCase):

    def setUp(self):
        self.test_filename = "test.db"

    def test_record_url(self):
        fmt = "url%s"
        url_cnt = 10
        uniqure_url_cnt = 6
        url_list = [fmt % (i % uniqure_url_cnt) for i in range(url_cnt)]
        store = SqliteBackend(self.test_filename)
        recorded_url_list = store.record_url(url_list)
        assert len(recorded_url_list) == uniqure_url_cnt
        for i, url in enumerate(url_list[:uniqure_url_cnt]):
            assert fmt % i == url

    def tearDown(self):
        os.remove(self.test_filename)


if __name__ == "__main__":
    logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s %(levelname)s %(message)s')
    unittest.main()
