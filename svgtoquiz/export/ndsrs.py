#!/usr/bin/env python
#
# $Id: mnemosyne.py 183 2008-11-27 10:49:09Z tbourke $
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

import xml.dom.minidom, os, os.path, codecs
from svgtoquiz import register_export_class, ExportFile, options
import random

class NdsrsFile(ExportFile):
    """
    Export plugin for NDSRS.
    """
    name = "ndsrs"

    def makeTextNode(self, tagName, text):
	"""
	Given an xml dom object, create a tagName element containing text.
	"""
	c = self.dom.createElement(tagName)
	c.appendChild(self.dom.createTextNode(text))
	return c

    def __init__(self, category, filepath):
	"""
	Initialize an export file with a category name.
	"""
	ExportFile.__init__(self, category, filepath + '.srs')
	self.items = []

	self.dom = xml.dom.minidom.Document()
	m = self.dom.createElement('deck')
	self.dom.appendChild(m)
	self.deck = m

    def addXMLItem(self, q, a, qimg = None, aimg = None):
	"""
	Given an xml dom object, return an xml element representing the
	item.
	"""
	e = self.dom.createElement('card')

	qitem = self.makeTextNode('question', q)
	qitem.setAttribute('size', str(self.fontsize))
	if qimg != None: qitem.setAttribute('image', qimg)

	aitem = self.makeTextNode('answer', a)
	aitem.setAttribute('size', str(self.fontsize))
	if aimg != None: aitem.setAttribute('image', aimg)

	e.appendChild(qitem)
	e.appendChild(aitem)

	self.deck.appendChild(e)

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

	blank = 'data/img/' + os.path.basename(blank)
	highlighted = 'data/img/' + os.path.basename(highlighted)

	if addnormal:
	    self.items.append((objname + '?', objname, blank, highlighted))

	if addinverse:
	    self.items.append(('', objname, highlighted, None))

    def write(self):
	"""
	Create a file at path and write all items to it.
	"""

	if options.random_order:
	    random.shuffle(self.items)

	for (q, a, qimg, aimg) in self.items:
	    self.addXMLItem(q, a, qimg, aimg)

	xfp = codecs.open(self.filepath, 'wb', 'UTF-8')
	self.dom.writexml(xfp, encoding='UTF-8')
	xfp.close()

    def init(cls, args = []):
	"""
	Called just after options have been parsed, but before any other
	work is done.
	"""
	cls.setExportDefaultPath(os.getcwd(), '')

	just_width = False
	just_height = False
	cls.fontsize = 12

	for (n, v) in args:
	    if n == "justwidth":
		just_width = True

	    elif n == "justheight":
		just_height = True

	    elif n == "fontsize" and v.isdigit():
		cls.fontsize = int(v)

	    else:
		cls.warning('invalid option: %s %s' % (n, v))
	
	if options.zoom != 1.0:
	    cls.warning("ignoring zoom option.")
	
	if options.zoom == 1.0:
	    if not just_height and options.width == None:  options.width = 256
	    if not just_width  and options.height == None: options.height = 180

    init = classmethod(init)

register_export_class(NdsrsFile)

