#!/usr/bin/env python
# coding: utf-8
#
# > How to get tkinter canvas to dynamically resize to window width?
# http://stackoverflow.com/questions/22835289/how-to-get-tkinter-canvas-to-dynamically-resize-to-window-width
#
# > Canvas tutoril
# http://www.tkdocs.com/tutorial/canvas.html
#
# > Canvas API reference
# http://effbot.org/tkinterbook/canvas.htm
#
# > Tutorial canvas tk
# http://www.tutorialspoint.com/python/tk_canvas.htm

import os
import threading
import logging, time
import Tkinter as tk
import tkFileDialog
from Queue import Queue

import atx
from atx import logutils
from PIL import Image, ImageTk
import atx.drivers.screen_mapping as mapping

log = logutils.getLogger('tkgui')
log.setLevel(logging.DEBUG)


def insert_code(filename, code, save=True, marker='# ATX CODE END'):
    """ Auto append code """
    content = ''
    found = False
    for line in open(filename, 'rb'):
        if not found and line.strip() == marker:
            found = True
            cnt = line.find(marker)
            content += line[:cnt] + code
        content += line
    if not found:
        if not content.endswith('\n'):
            content += '\n'
        content += code + marker + '\n'
    if save:
        with open(filename, 'wb') as f:
            f.write(content)
    return content


