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

# NB: rsvg does not seem to work propertly with utf-8 filenames, it gives an
#     error message: Invalid byte sequence in conversion input.
#     Inkscape does work.

#----------------------------------------------------------------------

import sys, re, os, codecs
import csv, cStringIO
from options import options

#----------------------------------------------------------------------

INKSCAPE_DPI = 90.0
IGNORE = '_ignore_'

#----------------------------------------------------------------------

def debug(str):
    if options.debug:
	print >> sys.stderr, str

class BadCSVEncoding:
    def __init__(self):
	pass

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
    debug('-svgtopng: ' + options.svgtopng_prog
	  + ' (' + options.svgtopng_path + ')')
    if options.svgtopng_prog == 'inkscape':
	zoom = '%.1f' % min(max(float(INKSCAPE_DPI) * float(options.zoom), 0.1),
			    10000)
	command = u' '.join([options.svgtopng_path,
					    '--without-gui',
					    '--export-png=' + png_path,
					    '--export-dpi=' + zoom,
					    svg_path])
    else:
	zoom = str(options.zoom)
	command = u' '.join([options.svgtopng_path,
					'--x-zoom', zoom,
				        '--y-zoom', zoom,
				        svg_path, png_path])
    os.system(command.encode(options.encoding))

def make_image(svg, (name, node), dir_path, prefix=''):
    prev_fill = fill_style(node, options.color)

    svg_path = os.path.join(dir_path, prefix + name + '.svg')
    png_path = os.path.join(dir_path, prefix + name + '.png')

    try:
	fp = codecs.open(svg_path, 'w', 'UTF-8')
	svg.writexml(fp)
	fp.close()
    except IOError, reason:
	print >> sys.stderr, (u'%s: cannot create %s (%s)' %
			      (options.progname, svg_path, reason))
	sys.exit(1)

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
        #return self.reader.next().encode("UTF-8")
        r = self.reader.next()
	s = r.encode("UTF-8")
	return s

class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    Modified from the Python library documentation.
    """

    def __init__(self, f, dialect=csv.excel, encoding="UTF-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        try: row = self.reader.next()
	except UnicodeDecodeError:
	    raise BadCSVEncoding()
        return [unicode(s, "UTF-8") for s in row]

    def __iter__(self):
        return self

def read_name_map(csv_path):
    """
    Read the first two columns of the given csv file into a map.
    """
    reader = UnicodeReader(open(csv_path, 'rb'), encoding=options.csvencoding)
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

    def __init__(self, f, dialect=csv.excel, encoding="UTF-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("UTF-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("UTF-8")
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

    writer = UnicodeWriter(open(csv_path, 'wb'), encoding=options.csvencoding)
    writer.writerows(non_ignored(name_map))

