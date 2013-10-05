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

# NB: rsvg does not seem to work propertly with utf-8 filenames, it gives an
#     error message: Invalid byte sequence in conversion input.
#     Inkscape does work.

#----------------------------------------------------------------------

import sys, re, os, codecs, subprocess
import platform
import csv, cStringIO
from options import options, Error

#----------------------------------------------------------------------

INKSCAPE_DPI = 90.0
IGNORE = '_ignore_'

#----------------------------------------------------------------------

class SvgError(Error):
    pass

def debug(priority, str):
    if priority <= options.debug:
	print >> sys.stderr, str

class BadCSVEncoding:
    def __init__(self):
	pass

#----------------------------------------------------------------------

def styleToDict(styleStr):
    atts = styleStr.split(';')
    d = {}
    for att in atts:
	(name, sep, value) = att.partition(':')
	if sep != '':
	    d[name.strip()] = value.strip()

    return d

def dictToStyle(styleDict):
    return '; '.join([name + ': ' + value
		      for (name, value) in styleDict.iteritems()])

#----------------------------------------------------------------------

svgobj_regex = re.compile(r'(path|rect|circle|ellipse|polygon)')

def allsvgobj_iter(node):
    for t in ['path', 'rect', 'circle', 'ellipse', 'polygon']:
	for e in node.getElementsByTagName(t):
	    yield e
    return

def get_state(name):
    """
    if name matches the state regular expression, returns the state
    abbreviation, otherwise returns an empty string.
    """
    m = options.state_regex.search(name)
    i = options.ignore_regex.search(name)
    if m and not i:
	try:
	    subname = m.group(1)
	    if options.show_names: print subname
	    return (subname, True)
	except IndexError:
	    if options.show_names: print name
	    return (name, False)
    return ('', False)

def set_style(ele, newStyleStr = ''):
    styleatt = ele.attributes.getNamedItem('style')
    ele.setAttribute('style', newStyleStr)

def fill_style(ele, newStyle = {}):
    """
    Return the fill style of the given element, changing it (afterward) if
    newfill is given.
    """

    styleAtt = ele.attributes.getNamedItem('style')
    if styleAtt == None:
	ele.setAttribute('style', dictToStyle(newStyle))
	return ''
    else:
	oldStyle = styleAtt.value
	debug(6, '-prestyle :' + oldStyle)

	currStyle = styleToDict(oldStyle)
	for (name, value) in newStyle.iteritems():
	    currStyle[name] = value

	currStyleStr = dictToStyle(currStyle)
	styleAtt.value = currStyleStr
	debug(6, '-poststyle:' + currStyleStr)

	return oldStyle

re_needsquotes = re.compile(r"[ ()']")
def svg_to_png(svg_path, png_path):
    """
    Convert the svg_path file into a png_path file.
    """

    if re_needsquotes.search(svg_path): svg_path = '"' + svg_path + '"'
    if re_needsquotes.search(png_path): png_path = '"' + png_path + '"'
    svg_path.replace('"', '\\"')
    png_path.replace('"', '\\"')

    if options.svgtopng_prog == 'inkscape':
	if (options.width == None and options.height == None):
	    zoom = '%.1f' % min(max(float(INKSCAPE_DPI) * float(options.zoom),
				    0.1), 10000)
	    size = ['--export-dpi=' + zoom]
	else:
	    size = []
	    if (options.width != None):
		size.append('-w' + str(options.width))
	    if (options.height != None):
		size.append('-h' + str(options.height))

	cmd = u' '.join([options.svgtopng_path,
			 '--without-gui',
			 '--export-png=' + png_path] + size + [svg_path])
    else:
	if (options.width == None and options.height == None):
	    zoom = str(options.zoom)
	    size = ['--x-zoom', zoom, '--y-zoom', zoom]
	else:
	    size = []
	    if (options.width != None):
		size.append('-w ' + str(options.width))
	    if (options.height != None):
		size.append('-h ' + str(options.height))

	cmd = u' '.join([options.svgtopng_path] + size + [svg_path, png_path])
    cmd = cmd.encode(options.encoding)
    debug(2, '-svgtopng: ' + cmd)
    data = ""
    try:
	if platform.system() == 'Windows': cmd = '"' + cmd + '"'
	proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
	pipe = proc.stdout
	data = pipe.read()
	pipe.close()
	r = proc.wait()
    except OSError, reason:
	print >> sys.stderr, reason
	r = -1
    if r != 0:
	raise SvgError("svg to png conversion failed (" + str(r) + ").")
    debug(2, '-output:\n' + data)

