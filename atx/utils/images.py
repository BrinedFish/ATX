#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Yeshen'

import aircv as ac
from atx.utils import time_log
from atx import imutils

__screensize = (1920, 1080)
__match_threshold = 0.8
__scale = 3


class Error(Exception):
    def __init__(self, message, data=None):
        self.message = message
        self.data = data

    def __str__(self):
        if self.data:
            return '{}, data: {}'.format(self.message, self.data)
        return self.message

    def __repr__(self):
        return repr(self.message)


class ImageNotFoundError(Error):
    pass


@time_log
def read(path, rect=None):
    raw_image = imutils.open(path)
    if rect is not None:
        raw_image = imutils.crop(image=raw_image, left=rect[0], top=rect[1], right=rect[2], bottom=rect[3])
    return imutils.to_pillow(raw_image)


@time_log
def match(target, scanner):
    not_reusable_target = isinstance(target, str) or isinstance(target, unicode)
    ret = None
    if not_reusable_target:
        target = read(target)
    if isinstance(scanner, str) or isinstance(target, unicode):
        scanner = read(scanner)

    if ret is None:
        ret = __match_template(scanner, target)
    # TODO
    # if ret is None:
    #     ret = __match_sift(scanner, target)

    if not_reusable_target:
        del target
    del scanner

    if ret is None:
        raise ImageNotFoundError(Error("match error"))
    else:
        return ret


@time_log
def __match_template(scanner, target):
    ret = ac.find_template(__fuck(scanner), __fuck(target))
    if ret and ret['confidence'] > __match_threshold:
        return ret['result']
    return None


@time_log
def __match_sift(scanner, target):
    ret = ac.find_sift(__fuck(scanner), __fuck(target), min_match_count=10)
    if ret is not None:
        matches, total = ret['confidence']
        if 1.0 * matches / total > 0.5:
            return ret['result']
    return None


def __fuck(image):
    return imutils.from_pillow(image)
