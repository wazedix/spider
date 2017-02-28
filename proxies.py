# -*- coding: utf-8 -*-

import re
import logging
import pprint
import requests

logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

VERTIFY_SITE = "http://www.baidu.com"


def get_from_ipcn():
    url = "http://proxy.ipcn.org/proxylist.html"
    r = requests.get(url)
    ip_re = re.compile("[0-9]+(?:\.[0-9]+){3}:[0-9]+")
    proxies_list = [{"http": ip} for ip in ip_re.findall(r.text)]
    return filter(check_proxies, proxies_list)


def check_proxies(proxies):
    try:
        r = requests.head(VERTIFY_SITE, timeout=1, proxies=proxies)
        r.raise_for_status()
    except Exception as e:
        logger.error("PROXY %s: %s", proxies["http"], e)
        return False
    logger.info("PROXY %s: healthy", proxies["http"])
    return True


if __name__ == "__main__":
    pprint.pprint(get_from_ipcn())
