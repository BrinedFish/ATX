#!/usr/bin/env python
# -*- coding: utf-8 -*-

# USAGE
# python -m atx -s serial gui

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function

import argparse
import sys
import inspect
from contextlib import contextmanager


def inject(func, kwargs):
    args = []
    for name in inspect.getargspec(func).args:
        args.append(kwargs.get(name))
    return func(*args)


def load_main(module_name):
    def _inner(parser_args):
        module_path = 'atx.cmds.'+module_name
        __import__(module_path)
        mod = sys.modules[module_path]
        pargs = vars(parser_args)
        return inject(mod.main, pargs)
    return _inner


def main():
    ap = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument("-s", "--serial", "--udid", required=False, help="Android serial or iOS unid")
    ap.add_argument("-H", "--host", required=False, default='127.0.0.1', help="Adb host")
    ap.add_argument("-P", "--port", required=False, type=int, default=5037, help="Adb port")

    subp = ap.add_subparsers()

    @contextmanager
    def add_parser(name):
        yield subp.add_parser(name, formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    with add_parser('gui') as p:
        p.description = 'GUI tool to help write test script'
        p.add_argument('-p', '--platform', default='auto', choices=('auto', 'android', 'ios'), help='platform')
        p.add_argument('-s', '--serial', default=None, type=str, help='android serial or WDA device url')
        p.add_argument('--scale', default=0.5, type=float, help='scale size')
        p.set_defaults(func=load_main('tkgui'))

    args = ap.parse_args()
    if not hasattr(args, 'func'):
        print(' '.join(sys.argv) + ' -h for more help')
        return
    args.func(args)


if __name__ == '__main__':
    main()
