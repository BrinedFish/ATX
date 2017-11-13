#!/usr/bin/env python
# -*- coding: utf-8 -*-

import atx,time
from atx.ext.report import Report

class HtmlReport(object):
    def __new__(cls, d):
        return super(HtmlReport, cls).__new__(cls)

    def __init__(self, d):
        self.d = d

    def __enter__(self):
        self.rp = Report(self.d, save_dir="examples/out")
        self.rp.patch_uiautomator()
        return self.rp

    def __exit__(self, type, value, trace):
        if self.rp is not None:
            self.rp.close()
            del self.rp

# python -c "import examples.test as test;test.go()"
def go():
    d = atx.connect()
    with HtmlReport(d) as rp:
        d.press_home()
        d.click_image(r"examples/lunch_icon.720x1280.png")
        d.click(258, 184)
        time.sleep(1)
        d.click(172, 274)
        d.type("ps")
        d.click(658, 258)
        rp.assert_image_exists('examples/ps_out.720x1280.png', timeout=10.0, safe=True)