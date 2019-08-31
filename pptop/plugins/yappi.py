from pptop.plugin import GenericPlugin, format_mod_name, not_my_mod
from pptop.plugin import abspath, palette

from collections import OrderedDict


class Plugin(GenericPlugin):
    '''
    yappi plugin: function profiler

    requires yappi profiler module https://github.com/sumerc/yappi
    '''

    def on_load(self):
        self.short_name = 'Prof'
        self.title = 'Function profiler (yappi)'
        self.sorting_col = 'ttot'
        self.background_loader = True

    def handle_key_event(self, event, key, dtd, **kwargs):
        if event == 'reset':
            self.injection_command(cmd='reset')
            self.print_message('Profiler stats were reset',
                               color=palette.WARNING)

    def process_data(self, data):
        sess = []
        for s in data:
            mod = format_mod_name(s[1])
            if not_my_mod(mod):
                d = OrderedDict()
                d['function'] = '{}.{}'.format(mod, s[0])
                d['ncall'] = s[3]
                d['nacall'] = s[4]
                d['ttot'] = s[6]
                d['tsub'] = s[7]
                d['tavg'] = s[11]
                d['file'] = '{}:{}'.format(abspath(s[1]), s[2])
                d['builtin'] = 'builtin' if s[5] else ''
                sess.append(d)
        return sess

    def format_dtd(self, dtd):
        ks = ['ttot', 'tsub', 'tavg']
        for s in dtd:
            z = s.copy()
            for k in ks:
                z[k] = '{:.3f}'.format(z[k])
            yield z

    def get_table_col_color(self, element, key, value):
        if key == 'function':
            return palette.BOLD
        elif key in ['ncall', 'nacall']:
            return palette.CYAN
        elif key == 'file':
            return
        else:
            return palette.GREEN

    async def run(self, *args, **kwargs):
        super().run(*args, **kwargs)


def injection_load(**kwargs):
    import yappi
    if not yappi.is_running():
        yappi.start()


def injection_unload(**kwargs):
    import yappi
    if yappi.is_running():
        yappi.stop()


def injection(cmd=None, **kwargs):
    import yappi
    if cmd == 'reset':
        yappi.clear_stats()
        return True
    else:
        if not yappi.is_running():
            yappi.start()
        d = list(yappi.get_func_stats())
        for v in d:
            del v[9]
        return d
