from importlib import import_module
import inspect
from table import Table
from bitstream import BitStream
from doc import Doc

class Plugin:
    def __init__(self):
        self.exports = {}
        self.doc = Doc()
        self.default = ''
        self.name = ''

def load_plugin(name):
    mod = import_module('.main', 'plugins.'+name)
    bs = BitStream(bytes([]))
    t = Table('inspect', None, bs)
    plugin = Plugin()
    plugin.name = name

    for attr in dir(mod):
        if attr.startswith('__'):
            continue
        obj = getattr(mod, attr)
        if not inspect.isfunction(obj):
            continue
        sig = inspect.signature(obj)
        try:
            sig.bind(t, bs)
            if attr == 'default_parser':
                plugin.default = attr
            plugin.exports[attr] = obj
        except TypeError as e:
            continue

    if len(plugin.default) == 0 and len(plugin.exports) > 0:
        plugin.default = list(plugin.exports.keys())[0]
    plugin.doc.parse('plugins/'+name+'/doc.md')
    return plugin
