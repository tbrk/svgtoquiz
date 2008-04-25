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
# 20080324 T. Bourke
#   Original code to generate a Mnemosyne quiz from an SVG file.
#
# REQUIRES:
#   * Developed in python 2.5
#   * Requires rsvg (part of librsvg2)
#     although it could be modified to support any svg->png converter.
#   * threading
#   * xml.dom.minidom
#

import sys, os, codecs
import xml.dom.minidom
from svgtoquiz import *

import locale
locale.setlocale(locale.LC_ALL, '')

def main():
    try: mapdom = xml.dom.minidom.parse(options.srcpath_svg)
    except IOError, e:
	print >> sys.stderr, 'Could not open ' + options.srcpath_svg,
	print >> sys.stderr, '(' + e.strerror + ')'
	sys.exit(1)

    svgs = mapdom.getElementsByTagName('svg')
    if svgs.length == 0:
	print >> sys.stderr, 'The document does not contain an svg element.'
	sys.exit(1)
    svg = svgs[0]

    if options.srcpath_csv:
	try: name_map = svgmanip.read_name_map(options.srcpath_csv)
	except svgmanip.BadCSVEncoding:
	    print >> sys.stderr, 'Bad encoding: ' + options.srcpath_csv,
	    print >> sys.stderr, '(expected ' + options.csvencoding + ')'
	    sys.exit(1)
	except:
	    if not hasGUI:
		print >> sys.stderr, 'Unable to read ' + options.srcpath_csv
	    name_map = None
    else:
	name_map = None

    if options.run_csvgui:
	if hasGUI:
	    cvsgui.start(mapdom, svg, name_map)
	else:
	    print >> sys.stderr, 'Sorry, the GUI feature is not available.'
	    print >> sys.stderr, 'One of the requirements is not satisfied:'
	    print >> sys.stderr, '  * svgtoquiz_gui.py in same directory'
	    print >> sys.stderr, '  * Tkinter and tkMessageBox (python-tk)'
	    print >> sys.stderr, '  * Python Image Library (python-imaging,'
	    print >> sys.stderr, '  *                       python-imaging-tk)'
	    sys.exit(1)

    try:
	try:	os.stat(options.dstpath)
	except: os.makedirs(options.dstpath)
    except OSError, e:
	print >> sys.stderr, 'Could not create ' + options.dstpath,
	print >> sys.stderr, '(' + e.strerror + ')'
	sys.exit(1)

    namesAndNodes = svgmanip.read_names_and_nodes(svg, name_map)
    names = svgmanip.make_state_maps(svg, namesAndNodes, options.dstpath,
				     options.prefix)
    mapdom.unlink()

    export = mnemosyne.make_questions(names, name_map,
				      options.category, options.q_img)
    edom = export.toXmlDom()
    xfp = codecs.open(os.path.join(options.dstpath, options.dstname_xml),
		      'wb', 'UTF-8')
    edom.writexml(xfp, encoding='UTF-8')
    xfp.close()

    svgmanip.svg_to_png(options.srcpath_svg,
			os.path.join(options.dstpath, options.q_img))

options.parseArguments(sys.argv[1:])
main()

