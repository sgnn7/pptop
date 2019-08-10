import re
import pickle
import curses
import tabulate
import sys
import readline
import threading

from atasker import BackgroundIntervalWorker

tabulate.PRESERVE_WHITESPACE = True


class GenericPlugin(BackgroundIntervalWorker):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cursor = 0
        self.shift = 0
        self.hshift = 0
        mod = sys.modules[self.__module__]
        self.name = mod.__name__.rsplit('.', 1)[-1]
        self.title = None
        self.short_name = None
        self.stdscr = None  # curses stdscr object
        self.data = []
        self.dtd = []
        self.filter = ''
        self.sorting_col = None
        self.sorting_rev = True
        self.sorting_enabled = True
        self.cursor_enabled = True
        self.window = None
        self._visible = False

    def on_load(self):
        '''
        Executed on plugin load (on pptop startup)
        '''
        pass

    def on_unload(self):
        '''
        Executed on plugin unload (on pptop shutdown)
        '''
        pass

    def get_process(self):
        '''
        Get connected process

        Returns:
            psutil.Process object
        '''
        return None

    def get_process_path(self):
        '''
        Get sys.path of connected process

        Useful e.g. to format module names

        Returns:
            sys.path object
        '''
        return None

    def command(cmd, data=None):
        '''
        Execute command on connected process

        Args:
            cmd: command to execute
            data: command data (optional, free format)
        '''
        return None

    def handle_pager_event(self):
        '''
        Pager event handler
        '''
        height, width = self.window.getmaxyx()
        max_pos = len(self.dtd) - 1
        if self.key_event:
            if self.sorting_enabled:
                if self.key_event in ['kLFT3', 'kRIT3']:
                    if self.dtd:
                        cols = list(self.dtd[0])
                        if not self.sorting_col:
                            self.sorting_col = cols[0]
                        try:
                            pos = cols.index(self.sorting_col)
                            pos += 1 if self.key_event == 'kRIT3' else -1
                            if pos > len(cols) - 1:
                                pos = 0
                            elif pos < 0:
                                pos = len(cols) - 1
                            self.sorting_col = cols[pos]
                        except:
                            pass
                elif self.key_event == 'kDN3':
                    self.sorting_rev = False
                elif self.key_event == 'kUP3':
                    self.sorting_rev = True
            if self.key_event == 'KEY_LEFT':
                self.hshift -= 1
                if self.hshift < 0:
                    self.hshift = 0
            elif self.key_event == 'KEY_RIGHT':
                self.hshift += 1
            if self.key_event == 'KEY_DOWN':
                if self.cursor_enabled:
                    self.cursor += 1
                    if self.cursor > max_pos:
                        self.cursor = max_pos
                    if self.cursor - self.shift >= height - 1:
                        self.shift += 1
                else:
                    self.cursor += 1
                    self.shift += 1
            elif self.key_event == 'KEY_UP':
                if self.cursor_enabled:
                    self.cursor -= 1
                else:
                    self.cursor -= 1
                    self.shift -= 1
            elif self.key_event == 'KEY_NPAGE':
                self.cursor += height - 1
                self.shift += height - 1
            elif self.key_event == 'KEY_PPAGE':
                self.cursor -= height + 1
                self.shift -= height + 1
            elif self.key_event == 'KEY_HOME':
                self.hshift = 0
                self.cursor = 0
                self.shift = 0
            elif self.key_event == 'KEY_END':
                self.cursor = max_pos
                self.shift = max_pos - height + 2
            if self.cursor < 0:
                self.shift -= 1
                self.cursor = 0
            if self.cursor - self.shift < 0:
                self.cursor = self.shift - 1
                if self.cursor < 0: self.cursor = 0
                self.shift -= 1
            if self.shift < 0:
                self.shift = 0
        if max_pos == 0:
            self.cursor = 0
            self.shift = 0
        else:
            if self.cursor > max_pos:
                self.cursor = max_pos
                self.shift = max_pos - height + 2
                if self.shift < 0:
                    self.shift = 0
            if max_pos < height:
                self.shift = 0
                if self.cursor > max_pos:
                    self.cursor = max_pos - 1

    def print_section_title(self):
        '''
        Print section title
        '''
        height, width = self.stdscr.getmaxyx()
        self.stdscr.addstr(3, 0, ' ' + self.title.ljust(width - 1),
                           curses.color_pair(4) | curses.A_BOLD)
        self.stdscr.move(4, 0)
        self.stdscr.clrtoeol()

    def print_empty_sep(self):
        '''
        Print empty separator instead of table header
        '''
        height, width = self.stdscr.getmaxyx()
        self.stdscr.addstr(4, 0, ' ' * (width - 1),
                           curses.color_pair(3) | curses.A_REVERSE)

    def load_data(self):
        '''
        Load data from connected process

        Default method sends command cmd=<plugin_name>

        Returns:
            if False is returned, the plugin is stopped
        '''
        try:
            self.data = pickle.loads(self.command(self.name))
            return True
        except:
            return False

    def process_data(self):
        '''
        Format loaded data into table

        Returns:
            if False is returned, the plugin is stopped
        '''
        return True

    def sort_data(self):
        '''
        Sort data
        '''
        if self.sorting_enabled:
            if self.dtd:
                if not self.sorting_col:
                    self.sorting_col = list(self.dtd[0])[0]
                self.dtd = sorted(
                    self.dtd,
                    key=lambda k: k[self.sorting_col],
                    reverse=self.sorting_rev)

    def formatted_data(self, limit):
        '''
        Format part of data for rendering

        The method should use self.shift variable to determine current data
        offset

        Args:
            limit: max records limit

        Returns:
            The method should return generator object
        '''
        for d in self.dtd[self.shift:self.shift + limit - 1]:
            yield d

    def init_render_window(self):
        '''
        Init plugin working window
        '''
        height, width = self.stdscr.getmaxyx()
        self.window = curses.newwin(height - 6, width, 5, 0)

    def start(self, *args, **kwargs):
        if self.title is None:
            self.title = self.name.capitalize()
        if self.short_name is None:
            self.short_name = self.name[:6].capitalize()
        super().start(*args, **kwargs)
        self.on_start()

    def show(self):
        with self.scr_lock:
            self._visible = True
            self.init_render_window()
            self.print_section_title()
            self.output()

    def hide(self):
        with self.scr_lock:
            if self.window:
                self.window.move(0, 0)
                self.window.clrtoeol()
                self._visible = False
                self.stdscr.refresh()

    def stop(self, *args, **kwargs):
        super().stop(*args, **kwargs)
        self.hide()
        self.on_stop()

    def on_start(self):
        '''
        Called after plugin startup
        '''
        pass

    def on_stop(self):
        '''
        Called after plugin shutdown
        '''
        pass

    def resize(self):
        '''
        Automatically called on screen resize
        '''
        with self.scr_lock:
            self.init_render_window()
            self.print_section_title()
            self.key_event = 'KEY_RESIZE'
            self.handle_pager_event()
            self.output()

    def handle_key_event(self, event):
        '''
        Handle custom key event

        Args:
            event: curses getkey() event

        Returns:
            can return False to stop plugin
        '''
        return True

    def apply_filter(self):
        if not self.filter:
            self.dtd = self.data
        else:
            self.dtd.clear()
            self.stdscr.addstr(4, 1, 'f="')
            self.stdscr.addstr(self.filter,
                               curses.color_pair(5) | curses.A_BOLD)
            self.stdscr.addstr('"')
            self.stdscr.refresh()
            for d in self.data:
                for k, v in d.items():
                    if str(v).lower().find(self.filter) > -1:
                        self.dtd.append(d)
                        break

    def run(self, **kwargs):
        '''
        Primary plugin executor method
        '''
        if not self.key_event or self.key_event == ' ':
            if self.load_data() is False or self.process_data() is False:
                return False
        with self.scr_lock:
            if self._visible:
                return self.output()

    def output(self):
        self.stdscr.refresh()
        self.apply_filter()
        self.handle_pager_event()
        if self.handle_key_event(self.key_event) is False:
            return False
        if self.key_event:
            self.key_event = None
        self.sort_data()
        self.render()
        self.window.refresh()
        self.stdscr.refresh()
        return True

    def render(self):
        '''
        Renders plugin output
        '''
        height, width = self.window.getmaxyx()
        fancy_tabulate(
            self.window,
            self.formatted_data(height),
            cursor=(self.cursor - self.shift) if self.cursor_enabled else -1,
            hshift=self.hshift,
            sorting_col=self.sorting_col,
            sorting_rev=self.sorting_rev)


