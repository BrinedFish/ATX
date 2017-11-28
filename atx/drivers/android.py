#!/usr/bin/env python
# -*- coding: utf-8 -*-


from __future__ import absolute_import

import re
import os
import collections
import functools
import inspect
import traceback
import tempfile
import time
from atx import imutils
from atx.drivers import Pattern
from atx import consts
from atx.base import nameddict
import atx.utils.texts as texts
import atx.utils.adb as adb
import atx.utils.images as images
import atx.drivers.screen_mapping as mapping
from atx.utils.images import ImageNotFoundError

Traceback = collections.namedtuple('Traceback', ['stack', 'exception'])
HookEvent = nameddict('HookEvent', ['args', 'kwargs', 'tag', 'flag', 'result', 'traceback', 'done'])
ACTION_TIME = 0.3


def hook_wrap(event_type):
    def wrap(fn):
        @functools.wraps(fn)
        def _inner(*args, **kwargs):
            func_args = inspect.getcallargs(fn, *args, **kwargs)
            self = func_args.get('self')
            _tag = texts.unique(5)
            _traceback = None
            _result = None

            def trigger(event):
                for (f, event_flag) in self._listeners:
                    if event_flag & event_type:
                        event.args = args[1:]
                        event.kwargs = kwargs
                        event.flag = event_type
                        event.tag = _tag
                        event.result = _result
                        event.traceback = _traceback
                        f(event)

            try:
                trigger(HookEvent(done=False))
                _result = fn(*args, **kwargs)
                return _result
            except Exception as e:
                _traceback = Traceback(traceback.format_exc(), e)
                raise
            finally:
                trigger(HookEvent(done=True))

        return _inner

    return wrap


class Device(object):
    def __init__(self, serial=None, port=None):
        self.serial = serial
        self.port = port

    def cpu_usage(self):
        return adb.cpu_usage(serial=self.serial, port=self.port)

    def mem_usage(self):
        return adb.mem_usage(serial=self.serial, port=self.port)

    def temperature(self):
        return adb.temperature(serial=self.serial, port=self.port)

    def running_instance(self):
        pass

    def install(self, url):
        pass

    def uninstall(self, package):
        pass

    def dist_clean(self):
        pass

    def power_off(self):
        adb.power_off(serial=self.serial, port=self.port)

    def power_on(self):
        pass

    def reboot(self):
        adb.reboot(serial=self.serial, port=self.port)


