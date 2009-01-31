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

import sys, os, os.path, stat
import xml.dom.minidom
import cvsgui, svgmanip
from svgmanip import SvgError
from options import options, OptionError
from export import Export, ExportError

import shutil
from pkg_resources import resource_filename, resource_listdir

import locale

def debug(priority, str):
    if priority <= options.debug:
	print >> sys.stderr, str

try:
    import cvsgui
    hasGUI=True
except ImportError:
    hasGUI=False

def run_svgtoquiz():
    export = Export()

    if options.extract_docs != None:
	dstdir = options.extract_docs
	try: os.mkdir(dstdir)
	except OSError, reason: pass

	exampledir = resource_filename(__name__, 'examples')
	docdir = resource_filename(__name__, 'doc')

	for f in (map (lambda x: os.path.join (exampledir, x), 
		       resource_listdir(__name__, 'examples')) +
		  map (lambda x: os.path.join (docdir, x), 
		       resource_listdir(__name__, 'doc'))):
	    if os.path.isdir(f): continue
	    shutil.copy(f, dstdir)
	    os.chmod(os.path.join(dstdir, os.path.basename(f)),
		     stat.S_IREAD | stat.S_IWRITE |
		     stat.S_IRGRP | stat.S_IWGRP |
		     stat.S_IROTH)

	return 0

    if options.debug >= 1: options.debugPrint()

    debug(1, '-destination directory: ' + options.dstpath)
    debug(1, '-parsing: ' + options.srcpath_svg)
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

    debug(1, '-processing csv: ' + options.srcpath_csv)
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
	debug(1, '-running gui')
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

    debug(1, '-checking: ' + options.dstpath)
    try:
	try:	os.stat(options.dstpath)
	except: os.makedirs(options.dstpath)
    except OSError, e:
	print >> sys.stderr, 'Could not create ' + options.dstpath,
	print >> sys.stderr, '(' + e.strerror + ')'
	return 1

    debug(1, '-generating question image (dir=%s name=%s)' %
		(options.dstpath, options.name))
    svgmanip.convert_svg(svg, options.dstpath, options.name)
    
    debug(1, '-generating images')
    (namesAndNodes, name_map) = svgmanip.read_names_and_nodes(svg, name_map)
    names = svgmanip.make_state_maps(svg, namesAndNodes, options.dstpath,
				     options.prefix)
    mapdom.unlink()

    debug(1, '-making questions')
    try:
	if options.multiple_choice:
	    if name_map == None:
		print >> sys.stderr, 'Option --multiple-choice requires a csv file.'
		return 1
	    export.make_multiple_choice(names, name_map,
					options.category, options.q_img)
	else:
	    export.make_questions(names, name_map,
				  options.category, options.q_img)

    except ExportError, e:
	print >> sys.stderr, e.msg
	return 1

    debug(1, '-done')
    return 0

def main():
    locale.setlocale(locale.LC_ALL, '')

    try:
	options.parseArguments(sys.argv[1:])
	r = run_svgtoquiz ()
    except OptionError, e: e.show(); r = 1
    except SvgError, e: e.show(); r = 2 
    except ExportError, e: e.show(); r = 3

    sys.exit(r)

def svgtoquiz(arglist):
    options.parseArguments(arglist)
    return run_svgtoquiz ()