class CropIDE(object):
    def __init__(self, title='AirtestX Basic GUI', ratio=0.5, device=None):
        self._device = device
        self._root = tk.Tk()
        self._root.title(title)
        self._queue = Queue()

        self._refresh_text = tk.StringVar()
        self._refresh_text.set("Refresh")
        self._gencode_text = tk.StringVar()
        self._gen_code_text1 = tk.StringVar()
        self._type_text = tk.StringVar()
        self._commit_text = tk.StringVar()
        self._history_text = ''
        self._genfile_name = tk.StringVar()
        self._fileext_text = tk.StringVar()
        self._auto_refresh_var = tk.BooleanVar()
        self._auto_refresh_var.set(True)
        self._uiauto_detect_var = tk.BooleanVar()
        self._attachfile_text = tk.StringVar()
        self._running = False  # if background is running

        self._init_items()
        self._init_thread()
        self._init_refresh()

        self._lastx = 0
        self._lasty = 0
        self._bounds = None  # crop area
        self._center = (0, 0)  # center point
        self._offset = (0, 0)  # offset to image center
        self._poffset = (0, 0)
        self._size = (90, 90)
        self._moved = False  # click or click and move
        self._color = 'red'  # draw color
        self._tkimage = None  # keep reference
        self._image = None
        self._ratio = ratio
        self._uinodes = []  # ui dump
        self._selected_node = None
        self._hovered_node = None
        self._save_parent_dir = None

        self._init_vars()

    def _init_items(self):
        """
        .---------------.
        | Ctrl | Screen |
        |------|        |
        | Code |        |
        |      |        |
        """
        root = self._root
        root.resizable(0, 0)

        # controls
        frm_screen = tk.Frame(root, bg='#fff')
        frm_screen.grid(column=0, row=0)
        frm_control = tk.Frame(root, bg='#fff')
        frm_control.grid(column=1, row=0, padx=5, sticky=tk.NW)
        frm_controls_width = 40

        # refresh
        refresh_pad = tk.Frame(frm_control)
        refresh_pad.grid(column=0, row=0, sticky=tk.W)
        self._btn_refresh = tk.Button(refresh_pad,
                                      textvariable=self._refresh_text,
                                      width=(frm_controls_width-16)/2,
                                      command=self._refresh_screen)
        self._btn_refresh.grid(column=0, row=0, sticky=tk.W)
        tk.Button(refresh_pad,
                  text='Reset',
                  width=(frm_controls_width-16)/2,
                  command=self._reset).grid(column=1, row=0, sticky=tk.W)

        frm_checkbtns = tk.Frame(refresh_pad)
        frm_checkbtns.grid(column=2, row=0, sticky=(tk.W, tk.E))
        tk.Checkbutton(frm_checkbtns,
                       text="Auto refresh",
                       variable=self._auto_refresh_var,
                       width=14,
                       command=self._run_check_refresh).grid(column=0, row=0, sticky=tk.W)
        tk.Entry(frm_control, textvariable=self._gen_code_text1, width=frm_controls_width).grid(column=0, row=1, sticky=tk.EW)

        # save image for click
        tk.Label(frm_control, text='-Save image-').grid(column=0, row=5, sticky=tk.EW)
        image_pad = tk.Frame(frm_control)
        image_pad.grid(column=0, row=6, sticky=tk.EW)
        tk.Button(image_pad, text="SAVE", command=self._save_crop).grid(column=0, row=0, sticky=tk.EW)
        tk.Entry(image_pad, textvariable=self._genfile_name, width=frm_controls_width + 3).grid(column=0, row=3, sticky=tk.W)

        # generate code
        tk.Label(frm_control, text='-Generated code-').grid(column=0, row=10, sticky=tk.EW)
        code_pad = tk.Frame(frm_control)
        code_pad.grid(column=0, row=11, sticky=(tk.W, tk.E))
        tk.Entry(code_pad, textvariable=self._gencode_text, width=frm_controls_width).grid(column=0, row=1, sticky=tk.EW)

        run_pad = tk.Frame(code_pad)
        run_pad.grid(column=0, row=12, sticky=tk.EW)
        tk.Button(run_pad, text='RUN', command=self._run_code, width=6).grid(column=0, row=0, sticky=tk.W)
        tk.Entry(run_pad, textvariable=self._commit_text, width=frm_controls_width - 6).grid(column=1, row=0, sticky=tk.W)

        # run type
        tk.Label(frm_control, text='-Text type-').grid(column=0, row=15, sticky=tk.EW)
        type_pad = tk.Frame(frm_control)
        type_pad.grid(column=0, row=16, sticky=(tk.W, tk.E))
        tk.Entry(type_pad, textvariable=self._type_text, width=frm_controls_width + 3).grid(column=0, row=4, sticky=tk.W)
        tk.Button(type_pad, text='TYPE', command=self._run_type).grid(column=0, row=5, sticky=tk.EW)

        tk.Label(frm_control, text='-Function-').grid(column=0, row=20, sticky=tk.EW)
        func_pad = tk.Frame(frm_control)
        func_pad.grid(column=0, row=21, sticky=(tk.W, tk.E))
        tk.Button(func_pad, text='Back', width=6, command=self._back_code).grid(column=1, row=0, sticky=tk.W)
        tk.Button(func_pad, text='Home', width=6, command=self._home_code).grid(column=2, row=0, sticky=tk.W)
        tk.Button(func_pad, text='History', width=6, command=self._history_code).grid(column=3, row=0, sticky=tk.W)

        # screen
        self.canvas = tk.Canvas(frm_screen, bg="blue", bd=0, highlightthickness=0, relief='ridge')
        self.canvas.grid(column=0, row=0, padx=10, pady=10)
        self.canvas.bind("<Button-1>", self._stroke_start)
        self.canvas.bind("<B1-Motion>", self._stroke_move)
        self.canvas.bind("<B1-ButtonRelease>", self._stroke_done)
        self.canvas.bind("<Motion>", self._mouse_move)

    def _init_vars(self):
        self.draw_image(self._device.screenshot())
        if self._uiauto_detect_var.get():
            self._uinodes = self._device.dump_nodes()

    def _worker(self):
        que = self._queue
        while True:
            (func, args, kwargs) = que.get()
            try:
                func(*args, **kwargs)
            except Exception as e:
                print(e)
            finally:
                que.task_done()

    def _run_check_refresh(self):
        auto = self._auto_refresh_var.get()
        state = tk.DISABLED if auto else tk.NORMAL
        self._btn_refresh.config(state=state)

    def _run_async(self, func, args=(), kwargs={}):
        self._queue.put((func, args, kwargs))

    def _init_thread(self):
        th = threading.Thread(name='thread', target=self._worker)
        th.daemon = True
        th.start()

    def _init_refresh(self):
        if not self._running and self._auto_refresh_var.get():
            self._refresh_screen()
        self._root.after(200, self._init_refresh)

    def _fix_bounds(self, bounds):
        bounds = [x / self._ratio for x in bounds]
        (x0, y0, x1, y1) = bounds
        if x0 > x1:
            x0, y0, x1, y1 = x1, y1, x0, y0
        # in case of out of bounds
        w, h = self._size
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(w, x1)
        y1 = min(h, y1)
        return map(int, [x0, y0, x1, y1])

    @property
    def select_bounds(self):
        if self._bounds is None:
            return None
        return self._fix_bounds(self._bounds)

    def _fix_path(self, path):
        try:
            return os.path.relpath(path, os.getcwd())
        except:
            return path

    def _save_screenshot(self):
        save_to = tkFileDialog.asksaveasfilename(**dict(
            defaultextension=".png",
            filetypes=[('PNG', '.png')],
            title='Select file'))
        if not save_to:
            return
        log.info('Save to: %s', save_to)
        self._image.save(save_to)

    def _save_crop(self):
        log.debug('crop bounds: %s', self._bounds)
        if self._bounds is None:
            return
        bounds = self.select_bounds
        # ext = '.%dx%d.png' % tuple(self._size)
        # tkFileDialog doc: http://tkinter.unpythonic.net/wiki/tkFileDialog
        save_to = tkFileDialog.asksaveasfilename(**dict(
            initialdir=self._save_parent_dir,
            defaultextension=".png",
            filetypes=[('PNG', ".png")],
            title='Select file'))
        if not save_to:
            return
        save_to = self._fix_path(save_to)
        # force change extention with info (resolution and offset)
        save_to = os.path.splitext(save_to)[0] + self._fileext_text.get()

        self._save_parent_dir = os.path.dirname(save_to)

        log.info('Crop save to: %s', save_to)
        self._image.crop(bounds).save(save_to)
        self._genfile_name.set(os.path.basename(save_to))
        self._gencode_text.set('d.click_image(r"%s")' % save_to)

    def _run_code(self):
        code = self._gencode_text.get()
        self.__run_run(code=code)
        self._gencode_text.set('d.')

    def _run_type(self):
        code = "d.type('%s')" % self._type_text.get()
        self.__run_run(code=code)

    def _back_code(self):
        self.__run_run(code='d.press_back()')

    def _home_code(self):
        self.__run_run(code='d.press_home()')

    def __run_run(self, code):
        commit = self._commit_text.get()
        d = self._device
        logging.debug("run code: %s", d)
        if len(commit) > 0:
            self._history_text = self._history_text + "# " + commit + "\n"
            self._commit_text.set('')
        self._history_text = self._history_text + str(code) + "\n"
        exec (code)
        self._refresh_screen()

    def _history_code(self):
        print "---\n"
        print "import atx"
        print "d=atx.connect()"
        print self._history_text
        print "---"

    def _refresh_screen(self):
        def foo():
            self._running = True
            image = self._device.screenshot()
            self.draw_image(image)
            self._refresh_text.set("Refresh")
            self._gen_code_text1.set(self._device.current_activity())

            self._draw_lines()
            self._running = False

        self._run_async(foo)
        self._refresh_text.set("Refresh")

    def _stroke_start(self, event):
        self._moved = False
        c = self.canvas
        self._lastx, self._lasty = c.canvasx(event.x), c.canvasy(event.y)
        log.debug('mouse position: %s', (self._lastx, self._lasty))

    def _stroke_move(self, event):
        self._moved = True
        self._reset()
        c = self.canvas
        x, y = c.canvasx(event.x), c.canvasy(event.y)
        self._bounds = (self._lastx, self._lasty, x, y)
        self._center = (self._lastx + x) / 2, (self._lasty + y) / 2
        self._draw_lines()

    def _stroke_done(self, event):
        c = self.canvas
        x, y = c.canvasx(event.x), c.canvasy(event.y)
        if self._moved:  # drag action
            x, y = (self._lastx + x) / 2, (self._lasty + y) / 2
            self._offset = (0, 0)
        else:
            # click action
            if self._bounds is None:
                cx, cy = (x / self._ratio, y / self._ratio)
                cx, cy = mapping.computer(cx, cy)
                if self._uiauto_detect_var.get() and self._hovered_node:
                    self._selected_node = self._hovered_node
                    log.debug("select node: %s", repr(self._selected_node))
                    log.debug("center: %s", self._selected_node.bounds.center)
                    # self._device.click(cx, cy)

                self._gencode_text.set('d.click(%d, %d)' % (cx, cy))
            else:
                (x0, y0, x1, y1) = self.select_bounds
                ww, hh = x1 - x0, y1 - y0
                cx, cy = (x / self._ratio, y / self._ratio)
                cx, cy = mapping.computer(cx, cy)
                mx, my = (x0 + x1) / 2, (y0 + y1) / 2
                self._offset = (offx, offy) = map(int, (cx - mx, cy - my))
                poffx = ww and round(offx * 100.0 / ww)
                poffy = hh and round(offy * 100.0 / hh)
                self._poffset = (poffx, poffy)
                self._gencode_text.set('(%d, %d)' % (cx, cy))

        ext = ".%dx%d" % mapping.physical_size()
        if self._poffset != (0, 0):
            px, py = self._poffset
            ext += '.%s%d%s%d' % (
                'R' if px > 0 else 'L', abs(px), 'B' if py > 0 else 'T', abs(py))
        ext += '.png'
        self._fileext_text.set(ext)
        self._center = (x, y)  # rember position
        self._draw_lines()
        self.canvas.itemconfigure('select-bounds', width=2)

    def draw_image(self, image):
        self._image = image
        self._size = (width, height) = image.size
        w, h = int(width * self._ratio), int(height * self._ratio)
        image = image.copy()
        image.thumbnail((w, h), Image.ANTIALIAS)
        tkimage = ImageTk.PhotoImage(image)
        self._tkimage = tkimage  # keep a reference
        self.canvas.config(width=w, height=h)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=tkimage)

    def _draw_bounds(self, bounds, color=None, tags='select-bounds'):
        if not color:
            color = self._color
        c = self.canvas
        (x0, y0, x1, y1) = bounds
        c.create_rectangle(x0, y0, x1, y1, outline=color, tags='select-bounds', width=2)

    def _draw_lines(self):
        if self._center and self._center != (0, 0):
            x, y = self._center
            self.draw_point(x, y)
        if self._bounds:
            self._draw_bounds(self._bounds)
        if self._hovered_node:
            # print self._hovered_node.bounds
            bounds = [v * self._ratio for v in self._hovered_node.bounds]
            self._draw_bounds(bounds, color='blue', tags='ui-bounds')

    def _reset(self):
        self._bounds = None
        self._offset = (0, 0)
        self._poffset = (0, 0)
        self._center = (0, 0)
        self.canvas.delete('select-bounds')
        self.canvas.delete('select-point')
        self.canvas.delete('ui-bounds')

    def _mouse_move(self, event):
        if not self._uiauto_detect_var.get():
            return
        c = self.canvas
        x, y = c.canvasx(event.x), c.canvasy(event.y)
        x, y = x / self._ratio, y / self._ratio
        # print x, y
        hovered_node = None
        min_area = None
        for node in self._uinodes:
            if node.bounds.is_inside(x, y):
                if min_area is None or node.bounds.area < min_area:
                    hovered_node = node
                    min_area = node.bounds.area
        if hovered_node:
            self._hovered_node = hovered_node
            self._reset()
            self._draw_lines()

    def draw_point(self, x, y):
        self.canvas.delete('select-point')
        r = max(min(self._size) / 30 * self._ratio, 5)
        self.canvas.create_line(x - r, y, x + r, y, width=2, fill=self._color, tags='select-point')
        self.canvas.create_line(x, y - r, x, y + r, width=2, fill=self._color, tags='select-point')

    def mainloop(self):
        self._root.mainloop()


def main(serial, host='127.0.0.1', scale=0.5):
    log.debug("gui starting(scale: {}) ...".format(scale))
    device = atx.connect(serial, host=host, platform='android')
    serial = device.serial
    gui = CropIDE('ATX GUI SN: %s' % serial, ratio=scale, device=device)
    gui.mainloop()


def test():
    gui = CropIDE('AirtestX IDE')
    image = Image.open('screen.png')
    gui.draw_image(image)
    gui.draw_point(100, 100)
    gui.mainloop()


if __name__ == '__main__':
    main(None)
