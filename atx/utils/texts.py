#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Yeshen'

import random
import string
import time
import uuid

random.seed(time.time())


def is_ascii(s):
    return all(ord(c) < 128 for c in s)


def strip(s):
    if isinstance(s, str):
        return s.strip().replace(' ', '\ ')
    elif isinstance(s, list):
        sb = ""
        for ss in s:
            sb = sb + " " + ss
        return sb.strip().replace(' ', '\ ')
    return s.strip()


def unique(n=None):
    if n is None:
        return uuid.uuid1()
    else:
        return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(n))