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

import os, os.path, random, sys
from options import options, Error
from pkg_resources import resource_filename, resource_listdir

plugins = {}

def register_export_class(name, cls):
    plugins[name.lower()] = cls

#----------------------------------------------------------------------

class ExportFile:
    """
    Parent class for export plugins. 
    """
    # set this:
    name = ""

    # Refine this: and call Export.register(name, class)
    def __init__(self, category, filepath):
	"""
	Initialize an export file with a category name.
	"""
	self.nextid = -1
	self.category = category
	self.filepath = filepath

    # Refine this:
    def addItem(self, objname, blank, highlighted, addnormal, addinverse):
	"""
	Add an item to the export file.

	objname:	The name of the quiz object being highlighted,
			for use as a question or answer.
			e.g. 'California'
	blank:		The path to the quiz image with nothing highlighted.
			e.g. a plain map of the USA.
	highlighted:	The path to the quiz image with objname highlighted.
			e.g. the USA map with a single state in red.
	addnormal:	add a normal card, i.e, show the highlighted image
		    	in the answer.
	addinverse:	add an inverse card, i.e. show the highlighted
			image in the question.
	"""
	pass

    # Refine this:
    def write(self, path):
	"""
	Create a file at path and write all items to it.
	"""
	pass

    # Optionally refine this:
    def init(cls):
	"""
	Called just after options have been parsed, but before any other
	work is done.
	"""
    init = classmethod(init)

    #------------------------------------------------------------------
    # Utility functions:

    def nextId(self):
	"""
	Return an id that is unique for the object.
	"""
	self.nextid += 1
	return str(self.nextid)

    def warning(cls, msg):
	"""
	Print a warning message.
	"""
	if isinstance(msg, list):
	    for line in msg:
		print >> sys.stderr, "%s:%s:%s" % (options.progname,
						   cls.name, line)
	else:
	    print >> sys.stderr, "%s:%s:%s" % (options.progname, cls.name, msg)
	
    warning = classmethod(warning)

#----------------------------------------------------------------------

class ExportError(Error):
    pass

class Export:
    """
    Export to file.
    """

    def __init__(self):
	plugindir = resource_filename(__name__, 'export')

	sys.path.insert(0, plugindir)
	for plugin in os.listdir(plugindir):
	    if plugin.endswith(".py"):
		try:
		    __import__(plugin[:-3])
		except:
		    print >> sys.stderr, 'Error in ' + plugin
	
	if not plugins.has_key(options.export):
	    raise ExportError('Invalid export type: ' + options.export)
	plugins[options.export].init();

    def make_questions(self, names, name_map=None, cat='Map', qimgfile=None):
	"""
	Turns the list of names into a set of questions and answers.
	The questions and answers are taken via name_map if it is given.
	qimgfile is the name of an image file to include with each question.
	A category can be specified by category.
	"""

	e = plugins[options.export](cat, os.path.join(options.dstpath,
						      options.name));

	qpath = ''
	if qimgfile:
	    qpath = os.path.join(options.exportpath, qimgfile)
	    qpath = qpath.replace('\\', '/')

	    if os.path.isabs(qpath) or qpath.startswith('./'):
		print >> sys.stderr, (
		    "%s: warning: the image path '%s' may be unsuitable for sharing"
		    % (options.progname, options.exportpath))

	items = []
	for n in names:
	    if name_map:
		if name_map.has_key(n):
		    fullname = name_map[n]
		elif name_map.has_key(n.upper()):
		    fullname = name_map[n.upper()]
		elif name_map.has_key(n.lower()):
		    fullname = name_map[n.lower()]
		else: fullname = n.replace('_', ' ')
	    else: fullname = n.replace('_', ' ')

	    n_path = os.path.join(options.exportpath, options.prefix + n + '.png')
	    n_path = n_path.replace('\\', '/')

	    e.addItem(fullname, qpath, n_path,
		      options.create_normal, options.create_inverse)

	e.write()

    def make_multiple_choice(self, names,
			     name_map=None, cat='Multiple', qimgfile=None):
	"""
	Turns the entries of name_map into a set of multiple choice cards.
	Entries which do not map to an image in names are ignored.
	qimgfile is the name of an image file to include with each question.
	A category can be specified by category.
	"""

	e = plugins[options.export](cat, os.path.join(options.dstpath,
						      options.name));

	qpath = ''
	if qimgfile:
	    qpath = os.path.join(options.exportpath, qimgfile)
	    qpath = qpath.replace('\\', '/')

	    if os.path.isabs(qpath) or qpath.startswith('./'):
		print >> sys.stderr, (
		    "%s: warning: the image path '%s' may be unsuitable for sharing"
		    % (options.progname, options.exportpath))

	if options.overlay:
	    cardstyle = '<card style="answerbox: overlay"/>'
	else:
	    cardstyle = ''

	for (qtext, n) in name_map.iteritems():
	    if n not in names:
		continue

	    n_path = os.path.join(options.exportpath, options.prefix + n + '.png')
	    n_path = n_path.replace('\\', '/')

	    e.addItem(qtext, qpath, n_path, True, False)

	e.write()

