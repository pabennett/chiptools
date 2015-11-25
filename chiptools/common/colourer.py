import logging
import sys
import os

try:
    # If colorama is available use it, otherwise turn colours off (win only)
    import colorama
except ImportError:
    colorama = None

_colours = [
    ('black',     'darkgray'),
    ('darkred',   'red'),
    ('darkgreen', 'green'),
    ('brown',     'yellow'),
    ('darkblue',  'blue'),
    ('purple',    'fuchsia'),
    ('turquoise', 'teal'),
    ('lightgray', 'white'),
]

_attrs = {
    'reset':     '39;49;00m',
    'bold':      '01m',
    'faint':     '02m',
    'standout':  '03m',
    'underline': '04m',
    'blink':     '05m',
}

foreground_codes = {}
background_codes = {}
function_codes = {}

for i, (dark, light) in enumerate(_colours):
    foreground_codes[dark] = '\x1b[%im' % (i+30)
    foreground_codes[light] = '\x1b[%i;01m' % (i+30)
    background_codes[dark] = '\x1b[%im' % (i+40)
    background_codes[light] = '\x1b[%i;01m' % (i+40)

for name, value in _attrs.items():
    function_codes[name] = '\x1b[' + value


def create_named_functions(name):
    def wrapped(text):
        return colourise(text, fg=name)
    globals()[name] = wrapped

# Create functions so that the colour names can be called directly outside of
# this module. Note that this has the limitation of not allowing foreground,
# background and effect codes to be combined, use a direct call to colourise
# to achieve this.
for name in foreground_codes:
    create_named_functions(name)
for name in function_codes:
    create_named_functions(name)
for name in background_codes:
    create_named_functions('bg' + name)


def colour_terminal():
    if sys.platform == 'win32' and colorama is not None:
        colorama.init()
        return True
    if not hasattr(sys.stdout, 'isatty'):
        return False
    if not sys.stdout.isatty():
        return False
    if 'COLORTERM' in os.environ:
        return True
    term = os.environ.get('TERM', 'dumb').lower()
    if term in ('xterm', 'linux') or 'color' in term:
        return True
    return False


def colourise(text, fg=None, bg=None, fn=None):
    return (
        foreground_codes.get(fg, '') +
        background_codes.get(bg, '') +
        function_codes.get(fn, '') +
        text +
        function_codes.get('reset', '')
    )


class ColouredStreamHandler(logging.StreamHandler):
    """Use this class in place of a logging.StreamHandler if coloured log
    output is desired. The ColouredStreamHandler will not output coloured text
    on Windows platforms if colorama is not installed"""

    _levels = {
        'INFO': ('green', ''),
        'DEBUG': ('teal', ''),
        'WARNING': ('yellow', ''),
        'ERROR': ('red', ''),
        'CRITICAL': ('white', 'red'),
    }

    @staticmethod
    def add_colour(msg, levelname):
        if levelname in ColouredStreamHandler._levels:
            fg, bg = ColouredStreamHandler._levels[levelname]
            msg = colourise(msg, fg=fg, bg=bg)
        return msg

    def emit(self, record):
        try:
            msg = ColouredStreamHandler.add_colour(
                self.format(record) + '\n',
                record.levelname
            )
            self.stream.write(msg)
            self.flush()
        except:
            self.handleError(record)