def format_mod_name(f, path):
    for p in path:
        if f.startswith(p):
            f = f[len(p) + 1:]
            break
    if f.endswith('.py'):
        f = f[:-3]
    return f.replace('/', '.')


def fancy_tabulate(stdscr,
                   table,
                   cursor=None,
                   hshift=0,
                   sorting_col=None,
                   sorting_rev=False):

    def format_str(s, width):
        return s[hshift:].ljust(width - 1)[:width - 1]

    stdscr.move(0, 0)
    stdscr.clrtobot()
    height, width = stdscr.getmaxyx()
    if table:
        d = tabulate.tabulate(table, headers='keys').split('\n')
        header = d[0]
        if sorting_col:
            if sorting_rev:
                s = '↑'
            else:
                s = '↓'
            if header.startswith(sorting_col + ' '):
                header = header.replace(sorting_col + ' ', s + sorting_col, 1)
            else:
                header = header.replace(' ' + sorting_col, s + sorting_col)
        stdscr.addstr(0, 0, format_str(header, width),
                      curses.color_pair(3) | curses.A_REVERSE)
        for i, t in enumerate(d[2:]):
            stdscr.addstr(
                1 + i, 0, format_str(t, width),
                curses.color_pair(7) | curses.A_REVERSE
                if cursor == i else curses.A_NORMAL)
    else:
        stdscr.addstr(0, 0, ' ' * (width - 1),
                      curses.color_pair(3) | curses.A_REVERSE)


ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')


def ansi_to_plain(txt):
    return ansi_escape.sub('', txt)


def print_ansi_str(stdscr, txt):
    stdscr.addstr(ansi_to_plain(txt))
    stdscr.clrtoeol()


from pptop.core import start
