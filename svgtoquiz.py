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
RSVG_PATH = '/usr/bin/rsvg'
RSVG_PATH = '/usr/local/bin/rsvg'
INKSCAPE_PATH = '/usr/bin/inkscape'
INKSCAPE_PATH = '/usr/local/bin/inkscape'
SVGTOPNG = 'rsvg'
# SVGTOPNG = 'inkscape'

VERSION = '1.2.1'
DESCRIPTION ="""Work through a given svg file, turning every path whose
id matches a given regular expression into a Mnemosyne entry where the
question is the id, or looked up in a separate csv file, and the answer is
the svg graphic with the given path hilighted.

The script produces a set of image files and xml ready for import into
Mnemosyne."""

#----------------------------------------------------------------------

import sys, re, os, random, codecs
import csv, cStringIO
from tempfile import mkdtemp
import xml.dom.minidom
from optparse import OptionParser
import threading

#----------------------------------------------------------------------

INKSCAPE_DPI = 90.0
IGNORE = '_ignore_'

class Options:
    parser = OptionParser(usage="%prog [options] <name>",
			  version="%prog " + VERSION,
			  description=DESCRIPTION)
    parser.add_option('-c', '--category', dest='category', metavar='CATEGORY',
		      help='specify the category')
    parser.add_option('-z', '--zoom', dest='zoom', metavar='FLOAT', default=1.0,
		      help='enlarge or reduce the produced images')
    parser.add_option('-s', '--id-regex', dest='id_regex', metavar='REGEX',
		      help='match path ids (regex with one bracketed group)')
    parser.add_option('-i', '--not-id-regex', dest='not_id_regex',
		      metavar='REGEX',
		      help='reject path ids (regex for subset of -s)')
    parser.add_option('-d', '--dst-path', dest='dstpath', metavar='PATH',
		      help='specify a location to put the results.')
    parser.add_option('-n', '--name', dest='name', metavar='STRING',
		      help='use a different name')
    parser.add_option('-r', '--randomize', dest='random_order',
		      action='store_true', default=False,
		      help='randomly shuffle the exported results')
    parser.add_option('--csv-path', dest='srcpath_csv', metavar='PATH',
		      help='specify a csv file explicitly')
    parser.add_option('--match-csv', dest='match_csv',
		      action='store_true', default=False,
		      help='ignore paths with ids missing from the csv file')
    parser.add_option('-m', '--show-matches', dest='show_names',
		      action='store_true', default=False,
		      help='write the matched ids to stdout')
    parser.add_option('--color', dest='color', default='#ff0000',
		      metavar='HTMLCOLOR',
		      help='color to use for path hilighting.')
    parser.add_option('--no-vice-versa', action='store_false',
		      dest='create_inverse', default=True,
		      help='do not produce vice-versa entries')
    parser.add_option('--only-vice-versa', action='store_false',
		      dest='create_normal', default=True,
		      help='only produce vice-versa entries')
    parser.add_option('--no-prefix', action='store_false',
		      dest='prefix_names', default=True,
		      help='do not add a prefix to filenames')
    parser.add_option('-e', '--gui-csv-edit', action='store_true',
		      dest='run_csvgui', default=False,
		      help='run the gui csv editor')

    def setName(self, name):
	re.sub(r'.svg$', '', name)
	self.name        = name
	self.srcpath_svg = name + '.svg'
	self.srcpath_csv = name + '.csv'
	self.dstname_xml = name + '.xml'
	self.q_img       = name + '.png'
	self.category	 = name.replace('_', ' ')

    def setStateRegex(self, regex=None, ignore=None):
	if regex: self.state_regex = re.compile(regex)
	else:     self.state_regex = re.compile(r'(.*)')

	if ignore: self.ignore_regex = re.compile(ignore)
	else:	   self.ignore_regex = re.compile(r'^$')

    def setDstPath(self, path):
	re.sub(r'[/\\]$', '', path)

	# Relative paths (without leading dot) go into .mnemosyne directory
	if re.match(r'^[^./]', path):
	    self.exportpath = path
	    self.dstpath = os.path.join(os.path.expanduser('~'), '.mnemosyne', path)
	else:
	    self.exportpath = path
	    self.dstpath = path

    def parseArguments(self, arguments):
	(options, args) = self.parser.parse_args(arguments)

	if args: self.setName(args[0])

	if options.srcpath_csv: self.srcpath_csv = options.srcpath_csv
	self.setStateRegex(options.id_regex, options.not_id_regex)
	if options.dstpath:     self.setDstPath(options.dstpath)
	if options.name:
	    prev_srcpath_svg = self.srcpath_svg
	    prev_srcpath_csv = self.srcpath_csv
	    self.setName(options.name)
	    self.srcpath_svg = prev_srcpath_svg
	    self.srcpath_csv = prev_srcpath_csv
	if options.category:    self.category    = options.category

	self.zoom	    = options.zoom
	self.random_order   = options.random_order
	self.show_names     = options.show_names
	self.create_normal  = options.create_normal
	self.create_inverse = (options.create_inverse or
			       not options.create_normal)
	self.color	    = options.color
	self.match_csv	    = options.match_csv
	self.run_csvgui	    = options.run_csvgui

	if options.prefix_names: self.prefix = self.name + '_'
	else:			 self.prefix = ''

    def __init__(self):
	self.setStateRegex()

	self.setName('map')

	self.setDstPath('maps')
	self.to_png         = True
	self.zoom	    = 1.0
	self.random_order   = True,
	self.show_names     = False
	self.create_inverse = True
	self.match_csv	    = False
	self.color	    = '#ff0000'
	self.prefix	    = self.name + '_'
	
