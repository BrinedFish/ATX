#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Yeshen'

from atx.utils import time_log
import atx.utils.texts as texts

try:
    import subprocess32 as subprocess
except:
    import subprocess


def __adb_path():
    return "adb"


def __adb_host():
    return "localhost"


def __adb_port():
    return "5037"


def run(serial=None, port=5037, cmd=list(), host=None, stdout=None, stderr=None):
    cmdline = [__adb_path()]
    if serial is not None and len(serial) > 0:
        cmdline = cmdline + ["-s", serial]
    if port is not None:
        cmdline = cmdline + ["-P", port]
    if host is not None and len(host) > 0:
        cmdline = cmdline + ["-H", host]
    cmdline = cmdline + cmd
    if stdout is None:
        stdout = subprocess.PIPE
    if stderr is None:
        stderr = subprocess.PIPE
    return subprocess.Popen(cmdline, stdout=stdout, stderr=stderr
                            ).communicate()[0].decode('utf-8').replace('\r\n', '\n')


def su(serial, port, su_cmd=list()):
    if len(su_cmd) > 0:
        cmd = ["su", "-c", "'%s'" % texts.strip(su_cmd)]
        shell(serial=serial, port=port, sh=cmd)


def am(serial, port, am_cmd=list()):
    cmd = ["am"] + am_cmd
    shell(serial=serial, port=port, sh=cmd)


def pm(serial, port, pm_cmd=list()):
    cmd = ["pm"] + pm_cmd
    shell(serial=serial, port=port, sh=cmd)


def inputs(serial, port, input_cmd=list(), instance=0):
    # TODO handle instance
    cmd = ["input"] + input_cmd
    shell(serial=serial, port=port, sh=cmd)


def dumpsys(serial, port, dumpsys_cmd=list()):
    cmd = ["dumpsys"] + dumpsys_cmd
    shell(serial=serial, port=port, sh=cmd)


def shell(serial, port, sh=list()):
    cmd = ["shell"] + sh
    return run(serial=serial, port=port, cmd=cmd)


@time_log
def connect(serial, port):
    cmd = ["connect", serial]
    output = run(port=port, cmd=cmd)
    return 'unable to connect' not in output


@time_log
def disconnect(serial, port):
    cmd = ["disconnect", serial]
    return run(port=port, cmd=cmd).wait()


@time_log
def forward(serial, local_port, remote_port=None):
    cmd = ["forward", "tcp:%d" % local_port, "tcp:%d" % remote_port]
    run(serial=serial, cmd=cmd)


@time_log
def am_force_stop(serial, port, package_name, instance):
    pk = "%s@#%s" % (package_name, instance)
    cmd = ["force-stop", pk]
    am(serial=serial, port=port, am_cmd=cmd)


@time_log
def am_start(serial, port, package_name, activity_name, instance):
    ac = "%s/%s" % (package_name, activity_name)
    cmd = ["start", ac]
    am(serial=serial, port=port, am_cmd=cmd)


@time_log
def pm_install(serial, port, local_path):
    cmd = ["install", local_path]
    pm(serial=serial, port=port, pm_cmd=cmd)


@time_log
def pm_uninstall(serial, port, package_name):
    cmd = ["uninstall", package_name]
    pm(serial=serial, port=port, pm_cmd=cmd)


@time_log
def type(serial, port, message, instance=0):
    if texts.is_ascii(message):
        _type(serial=serial, port=port, message=message, instance=instance)
    else:
        _type_chinese(serial=serial, port=port, message=message, instance=instance)


@time_log
def _type(serial, port, message, instance=0):
    cmd = ["text", texts.strip(message)]
    inputs(serial=serial, port=port, input_cmd=cmd, instance=instance)


@time_log
def _type_chinese(serial, port, message, instance=0):
    cmd = ["chinese", texts.strip(message)]
    inputs(serial=serial, port=port, input_cmd=cmd, instance=instance)


@time_log
def tap(serial, port, x, y, instance=0):
    cmd = ["tap", str(x), str(y)]
    inputs(serial=serial, port=port, input_cmd=cmd, instance=instance)


