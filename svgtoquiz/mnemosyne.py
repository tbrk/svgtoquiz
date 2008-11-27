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

	#for (a, v) in self.defatts.iteritems():
	#    e.setAttribute(a, v)
	e.appendChild(makeTextNode(dom, 'cat', self.cat))
	e.appendChild(makeTextNode(dom, 'Q', self.q))
	e.appendChild(makeTextNode(dom, 'A', self.a))

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
	e.appendChild(makeTextNode(dom, 'name', cat))
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

	for cat in self.cats:
	    m.appendChild(self.__catToElement__(x, cat))
	
	if options.random_order:
	    random.shuffle(self.items)
	
	for item in self.items:
	    m.appendChild(item.toElement(x))
	
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
	qpath = os.path.join(options.exportpath, qimgfile)
	qpath = qpath.replace('\\', '/')

	if os.path.isabs(qpath) or qpath.startswith('./'):
	    print >> sys.stderr, (
		"%s: warning: the image path '%s' may be unsuitable for sharing"
		% (options.progname, qpath))

	qimg = '<img src="%s">' % qpath
    else:
	qimg = ''

    if options.overlay:
	cardstyle = '<card style="answerbox: overlay"/>'
    else:
	cardstyle = ''

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

	q = '<b>%s?</b>\n%s%s' % (fullname, qimg, cardstyle)
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

def make_multiple_choice(names, name_map=None, cat='Multiple', qimgfile=None):
    """
    Turns the entries of name_map into a set of multiple choice cards.
    Entries which do not map to an image in names are ignored.
    qimgfile is the name of an image file to include with each question.
    A category can be specified by category.
    """

    e = MnemosyneExport()

    if qimgfile:
	qpath = os.path.join(options.exportpath, qimgfile)
	qpath = qpath.replace('\\', '/')

	if os.path.isabs(qpath) or qpath.startswith('./'):
	    print >> sys.stderr, (
		"%s: warning: the image path '%s' may be unsuitable for sharing"
		% (options.progname, qpath))

	qimg = '<img src="%s">' % qpath
    else:
	qimg = ''

    if options.overlay:
	cardstyle = '<card style="answerbox: overlay"/>'
    else:
	cardstyle = ''

    for (qtext, n) in name_map.iteritems():
	if n not in names:
	    continue

	n_path = os.path.join(options.exportpath, options.prefix + n + '.png')
	n_path = n_path.replace('\\', '/')

	q = '<b>%s</b>\n%s%s' % (qtext, qimg, cardstyle)
	a = '<b>%s</b>\n<img src="%s">' % (qtext, n_path)
	e.addItem(q, a, cat, None, None)
	
    return e