options = Options()

#----------------------------------------------------------------------

def get_all_paths(svg_ele, getname_func):
    """
    Given an svg element node, calls getname_func for all path elements
    within, returning a double (name, node) for those that match.
    """
    for node in svg_ele.getElementsByTagName('path'):
	if (node.nodeType == node.ELEMENT_NODE
		and node.tagName == 'path'
		and node.attributes.has_key('id')):
	    name = getname_func(node.attributes.getNamedItem('id').value)
	    if name: yield (name, node)
    return

def get_state(name):
    """
    if name matches the state regular expression, returns the state
    abbreviation, otherwise returns an empty string.
    """
    m = options.state_regex.match(name)
    i = options.ignore_regex.match(name)
    if m and not i:
	try: return m.group(1)
	except IndexError: return ''
    return ''

fill_re = re.compile(r'fill:([^;]*)(;|$)')
def fill_style(ele, newfill = None):
    """
    Return the fill style of the given element, changing it (afterward) if
    newfill is given.
    """

    if newfill:
	newfillstr = 'fill:' + newfill + ';'
    else:
	newfillstr = ''

    styleatt = ele.attributes.getNamedItem('style')
    if styleatt == None:
	ele.setAttribute('style', newfillstr)
	return None
    else:
	fill = fill_re.match(styleatt.value)
	if fill:
	    newstyle = fill_re.sub(newfillstr, styleatt.value)
	    styleatt.value = newstyle
	    return fill.group(1)
	else:
	    styleatt.value = newfillstr + styleatt.value
	    return None

def svg_to_png(svg_path, png_path):
    """
    Convert the svg_path file into a png_path file.
    """
    if SVGTOPNG == 'inkscape':
	zoom = '%.1f' % min(max(float(INKSCAPE_DPI) * float(options.zoom),
				0.1),
			    10000)
	os.system(' '.join([INKSCAPE_PATH, '--without-gui',
					   '--export-png=' + png_path,
					   '--export-dpi=' + zoom,
					   svg_path]))
    else:
	zoom = str(options.zoom)
	os.system(' '.join([RSVG_PATH, '--x-zoom', zoom,
				       '--y-zoom', zoom,
				       svg_path, png_path]))

def make_image(svg, (name, node), dir_path, prefix=''):
    prev_fill = fill_style(node, options.color)

    svg_path = os.path.join(dir_path, prefix + name + '.svg')
    png_path = os.path.join(dir_path, prefix + name + '.png')

    fp = codecs.open(svg_path, 'w', 'utf-8')
    svg.writexml(fp)
    fp.close()

    if options.to_png:
	svg_to_png(svg_path, png_path)
	os.remove(svg_path)

    fill_style(node, prev_fill)

def read_names_and_nodes(svg, name_map=None):
    if not name_map: name_map = {}

    namesAndNodes = []
    for (name, node) in get_all_paths(svg, get_state):
	if options.match_csv and not name_map.has_key(name): continue
	namesAndNodes.append((name, node))

    return namesAndNodes

def make_state_maps(svg, namesAndNodes, dir_path, prefix=''):
    """
    Given an svg map, produce a separate svg map for each state.
    If name_map is given and options.match_csv=True, then names
    not in the map are ignored.
    """
    names = []
    for (name, node) in namesAndNodes:
	make_image(svg, (name, node), dir_path, prefix)
	names.append(name)

    return names

class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    Taken from the Python library documentation.
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")

class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    Taken from the Python library documentation.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self