class Application(object):
    def __init__(self, serial=None, port=None):
        self._listeners = []
        self.identity = None
        self.serial = serial
        self.port = port
        self.instance = None
        self.display_id = None
        self.package = None
        self.activity = None
        self.resource_path = None
        self.cache_image = None
        # adapt to old api
        self.display = (1920, 1080)
        self.local_only = True

    def info(self):
        pass

    def prepare(self):
        if len(adb.which(serial=self.serial, port=self.port, which_cmd="cv").strip()) == 0:
            self.local_only = False

    def attach(self, package=None, activity=None, resource_path=None, instance=None, display_id=None, identity=None):
        self.package = package
        self.activity = activity
        self.instance = instance
        self.display_id = display_id
        self.resource_path = resource_path  # r"tasks/res/%s/%s@auto.png"
        self.identity = identity

    def connect(self):
        adb.connect(serial=self.serial, port=self.port)

    def add_listener(self, fn, event_flags):
        self._listeners.append((fn, event_flags))

    def remove_listener(self, fn, event_flags):
        self._listeners.remove((fn, event_flags))

    def _trigger_event(self, event_flag, event):
        for (fn, flag) in self._listeners:
            if flag & event_flag:
                fn(event)

    def lunch(self):
        if self.package is None or self.activity is None:
            raise ValueError("app info should be attach before call lunch")
        adb.am_start(serial=self.serial,
                     port=self.port,
                     package_name=self.package,
                     activity_name=self.activity,
                     instance=self.instance)
        # TODO ensure lunch success

    def stop(self):
        if self.package is None:
            raise ValueError("app info should be attach before call stop")
        adb.am_force_stop(serial=self.serial,
                          port=self.port,
                          package_name=self.package,
                          instance=self.instance)

    @hook_wrap(consts.EVENT_SWIPE)
    def swipe(self, x1, y1, x2, y2):
        adb.swipe(serial=self.serial,
                  port=self.port,
                  instance=self.instance,
                  x1=x1,
                  y1=y1,
                  x2=x2,
                  y2=y2)
        time.sleep(ACTION_TIME)

    def tap(self, x, y):
        adb.tap(serial=self.serial,
                port=self.port,
                instance=self.instance,
                x=x,
                y=y)
        time.sleep(ACTION_TIME)

    @hook_wrap(consts.EVENT_TYPE)
    def type(self, msg):
        adb.type(serial=self.serial,
                 port=self.port,
                 instance=self.instance,
                 message=msg)

    def clear_type(self, count=20):
        while count > 0:
            adb.del_input(serial=self.serial, port=self.port, instance=self.instance)
            count = count - 1

    def screen_image(self):
        phone_tmp_file = self.__remote_tmp_path()
        local_tmp_file = self.__local_tmp_path()
        try:
            adb.screen_cap(serial=self.serial,
                           port=self.port,
                           remote_path=phone_tmp_file,
                           display_id=self.display_id)
            adb.pull(serial=self.serial,
                     port=self.port,
                     remote_path=phone_tmp_file,
                     local_path=local_tmp_file)

            return images.read(local_tmp_file, mapping.visible_area())
        except IOError:
            raise IOError("Screenshot failed.")
        finally:
            adb.rm(serial=self.serial, port=self.port, remote_path=phone_tmp_file)
            self.__remove_local_file(local_tmp_file)

    @hook_wrap(consts.EVENT_CLICK_IMAGE)
    def tap_image(self, key=None, local_object_path=None, timeout=15, frequency=0.2):
        if self.local_only:
            return self.__tap_image_remote(local_object_path=self.__get_path(key, local_object_path),
                                           timeout=timeout,
                                           frequency=frequency)
        else:
            return self.__tap_image_local(local_object_path=self.__get_path(key, local_object_path),
                                          timeout=timeout,
                                          frequency=frequency)

    @hook_wrap(consts.EVENT_ASSERT_EXISTS)
    def exists(self, key=None, local_object_path=None):
        local_object_path = self.__get_path(key, local_object_path)
        if self.local_only:
            self.__exist_remote(local_object_path)
        else:
            self.__exist_local(local_object_path)

    def wait_image(self, key=None, local_object_path=None, timeout=15, frequency=0.2):
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.exists(key=key, local_object_path=local_object_path):
                return
            else:
                time.sleep(frequency)

    def wait_image_gone(self, key=None, local_object_path=None, timeout=15, frequency=0.2):
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not self.exists(key=key, local_object_path=local_object_path):
                return
            else:
                time.sleep(frequency)

    def back(self):
        adb.back(serial=self.serial, port=self.port, instance=self.instance)
        time.sleep(ACTION_TIME)

    def home(self):
        adb.home(serial=self.serial, port=self.port, instance=self.instance)
        time.sleep(ACTION_TIME)

    def on_report(self):
        pass

    def __exist_local(self, local_object_path=None):
        try:
            images.match(target=local_object_path,
                         scanner=self.screen_image())
            return True
        except ImageNotFoundError:
            return False

    def __tap_image_local(self, local_object_path=None, timeout=15.0, frequency=0.2):
        target = images.read(local_object_path)
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                x, y = images.match(target, self.screen_image())
                x, y = mapping.computer(x, y)
                self.tap(x, y)
                return x, y
            except ImageNotFoundError:
                time.sleep(frequency)
                pass
        del target
        raise ImageNotFoundError('Not found image %s' % local_object_path)

    def __exist_remote(self, local_object_path=None):
        remote_target = self.__remote_tmp_path(True)
        adb.push(serial=self.serial, port=self.port, local_path=local_object_path, remote_path=remote_target)
        screen = self.__remote_tmp_path()
        try:
            adb.screen_cap(serial=self.serial,
                           port=self.port,
                           remote_path=screen,
                           display_id=self.display_id)
            cv = adb.match(serial=self.serial,
                           port=self.port,
                           remote_object_path=remote_target,
                           remote_scanner_path=screen)
            mapping.computer_match(cv)
            return True
        except (IOError, ImageNotFoundError):
            pass
        finally:
            adb.rm(serial=self.serial, port=self.port, remote_path=screen)
            adb.rm(serial=self.serial, port=self.port, remote_path=remote_target)
        return False

    def __tap_image_remote(self, local_object_path=None, timeout=15, frequency=0.2):
        remote_target = self.__remote_tmp_path(True)
        adb.push(serial=self.serial, port=self.port, local_path=local_object_path, remote_path=remote_target)
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                screen = self.__remote_tmp_path()
                adb.screen_cap(serial=self.serial,
                               port=self.port,
                               remote_path=screen,
                               display_id=self.display_id)
                cv = adb.match(serial=self.serial,
                               port=self.port,
                               remote_object_path=remote_target,
                               remote_scanner_path=screen)
                x, y = mapping.computer_match(cv)
                self.tap(x, y)
                return x, y
            except (IOError, ImageNotFoundError):
                time.sleep(frequency)
            finally:
                adb.rm(serial=self.serial, port=self.port, remote_path=screen)
        adb.rm(serial=self.serial, port=self.port, remote_path=remote_target)
        raise ImageNotFoundError('Not found image %s' % local_object_path)

    def __get_path(self, key=None, local_object_path=None):
        if key is None and local_object_path is None:
            raise ValueError("Illegal Argument")
        if key is not None and self.resource_path is not None:
            return self.resource_path % (self.package, key)
        return local_object_path

    @staticmethod
    def __remote_tmp_path(complexity=False):
        return '/data/local/tmp/atx_screen_%s.png' % texts.unique(None if complexity else 5)

    @staticmethod
    def __local_tmp_path(complexity=True):
        return tempfile.mktemp(prefix='atx_tmp_%s' % texts.unique(None if complexity else 5), suffix='.png')

    @staticmethod
    def __remove_local_file(name):
        if not os.path.isfile(name):
            return
        try:
            os.unlink(name)
        except Exception as e:
            print("Warning: local file {} not deleted, Error {}".format(name, e))

    # adapt to old api
    def press_back(self):
        self.back()

    def press_home(self):
        self.home()

    def click_image(self, pattern):
        self.tap_image(local_object_path=pattern)

    def wait(self, pattern, timeout=15):
        self.wait_image(local_object_path=pattern, timeout=timeout)

    def screenshot(self, filename=None):
        screen = self.screen_image()
        if filename:
            save_dir = os.path.dirname(filename) or '.'
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            screen.save(filename)
        return screen

    @hook_wrap(consts.EVENT_CLICK)
    def click(self, x, y):
        self.tap(x, y)

    @staticmethod
    def pattern_open(path):
        return Pattern('unknown', image=imutils.open(path))

    def current_activity(self):
        ai = self.current_app()
        return ai['package'] + '/' + ai['activity']

    def assert_activity(self, activity):
        return self.current_activity() == activity

    def current_app(self):
        _activityRE = re.compile(r'ACTIVITY (?P<package>[^/]+)/(?P<activity>[^/\s]+) \w+ pid=(?P<pid>\d+)')
        m = _activityRE.search(adb.shell(serial=self.serial, port=self.port, sh=['dumpsys', 'activity', 'top']))
        if m:
            return dict(package=m.group('package'), activity=m.group('activity'), pid=int(m.group('pid')))

        _focusedRE = re.compile('mFocusedApp=.*ActivityRecord{\w+ \w+ (?P<package>.*)/(?P<activity>.*) .*')
        m = _focusedRE.search(adb.shell(serial=self.serial, port=self.port, sh=['dumpsys', 'window', 'windows']))
        if m:
            return dict(package=m.group('package'), activity=m.group('activity'))
        raise RuntimeError("Couldn't get focused app")
