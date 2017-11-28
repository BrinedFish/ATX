#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Yeshen'

import time
import atx
from atx.ext.report import Report


# python -c "import atx.test as test;test.report()"
def report():
    d = atx.connect()
    rp = Report(d, save_dir='tasks/out/local.test')
    try:
        d.press_home()
        d.click(704, 1296)
        try:
            d.click_image(r"../../../Desktop/setting.1920x1080.png")
        except Exception as error:
            print error
        try:
            d.wait(r"../../../Desktop/timeline.1920x1080.png")
        except Exception as error:
            print error
        d.click_image(r"../../../Desktop/timeline.1920x1080.png")
        rp.info("timeline", screenshot=d.screenshot())
        rp.assert_image_exists(r"../../../Desktop/show_chart.1920x1080.png", scanner=d.screen_image())
        d.press_back()
        d.press_back()
    except Exception as error1:
        print error1
    finally:
        rp.close()


def run():
    d = atx.connect()
    d.press_home()
    d.click(704, 1296)
    try:
        d.click_image(r"../../../Desktop/setting.1920x1080.png")
    except Exception as error:
        print error
    try:
        d.wait(r"../../../Desktop/timeline.1920x1080.png")
    except Exception as error:
        print error
    d.click_image(r"../../../Desktop/timeline.1920x1080.png")
    d.screenshot()
    print d.exists(local_object_path=r"../../../Desktop/show_chart.1920x1080.png")
    d.press_back()
    d.press_back()
