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

import xml.dom.minidom, os.path, codecs
from svgtoquiz import register_export_class, ExportFile, options

# TODO: respect options.random_order

class MnemosyneFile(ExportFile):
    """
    Export plugin for Mnemosyne.
    """

    def makeTextNode(self, tagName, text):
	"""
	Given an xml dom object, create a tagName element containing text.
	"""
	c = self.dom.createElement(tagName)
	c.appendChild(self.dom.createTextNode(text))
	return c

    def __init__(self, category):
	"""
	Initialize an export file with a category name.
	"""
	ExportFile.__init__(self, category)

	self.dom = xml.dom.minidom.Document()
	m = self.dom.createElement('mnemosyne')

	m.setAttribute('core_version', '1')
	self.dom.appendChild(m)
	self.mnemosyne = m

	c = self.dom.createElement('category')
	c.setAttribute('active', '1')
	c.appendChild(self.makeTextNode('name', category))
	m.appendChild(c)

    def addXMLItem(self, id, q, a):
	"""
	Given an xml dom object, return an xml element representing the
	item.
	"""
	e = self.dom.createElement('item')
	e.setAttribute('id', id)
	e.setIdAttribute('id')

	e.appendChild(self.makeTextNode('cat', self.category))
	e.appendChild(self.makeTextNode('Q', q))
	e.appendChild(self.makeTextNode('A', a))

	self.mnemosyne.appendChild(e)

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

	qimg = ''
	if blank != None: qimg = '<img src="%s">' % blank

	if options.overlay:
	    cardstyle = '<card style="answerbox: overlay"/>'
	else:
	    cardstyle = ''

	id = self.nextId()
	idinv = id + '.inv'

	if addnormal:
	    q = '<b>%s?</b>\n%s%s' % (objname, qimg, cardstyle)
	    a = '<b>%s</b>\n<img src="%s">' % (objname, highlighted)
	    self.addXMLItem(id, q, a)

	if addinverse:
	    qinv = '<img src="%s">' % highlighted
	    ainv = '<b>' + objname + '</b>'
	    self.addXMLItem(idinv, qinv, ainv)

    def write(self):
	"""
	Create a file at path and write all items to it.
	"""
	filepath = os.path.join(options.dstpath, options.dstname_xml)
	xfp = codecs.open(filepath, 'wb', 'UTF-8')
	self.dom.writexml(xfp, encoding='UTF-8')
	xfp.close()

register_export_class('mnemosyne', MnemosyneFile)

