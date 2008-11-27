#!/usr/bin/env python
#
# $Id$
#
# Copyright (c) 2008 Timothy Bourke. All rights reserved.
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

__all__ = ['options', 'svgmanip', 'register_export_class',
	   'ExportFile', 'cvsgui', 'hasGUI', 'main', '__version__']

import options
import svgmanip
from export import register_export_class, ExportFile
from version import __version__
from main import main

try:
    import cvsgui
    hasGUI=True
except ImportError:
    hasGUI=False

del version
options = options.options

