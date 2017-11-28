#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import

import atx
import os
import time
import json
import inspect
import codecs
import functools
from atx import consts
from atx import imutils
from atx.base import nameddict
from atx.ext.report import patch as pt
import shutil
import numpy
from PIL.Image import Image
import atx.drivers.screen_mapping as mapping
from atx.drivers.android import Application

EVENT_SCREENSHOT = 1 << 1
EVENT_CLICK = 1 << 2
EVENT_SWIPE = 1 << 3
EVENT_TYPE = 1 << 4
EVENT_CLICK_IMAGE = 1 << 5
EVENT_ASSERT_EXISTS = 1 << 6
EVENT_ALL = EVENT_SCREENSHOT | EVENT_CLICK | EVENT_CLICK_IMAGE | EVENT_ASSERT_EXISTS | EVENT_SWIPE | EVENT_TYPE

LEVEL_DEFAULT = 1 << 0
LEVEL_HTML = 1 << 1
LEVEL_STACK = 1 << 2

__dir__ = os.path.dirname(os.path.abspath(__file__))


def report(level, out="out/"):
    def wrap(fn):
        @functools.wraps(fn)
        def _inner(*args, **kwargs):
            func_args = inspect.getcallargs(fn, *args, **kwargs)
            app = func_args['d']
            if not isinstance(app, Application):
                raise ValueError("report_log need a param d(android.Application) ")
            report_path = out + app.package
            if app.identity is not None and len(app.identity) > 0:
                report_path = report_path + '/' + app.identity + '/'
            rp = Reporter(app=app, path=report_path, level=level)
            app.add_listener(fn=rp.trigger, event_flags=EVENT_ALL)
            try:
                _result_val = fn(*args, **kwargs)
                return _result_val
            except Exception as e:
                raise e
            finally:
                app.remove_listener(fn=rp.trigger, event_flags=EVENT_ALL)
                rp.save()
                del rp

        return _inner

    return wrap


class ReportData(object):
    def __init__(self):
        self.saved = False
        self.steps = []
        self.result = None

    def header(self, width=0, height=0, serial=''):
        self.result = dict(
            device=dict(
                display=dict(width=width, height=height),
                serial=serial,
                start_time=time.strftime("%Y-%m-%d %H:%M:%S"),
                start_timestamp=time.time()
            ),
            steps=self.steps)

    def step(self, step_dict):
        step_dict['action'] = step_dict.pop('action', "unknow")
        step_dict['success'] = step_dict.pop('success', True)
        step_dict['description'] = step_dict.get('description') or step_dict.get('desc')
        step_dict['time'] = round(step_dict.pop('time', time.time() - step_dict.pop('start', 0)), 1)
        self.steps.append(step_dict)


