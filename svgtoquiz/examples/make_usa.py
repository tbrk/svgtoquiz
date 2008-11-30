#!/usr/bin/env python

# Example python script that invokes svgtoquiz

from svgtoquiz import svgtoquiz, OptionError, SvgError, ExportError
import sys

try:
    r= svgtoquiz(['-d', '/tmp/TEST',
		  '--export=ndsrs(fontsize=18)',
		  '--randomize',
		  '--name=States_of_the_USA',
		  '--id-regex=^(..)_1_$'
		 ] + sys.argv[1:] + ['Map_of_USA'])
except OptionError, e: e.show(); r = 1
except SvgError, e: e.show(); r = 2 
except ExportError, e: e.show(); r = 3

sys.exit(r)
