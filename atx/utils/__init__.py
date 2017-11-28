#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Yeshen'

import datetime
import atx

ENABLE_TIME_LOG = False


def time_log(func):
    def wrapper(*args, **kw_args):
        if ENABLE_TIME_LOG:
            print func.__name__ + datetime.datetime.now().strftime('__%H:%M:%S.%f')
        ret = func(*args, **kw_args)
        if ENABLE_TIME_LOG:
            print "__done_" + func.__name__ + datetime.datetime.now().strftime('__%H:%M:%S.%f')
        return ret

    return wrapper
