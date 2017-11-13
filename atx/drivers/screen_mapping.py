#!/usr/bin/env python
# -*- coding: utf-8 -*-

def enable():
    return False

def physical_size():
    '''width,height'''
    return (1920,1080)

def override_size():
    '''witdh,height'''
    return (1080,1992)

def mapping_size():
    '''width,height'''
    os = override_size()
    ps = physical_size()
    width = int(1.0*os[0]*ps[1]/os[1])
    height = ps[1]
    return (width,height)

def visible_area():
    ps = physical_size()
    ms = mapping_size()
    # center
    left = int((ps[0] - ms[0])/2.0)
    right = left + ms[0]
    # full height
    top = 0
    botton = ms[1]
    return (left,top,right,botton)

def computer(x=0,y=0):
    if enable():
        os = override_size()
        ms = mapping_size()
        mapping_x =int(1.0 * x * os[0] / ms[0])
        mapping_y =int(1.0 * y * os[1] / ms[1])
        return (mapping_x,mapping_y)
    else:
        return (x,y)
