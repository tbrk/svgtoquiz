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

import xml.dom.minidom, os, os.path, codecs
from svgtoquiz import register_export_class, ExportFile, options
import random

class QuizifyFile(ExportFile):
    """
    Export plugin for Quizify (http://quizify.com/).
    """
    name = "quizify"

    def __init__(self, category, filepath):
	"""
	Initialize an export file with a category name.
	"""
	ExportFile.__init__(self, category, filepath + '.html')
	self.items = []

	self.dom = xml.dom.minidom.Document()
	m = self.dom.createElement('dl')
	self.dom.appendChild(m)
	self.list = m

    def makeTextNode(self, tagName, text):
	"""
	Given an xml dom object, create a tagName element containing text.
	"""
	c = self.dom.createElement(tagName)
	c.appendChild(self.dom.createTextNode(text))
	return c

    def addXMLItem(self, q, a, qimg = None, aimg = None):
	"""
	Given an xml dom object, return an xml element representing the
	item.
	"""
	qitem = self.makeTextNode('dt', q)
	if qimg != None:
	    img = self.dom.createElement('img')
	    img.setAttribute('src', qimg)
	    img = qitem.appendChild(img)

	aitem = self.makeTextNode('dd', a)
	if aimg != None:
	    img = self.dom.createElement('img')
	    img.setAttribute('src', aimg)
	    img = aitem.appendChild(img)

	self.list.appendChild(qitem)
	self.list.appendChild(aitem)

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

	blank = os.path.basename(blank)
	highlighted = os.path.basename(highlighted)

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

    init = classmethod(init)

register_export_class(QuizifyFile)

