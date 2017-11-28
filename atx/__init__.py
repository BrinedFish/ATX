#!/usr/bin/env python
# -*- coding: utf-8 -*-

from atx.drivers.android import Application
from atx.drivers.android import Device

version = '1.0'
DEBUG = True


def connect(serial=None, port=None, **kwargs):
    if len(kwargs) > 0 and DEBUG:
        print kwargs
    app = Application(serial=serial, port=port)
    app.prepare()
    return app


def machine(serial=None, port=None, **kwargs):
    if len(kwargs) > 0 and DEBUG:
        print kwargs
    return Device(serial=serial, port=port)