def convert_svg(svg, dir_path, name):
    """
    Turn an svg map into a graphic file.
    """

    svg_path = os.path.join(dir_path, name + '.svg')
    png_path = os.path.join(dir_path, name + '.png')

    try:
	fp = codecs.open(svg_path, 'w', 'UTF-8')
	svg.writexml(fp)
	fp.close()
    except IOError, reason:
	raise SvgError(u'cannot create %s (%s)' % (svg_path, reason))

    if options.to_png:
	svg_to_png(svg_path, png_path)
	if not options.keep_svg: os.remove(svg_path)

def make_image(svg, (name, node), dir_path, prefix, style):
    if node.tagName == 'g':
	prev_branch = node.cloneNode(deep=True)
	for e in allsvgobj_iter(node):
	    fill_style(e, style)
	for e in node.getElementsByTagName('g'):
	    fill_style(e, style)

    prev_style = fill_style(node, style)

    convert_svg(svg, dir_path, prefix + name)

    if node.tagName == 'g':
	parent = node.parentNode
	parent.replaceChild(prev_branch, node)
    else:
	set_style(node, prev_style)

def get_all_paths(svg_ele, getname_func):
    """
    Given an svg element node, calls getname_func for all path elements
    within, returning a double (name, node) for those that match.
    """
    for node in allsvgobj_iter(svg_ele):
	if node.nodeType == node.ELEMENT_NODE:
	    if node.attributes.has_key('id'):
		id = node.attributes.getNamedItem('id').value
		debug(5, '-element: ' + node.tagName + ', id=' + id)
		if svgobj_regex.match(node.tagName):
		    (name, matched) = getname_func(id)
		    if name: yield (name, node, matched)
	    else:
		debug(5, '-element: ' + node.tagName)
    return

def get_group_paths(node, depth, getname_func):
    for n in node.childNodes:
	if n.nodeType == node.ELEMENT_NODE:
	    if n.attributes.has_key('id'):
		id = n.attributes.getNamedItem('id').value
		debug(5, '-element: ' + n.tagName + ', id=' + id)
		(name, matched) = getname_func(id)
	    else:
		debug(5, '-element: ' + n.tagName)
		(name, matched) = ('', False)

	    if ((n.tagName == 'g') and
		    (depth > 0 or options.transparent_regex.search(name))
		    and not options.opaque_regex.match(name)):
		debug(2, '-' + ('>' * depth) + 'group: "' + name + '"')
		for gn in get_group_paths(n, depth - 1, getname_func):
		    yield gn
	    elif ((svgobj_regex.match(n.tagName) or n.tagName == 'g')
		    and (name != '')):
		yield (name, n, matched)

def read_names_and_nodes(svg, name_map=None):
    if not name_map:
	name_map = {}

    if options.skip_groups >= 0:
	f = lambda s, f: get_group_paths(s, options.skip_groups, f)
    else:
	f = get_all_paths

    namesAndNodes = []
    for (name, node, matched) in f(svg, get_state):
	if not name_map.has_key(name):
	    if options.match_csv: continue
	    if not matched and node.attributes.has_key('inkscape:label'):
		name_map[name] = (
		    node.attributes.getNamedItem('inkscape:label').value)
	namesAndNodes.append((name, node))

    return (namesAndNodes, name_map)

def make_state_maps(svg, namesAndNodes, dir_path, prefix=''):
    """
    Given an svg map, produce a separate svg map for each state.
    If name_map is given and options.match_csv=True, then names
    not in the map are ignored.
    """
    names = []
    style = styleToDict(options.style_str)
    for (name, node) in namesAndNodes:
	make_image(svg, (name, node), dir_path, prefix, style)
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