def read_name_map(csv_path):
    """
    Read the first two columns of the given csv file into a map.
    """
    reader = UnicodeReader(open(csv_path, 'rb'))
    data = {}
    for row in reader:
	data[row[0]] = row[1]
    return data

class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    Taken from the Python library documentation.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

def non_ignored(name_map):
    for (key, val) in name_map.iteritems():
	if val != IGNORE: yield [key, val]
    return

def write_name_map(name_map, csv_path=None):
    """
    Write non-IGNORE elements of the name_map hash into a csv file.
    """
    if csv_path == None: csv_path = options.srcpath_csv

    writer = UnicodeWriter(open(csv_path, 'wb'))
    writer.writerows(non_ignored(name_map))

#----------------------------------------------------------------------
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

#----------------------------------------------------------------------
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
	q = '<b>%s?</b>\n%s' % (fullname,
				qimg.encode('utf-8', 'xmlcharrefreplace'))
	a = '<b>%s</b>\n<img src="%s">' % (fullname,
					   n_path.encode('utf-8',
							 'xmlcharrefreplace'))
	if options.create_inverse:
	    qinv = '<img src="%s">' % n_path
	    ainv = '<b>' + fullname + '</b>'
	else: (qinv, ainv) = (None, None)

	if options.create_normal:
	    e.addItem(q, a, cat, qinv, ainv)
	else:
	    e.addItem(qinv, ainv, cat)

    return e

#----------------------------------------------------------------------

class ConverterThread (threading.Thread):
    def __init__(self, dom, svg, namesAndNodes, dir_path, prefix=''):
	"""
	The dom, svg and, namesAndNodes data structures become owned by the
	thread. They should not be further accessed externally.
	"""
	threading.Thread.__init__(self)

	self.dom = dom
	self.svg = svg
	self.namesAndNodes = namesAndNodes
	self.numImages = len(namesAndNodes)
	self.numDone = 0
	self.current = 0
	self.pending = [True for x in range(len(self.namesAndNodes))]
	self.dir_path = dir_path
	self.prefix = prefix

	self.lock = threading.Lock()
    
    def setCurrent(self, curr):
	self.lock.acquire()
	self.current = curr
	self.lock.release()

    def requestStop(self):
	self.lock.acquire()
	for i in range(len(self.pending)):
	    self.pending[i] = False
	self.lock.release()

    def isDone(self, curr):
	self.lock.acquire()
	r = not (self.pending[curr])
	self.lock.release()
	return r

    def getNames(self):
	self.lock.acquire()
	r = [unicode(name) for (name, node) in self.namesAndNodes]
	self.lock.release()
	return r

    def numberDone(self):
	self.lock.acquire()
	r = self.numDone
	self.lock.release()
	return r

    def run(self):
	done = False
	while not done:
	    self.lock.acquire()
	    curr = self.current
	    while not self.pending[curr]:
		curr = (curr + 1) % self.numImages
	    self.lock.release()
	    done = self.task(curr)
	self.dom.unlink()

    def task(self, i):
	# print "converting: " + str(i) + "..."
	make_image(self.svg, self.namesAndNodes[i], self.dir_path, self.prefix)

	self.lock.acquire()
	self.pending[i] = False
	more = True in self.pending
	self.numDone += 1
	self.lock.release()

	return (not more)

#----------------------------------------------------------------------

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
	try: name_map = read_name_map(options.srcpath_csv)
	except:
	    print >> sys.stderr, 'Unable to read ' + options.srcpath_csv
	    name_map = None
    else:
	name_map = None

    if options.run_csvgui:
	if GUI:
	    namesAndNodes = read_names_and_nodes(svg, name_map)
	    tmpdir = mkdtemp()
	    converter = ConverterThread(mapdom, svg, namesAndNodes, tmpdir, '')
	    guicsv_main(name_map, converter, tmpdir, write_name_map)
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

    namesAndNodes = read_names_and_nodes(svg, name_map)
    names = make_state_maps(svg, namesAndNodes, options.dstpath, options.prefix)
    mapdom.unlink()

    export = make_questions(names, name_map, options.category, options.q_img)
    edom = export.toXmlDom()
    xfp = codecs.open(os.path.join(options.dstpath, options.dstname_xml),
		      'wb', 'utf-8')
    edom.writexml(xfp, encoding='utf-8')
    xfp.close()

    svg_to_png(options.srcpath_svg,
	       os.path.join(options.dstpath, options.q_img))


#sys.path.append(os.path.dirname(sys.argv[0]))
try:
    from svgtoquiz_gui import *
    GUI=True
except: GUI=False

options.parseArguments(sys.argv[1:])
main()