class Reporter(object):
    def __init__(self, app, path='out/', level=LEVEL_DEFAULT):
        self.app = app
        self.path = path
        self.level = level
        self.saved = False
        self.cache = dict()
        self.data = ReportData()
        self.data.header(serial=app.serial)
        self.image_path = os.path.join(path, "images")
        if not os.path.exists(self.image_path):
            os.makedirs(self.image_path)
        if self.app is None or not isinstance(self.app, Application):
            raise ValueError("fail to create a Reporter,app should be type of android.Application")

    def trigger(self, hook):
        if not hook.done:
            self.__trigger_before(hook=hook)
        else:
            self.__trigger_after(hook=hook)

    def save(self):
        if atx.DEBUG and len(self.cache) > 0:
            raise ValueError("Missing cache:%,when save report", self.cache)
        if not self.saved:
            self.saved = True
            save_dir = self.path
            data = json.dumps(self.data.result)
            template_path = os.path.join(__dir__, 'index.tmpl.html')
            save_path = os.path.join(save_dir, 'index.html')
            json_path = os.path.join(save_dir, 'result.json')

            with codecs.open(template_path, 'rb', 'utf-8') as f:
                html_content = f.read().replace('$$data$$', data)

            with open(json_path, 'wb') as f:
                f.write(json.dumps(self.data.result, indent=4).encode('utf-8'))

            with open(save_path, 'wb') as f:
                f.write(html_content.encode('utf-8'))

    def __del__(self):
        self.save()

    def __point_saver(self, name='', screen=None, x=0, y=0):
        screen = imutils.from_pillow(screen)
        screen = imutils.mark_point(screen, x, y)
        return self.__image_saver(name=name, image=screen)

    def __image_saver(self, name='', image=None):
        path = "%s/%s%s.png" % (self.image_path, name, time.time())
        if image is None:
            self.app.screen_image().save(path)
        elif isinstance(image, str) or isinstance(image, unicode):
            shutil.copyfile(image, path)
        elif isinstance(image, Image):
            image.save(path)
        elif isinstance(image, numpy.ndarray):
            imutils.to_pillow(image).save(path)
        return path.replace(self.path + '/', '')

    def __enable_html(self):
        return self.level & LEVEL_HTML != 0

    def __enable_stack(self):
        return self.level & LEVEL_STACK != 0

    def __trigger_before(self, hook):
        before = dict()
        before['start'] = time.time()
        if self.__enable_html():
            before['bf_screen'] = self.app.screen_image()
        if self.__enable_stack():
            before['bf_activity'] = self.app.current_activity()
        self.cache[hook.tag] = before

    def __trigger_after(self, hook):
        after = self.cache.pop(hook.tag) if hook.tag in self.cache else dict()
        after['success'] = hook.traceback is None
        after['traceback'] = None if hook.traceback is None else hook.traceback.stack
        after['action'] = self.__action_from_flag(hook.flag)
        if self.__enable_html():
            target = None if 'local_object_path' not in hook.kwargs else hook.kwargs["local_object_path"]
            last = None if 'bf_screen' not in after else after.pop('bf_screen')
            current = self.app.screen_image()
            if hook.flag == consts.EVENT_CLICK:
                x, y = hook.args
                # x, y = mapping.computer(x, y)
                after['position'] = {'x': x, 'y': y}
                if last is not None:
                    after['screen_before'] = self.__point_saver('bf_tap', screen=last, x=x, y=y)
                if current is not None:
                    after['screen_after'] = self.__image_saver("at_tap", image=current)
            elif hook.flag == consts.EVENT_CLICK_IMAGE:
                if target is not None:
                    after['target'] = self.__image_saver('tg_tap_img', target)
                if last is not None:
                    if hook.result is not None:
                        x, y = hook.result
                        # x, y = mapping.computer(x, y)
                        after['position'] = {'x': x, 'y': y}
                        after['screen_before'] = self.__point_saver('bf_tap_img', screen=last, x=x, y=y)
                    else:
                        after['screen_before'] = self.__image_saver('tg_tap_img', last)
                if current is not None:
                    after['screen_after'] = self.__image_saver("at_tap_img", image=current)
            elif hook.flag == consts.EVENT_TYPE:
                after['description'] = hook.args
                if last is not None:
                    after['screen_before'] = self.__image_saver('bf_type', image=last)
                if current is not None:
                    after['screen_after'] = self.__image_saver("at_type", image=current)
            elif hook.flag == consts.EVENT_SWIPE:
                if last is not None:
                    after['screen_before'] = self.__image_saver('bf_swipe', image=last)
                if current is not None:
                    after['screen_after'] = self.__image_saver("at_swipe", image=current)
            elif hook.flag == consts.EVENT_ASSERT_EXISTS:
                after['success'] = hook.result
                if current is not None:
                    after['screenshot'] = self.__image_saver("check_exist", image=current)
            elif hook.flag == consts.EVENT_SCREENSHOT:
                if current is not None:
                    after['screenshot'] = self.__image_saver("shot", image=current)
            del last, current, target
        if self.__enable_stack():
            after['activity'] = self.app.current_activity()
        self.data.step(after)
        del after

    @staticmethod
    def __action_from_flag(flag):
        if flag == consts.EVENT_CLICK:
            return 'click'
        elif flag == consts.EVENT_CLICK_IMAGE:
            return 'click_image'
        elif flag == consts.EVENT_TYPE:
            return 'type'
        elif flag == consts.EVENT_SWIPE:
            return 'swipe'
        elif flag == consts.EVENT_ASSERT_EXISTS:
            return 'assert_exists'
        elif flag == consts.EVENT_SCREENSHOT:
            return 'screenshot'
        else:
            return 'unknow'


def json2obj(data):
    data['this'] = data.pop('self', None)
    return nameddict('X', data.keys())(**data)


def center(bounds):
    x = (bounds['left'] + bounds['right']) / 2
    y = (bounds['top'] + bounds['bottom']) / 2
    return x, y
