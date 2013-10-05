#!/usr/bin/env python
#
# Copyright (c) 2013 Timothy Bourke. All rights reserved.
# 
# This program is free software; you can redistribute it and/or 
# modify it under the terms of the "BSD License" which is 
# distributed with the software in the file LICENSE.
# 
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the BSD
# License for more details.
#

__all__ = ['svgtoquiz', 'options', 'svgmanip', 'register_export_class',
	   'ExportFile', 'cvsgui', 'hasGUI', 'main', '__version__',
	   'OptionError', 'SvgError', 'ExportError']

import options
from options import OptionError
import svgmanip
from svgmanip import SvgError
from export import register_export_class, ExportFile, ExportError
from version import __version__
from main import main, svgtoquiz

try:
    import cvsgui
    hasGUI=True
except ImportError:
    hasGUI=False

del version
options = options.options

