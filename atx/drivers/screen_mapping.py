#!/usr/bin/env python
# -*- coding: utf-8 -*-


from atx.utils.images import ImageNotFoundError


def enable():
    return False


def physical_size():
    """width,height"""
    return 1920, 1080


def override_size():
    """width,height"""
    return 1080, 1992


def mapping_size():
    """width,height"""
    os = override_size()
    ps = physical_size()
    width = int(1.0 * os[0] * ps[1] / os[1])
    height = ps[1]
    return width, height


def visible_area():
    if enable():
        ps = physical_size()
        ms = mapping_size()
        # center
        left = int((ps[0] - ms[0]) / 2.0)
        right = left + ms[0]
        # full height
        top = 0
        button = ms[1]
        return left, top, right, button
    else:
        return None


def computer(x=0, y=0):
    if enable():
        os = override_size()
        ms = mapping_size()
        mapping_x = int(1.0 * x * os[0] / ms[0])
        mapping_y = int(1.0 * y * os[1] / ms[1])
        return mapping_x, mapping_y
    else:
        return x, y


def revise_computer(x=0, y=0):
    if enable():
        os = override_size()
        ms = mapping_size()
        mapping_x = int(1.0 * x * ms[0] / os[0])
        mapping_y = int(1.0 * y * ms[1] / os[1])
        return mapping_x, mapping_y
    else:
        return x, y


def computer_match(cv):
    if cv is None or isinstance(cv, str):
        raise ValueError("computer_match should input a str")
    cv = cv.strip()
    points = cv.split("|")
    if len(cv) == 0 or len(points) < 4:
        raise ImageNotFoundError("not found")
    match_x = 0
    match_y = 0
    count = 0
    visible_left, visible_top, _, _ = visible_area()
    for point in points:
        if len(point) > 0:
            x, y = point.split(",")
            match_x = match_x + int(x)
            match_y = match_y + int(y)
            count = count + 1
    match_x = match_x / count - visible_left
    match_y = match_y / count - visible_top
    return computer(x=match_x, y=match_y)
