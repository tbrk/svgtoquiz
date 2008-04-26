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

import sys, os, codecs
import xml.dom.minidom
import cvsgui, mnemosyne, options, svgmanip
import locale

def main():
    locale.setlocale(locale.LC_ALL, '')
    options.parseArguments(sys.argv[1:])

    try: mapdom = xml.dom.minidom.parse(options.srcpath_svg)
    except IOError, e:
	print >> sys.stderr, 'Could not open ' + options.srcpath_svg,
	print >> sys.stderr, '(' + e.strerror + ')'
	return 1

    svgs = mapdom.getElementsByTagName('svg')
    if svgs.length == 0:
	print >> sys.stderr, 'The document does not contain an svg element.'
	return 1
    svg = svgs[0]

    if options.srcpath_csv:
	try: name_map = svgmanip.read_name_map(options.srcpath_csv)
	except svgmanip.BadCSVEncoding:
	    print >> sys.stderr, 'Bad encoding: ' + options.srcpath_csv,
	    print >> sys.stderr, '(expected ' + options.csvencoding + ')'
	    return 1
	except:
	    if not hasGUI:
		print >> sys.stderr, 'Unable to read ' + options.srcpath_csv
	    name_map = None
    else:
	name_map = None

    if options.run_csvgui:
	if hasGUI:
	    try: cvsgui.start(mapdom, svg, name_map)
	    except cvsgui.NoNamesError: return 1
	    return 0
	else:
	    print >> sys.stderr, 'Sorry, the GUI feature is not available.'
	    print >> sys.stderr, 'One of the requirements is not satisfied:'
	    print >> sys.stderr, '  * svgtoquiz_gui.py in same directory'
	    print >> sys.stderr, '  * Tkinter and tkMessageBox (python-tk)'
	    print >> sys.stderr, '  * Python Image Library (python-imaging,'
	    print >> sys.stderr, '  *                       python-imaging-tk)'
	    return 1

    try:
	try:	os.stat(options.dstpath)
	except: os.makedirs(options.dstpath)
    except OSError, e:
	print >> sys.stderr, 'Could not create ' + options.dstpath,
	print >> sys.stderr, '(' + e.strerror + ')'
	return 1

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
    
    return 0

