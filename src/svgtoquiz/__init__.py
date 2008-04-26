#!/usr/bin/env python

__all__ = ['options', 'svgmanip', 'mnemosyne',
	   'cvsgui', 'hasGUI', 'main', '__version__']

import options
import svgmanip
import mnemosyne
from version import __version__

try:
    import cvsgui
    hasGUI=True
except ImportError:
    hasGUI=False

options = options.options