@time_log
def swipe(serial, port, x1, y1, x2, y2, instance=0):
    cmd = ["swipe", str(x1), str(y1), str(x2), str(y2)]
    inputs(serial=serial, port=port, input_cmd=cmd, instance=instance)


def key_event(serial, port, key, instance=0):
    cmd = ["keyevent", key]
    inputs(serial=serial, port=port, input_cmd=cmd, instance=instance)


@time_log
def back(serial, port, instance=0):
    key_event(serial=serial, port=port, key="KEYCODE_BACK", instance=instance)


@time_log
def home(serial, port, instance=0):
    key_event(serial=serial, port=port, key="KEYCODE_HOME", instance=instance)


@time_log
def del_input(serial, port, instance=0):
    key_event(serial=serial, port=port, key="KEYCODE_DEL", instance=instance)


@time_log
def screen_cap(serial, port, remote_path, display_id=None):
    if display_id is None:
        cmd = ["screencap", "-p", remote_path]
    else:
        cmd = ["screencap", "-p", remote_path, "-d", str(display_id)]
    shell(serial=serial, port=port, sh=cmd)


@time_log
def match(serial, port, remote_object_path, remote_scanner_path):
    cmd = ["cv", "match", remote_object_path, remote_scanner_path]
    return shell(serial=serial, port=port, sh=cmd)


@time_log
def push(serial, port, local_path, remote_path):
    cmd = ["push", local_path, remote_path]
    run(serial=serial, port=port, cmd=cmd)


@time_log
def pull(serial, port, remote_path, local_path):
    cmd = ["pull", remote_path, local_path]
    run(serial=serial, port=port, cmd=cmd)


@time_log
def sync(serial, port, remote_path, local_path):
    # TODO to be test
    cmd = ["sync", remote_path, local_path]
    run(serial=serial, port=port, cmd=cmd)


@time_log
def power_off(serial, port):
    run(serial=serial, port=port, cmd=["poweroff"])


@time_log
def reboot(serial, port):
    run(serial=serial, port=port, cmd=["reboot"])


def which(serial, port, which_cmd):
    cmd = ["which", which_cmd]
    return shell(serial=serial, port=port, sh=cmd)


def rm(serial, port, remote_path):
    if isinstance(remote_path, str):
        cmd = ["rm", "-r", remote_path]
    elif isinstance(remote_path, list):
        cmd = ["rm", "-r"] + remote_path
    else:
        raise ValueError("un except input")
    shell(serial=serial, port=port, sh=cmd)


@time_log
def cpu_usage(serial, port):
    cmd = "adb -s %s -p %s shell top -bn1" % (serial, port)
    cmd += " | grep 'cpu' | grep 'user' | awk  '{print $1}{print $5}' | cut -d '%' -f1"
    pipe = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    error = pipe.stderr.readline().strip()
    cpu = pipe.stdout.readline().strip()
    idle = pipe.stdout.readline().strip()
    pipe.stdout.close()
    pipe.stderr.close()
    if len(error) > 0:
        raise ValueError(error)
    if cpu and idle and idle.isdigit() and cpu.isdigit():
        return 1 - float(idle) / float(cpu)
    return 0


@time_log
def mem_usage(serial, port):
    cmd = "adb -s %s -p %s  shell top -bn1" % (serial, port)
    cmd += " | grep 'Mem:' | grep 'total' | awk '{print $2}{print $4 }' | cut -d 'k' -f1"
    pipe = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    error = pipe.stderr.readline().strip()
    total = pipe.stdout.readline().strip()
    used = pipe.stdout.readline().strip()
    pipe.stdout.close()
    pipe.stderr.close()
    if len(error) > 0:
        raise ValueError(error)
    if total and used and used.isdigit() and total.isdigit():
        return float(used) / float(total)
    return 0


@time_log
def temperature(serial, port):
    cmd = "adb -s %s -p %s shell dumpsys battery | grep 'temperature' | cut -d ':' -f2" % (serial, port)
    pipe = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = pipe.stdout.readline().strip()
    error = pipe.stderr.readline().strip()
    pipe.stdout.close()
    pipe.stderr.close()
    if len(error) > 0:
        raise ValueError(error)
    if out and out.isdigit():
        return float(out) / 10
    return 0
