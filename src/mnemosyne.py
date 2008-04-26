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

import os, random
import xml.dom.minidom
from options import options

def makeTextNode(dom, tagName, text):
    """
    Given an xml dom object, create a tagName element containing text.
    """
    c = dom.createElement(tagName)
    c.appendChild(dom.createTextNode(text))
    return c

class MnemosyneItem:
    """
    An item suitable for including in a Mnemosyne export file.
    """
    defatts = { 'gr'      : '0',
		'e'       : '2.594',
		'ac_rp'   : '1',
		'rt_rp'   : '0',
		'lps'     : '0',
		'ac_rp_l' : '1',
		'rt_rp_l' : '0',
		'l_rp'    : '36',
		'n_rp'    : '36'     }

    def __init__(self, id, q, a, cat):
	"""
	Given strings for an id, question, answer and category, create an
	item object.
	"""
	self.id = id
	self.q = q
	self.a = a
	self.cat = cat

    def toElement(self, dom):
	"""
	Given an xml dom object, return an xml element representing the
	item.
	"""
	e = dom.createElement('item')
	e.setAttribute('id', self.id)
	e.setIdAttribute('id')

	for (a, v) in self.defatts.iteritems():
	    e.setAttribute(a, v)
	e.appendChild(dom.createTextNode('\n'))
	e.appendChild(makeTextNode(dom, 'cat', self.cat))
	e.appendChild(dom.createTextNode('\n'))
	e.appendChild(makeTextNode(dom, 'Q', self.q))
	e.appendChild(dom.createTextNode('\n'))
	e.appendChild(makeTextNode(dom, 'A', self.a))
	e.appendChild(dom.createTextNode('\n'))

	return e

class MnemosyneExport:
    """
    An xml file in Mnemosyne export format.
    """
    def __init__(self):
	self.nextid = -1
	self.cats = {}
	self.items = []

    def nextId(self):
	"""
	Return an id that is unique for the object.
	"""
	self.nextid += 1
	return str(self.nextid)

    def __catToElement__(self, dom, cat):
	e = dom.createElement('category')
	e.setAttribute('active', '1')
	e.appendChild(dom.createTextNode('\n'))
	e.appendChild(makeTextNode(dom, 'name', cat))
	e.appendChild(dom.createTextNode('\n'))
	return e

    def addItem(self, q, a, cat, invq=None, inva=None, addinv=False):
	"""
	Add an item to the export file.

	Question, answer, and category strings must be supplied.

	An inverse item is also added if invq and inva are given, or if
	addinv is true.
	"""
	id = self.nextId()
	self.cats[cat] = True
	self.items.append(MnemosyneItem(id, q, a, cat))

	if (invq != None and inva != None):
	    self.items.append(MnemosyneItem(id + '.inv', invq, inva, cat))
	elif addinv:
	    self.items.append(MnemosyneItem(id + '.inv', a, q, cat))


    def toXmlDom(self):
	"""
	Returns an xml dom for the export file.
	"""
	x = xml.dom.minidom.Document()
	m = x.createElement('mnemosyne')
	m.setAttribute('core_version', '1')
	x.appendChild(m)
	m.appendChild(x.createTextNode('\n'))

	for cat in self.cats:
	    m.appendChild(self.__catToElement__(x, cat))
	    m.appendChild(x.createTextNode('\n'))
	
	if options.random_order:
	    random.shuffle(self.items)
	
	for item in self.items:
	    m.appendChild(item.toElement(x))
	    m.appendChild(x.createTextNode('\n'))
	
	return x

def make_questions(names, name_map=None, cat='Map', qimgfile=None):
    """
    Turns the list of names into a set of questions and answers.
    The questions and answers are taken via name_map if it is given.
    qimgfile is the name of an image file to include with each question.
    A category can be specified by category.
    """
    e = MnemosyneExport()

    if qimgfile:
	qpath = os.path.join(options.dstpath, qimgfile)
	qimg = '<img src="%s">' % qpath
    else:
	qimg = ''

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
	q = '<b>%s?</b>\n%s' % (fullname, qimg)
	a = '<b>%s</b>\n<img src="%s">' % (fullname, n_path)
	if options.create_inverse:
	    qinv = '<img src="%s">' % n_path
	    ainv = '<b>' + fullname + '</b>'
	else: (qinv, ainv) = (None, None)

	if options.create_normal:
	    e.addItem(q, a, cat, qinv, ainv)
	else:
	    e.addItem(qinv, ainv, cat)

    return e

