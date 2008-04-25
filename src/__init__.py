#!/usr/bin/env python

__all__ = ['options', 'svgmanip', 'mnemosyne', 'cvsgui', 'hasGUI']

import options
import svgmanip
import mnemosyne

try:
    import cvsgui
    hasGUI=True
except: hasGUI=False

from version import __version__
del version

options = options.options

