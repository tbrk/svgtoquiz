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

DESCRIPTION ="""Work through a given svg file, turning every path whose
id matches a given regular expression into a Mnemosyne entry where the
question is the id, or looked up in a separate csv file, and the answer is
the svg graphic with the given path hilighted.

The script produces a set of image files and xml ready for import into
Mnemosyne."""

import sys, re, os, subprocess
from version import __version__
from optparse import OptionParser
import locale, platform

def debug(priority, str):
    if priority <= options.debug:
	print >> sys.stderr, str

class Options:
    parser = OptionParser(usage="%prog [options] <name>",
			  version="%prog " + __version__,
			  description=DESCRIPTION)

    parser.add_option('-c', '--category', dest='category', metavar='<category>',
		      help='specify the category')
    parser.add_option('-z', '--zoom', dest='zoom', metavar='<float>',
		      default=1.0,
		      help='enlarge or reduce the produced images')

    parser.add_option('-s', '--id-regex', dest='id_regex', metavar='<regex>',
		      help='match path ids (regex with one bracketed group)')
    parser.add_option('-i', '--not-id-regex', dest='not_id_regex',
		      metavar='<regex>',
		      help='reject path ids (regex for subset of -s)')

    parser.add_option('-d', '--dst-path', dest='dstpath', metavar='<path>',
		      help='specify a location to put the results.')
    parser.add_option('-n', '--name', dest='name', metavar='<string>',
		      help='use a different name')
    parser.add_option('-r', '--randomize', dest='random_order',
		      action='store_true', default=False,
		      help='randomly shuffle the exported results')

    parser.add_option('--keep-svg', dest='keep_svg',
		      action='store_true', default=False,
		      help='keep the intermediate svg files')

    parser.add_option('--csv-path', dest='srcpath_csv', metavar='<path>',
		      help='specify a csv file explicitly')
    parser.add_option('--csv-encoding', dest='csvencoding',
		      metavar='<encoding>',
		      help='specify the encoding of the csv file explicitly')
    parser.add_option('--match-csv', dest='match_csv',
		      action='store_true', default=False,
		      help='ignore paths with ids missing from the csv file')
    parser.add_option('-e', '--gui-csv-edit', action='store_true',
		      dest='run_csvgui', default=False,
		      help='run the gui csv editor')

    parser.add_option('-m', '--show-matches', dest='show_names',
		      action='store_true', default=False,
		      help='write the matched ids to stdout')

    parser.add_option('--style', dest='style_str',
		      default='fill: #ff0000',
		      metavar='<css style>',
		      help='style to use for path highlighting.')

    parser.add_option('--color', dest='color', default=None,
		      metavar='<htmlcolor>',
		      help='shortcut for setting the fill style.')

    parser.add_option('--no-vice-versa', action='store_false',
		      dest='create_inverse', default=True,
		      help='do not produce vice-versa entries')
    parser.add_option('--only-vice-versa', action='store_false',
		      dest='create_normal', default=True,
		      help='only produce vice-versa entries')

    parser.add_option('--prefix', action='store_true',
		      dest='prefix_names', default=False,
		      help='add a prefix to image filenames')

    parser.add_option('--svgtopng', metavar='<[path/]rsvg|[path/]inkscape>',
		      dest='svgtopng_path', default=None, help=
	'specify how to convert svg files into png files (rsvg or inkscape)')

    parser.add_option('--debug', metavar='<1=least, 5=most>',
		      dest='debug', default=0,
		      help='show debugging trace at given level of detail')

    parser.add_option('--extract-docs', metavar='<path>',
		      dest='extract_docs', default=None, help=
		      'extract documentation and example files to <path>')

    parser.add_option('-g', '--groups', metavar='<levels-to-skip>',
		      dest='skip_groups', default=-1,
	      help='Treat groups shallower than the depth as transparent.')

    parser.add_option('--enter-group', dest='group_enter', metavar='<regex>',
      help='Treat groups with matching ids (after id_regex) as transparent.')

    parser.add_option('--not-enter-group', dest='group_noenter',
		      metavar='<regex>',
      help='Treat groups with matching id selections as opaque with priority.')

    parser.add_option('--no-overlay', dest='no_overlay',
		      default=False, action='store_true',
		      help='Do not use the answerbox overlay feature.')

    def setName(self, name):
	name = re.sub(r'.svg$', '', name)
	self.name        = name.decode(self.encoding)
	self.srcpath_svg = self.name + '.svg'
	self.srcpath_csv = self.name + '.csv'
	self.dstname_xml = self.name + '.xml'
	self.q_img       = self.name + '.png'
	self.category	 = self.name.replace('_', ' ')

    def setGroupRegex(self, regex=None, ignore=None):
	if regex: self.transparent_regex = re.compile(regex)
	else:     self.transparent_regex = re.compile(r'^$')

	if ignore: self.opaque_regex = re.compile(ignore)
	else:	   self.opaque_regex = re.compile(r'^$')

	return (regex or ignore)

    def setStateRegex(self, regex=None, ignore=None):
	if regex: self.state_regex = re.compile(regex)
	else:     self.state_regex = re.compile(r'.*')

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
    
    def getSvgToPngProg(self, path):
	progmatch = re.search(r'(rsvg|inkscape)[^/\\]*$', path, re.IGNORECASE)
	if progmatch == None:
	    print >> sys.stderr, ('%s: svgtopng can only be rsvg or inkscape.'
				  % self.progname)
	    sys.exit(1)
	return progmatch.group(1).lower()
    
    def setSvgToPng(self, option_path):

	if platform.system() == 'Windows':
	    inkscape_try = ['C:\Program Files\Inkscape\inkscape.exe',
			    'inkscape.exe',
			    'inkscape']
	    rsvg_try	 = ['rsvg.exe',
			    'rsvg']
	else:
	    inkscape_try = ['inkscape',
			    '/usr/bin/inkscape',
			    '/usr/local/bin/inkscape']
	    rsvg_try	 = ['rsvg',
			    '/usr/bin/rsvg',
			    '/usr/local/bin/rsvg']

	if option_path == None:
	    svgtopng_try = rsvg_try + inkscape_try
	else:
	    if option_path == 'rsvg':
		svgtopng_try = rsvg_try + inkscape_try
	    elif option_path == 'inkscape':
		svgtopng_try = inkscape_try + rsvg_try
	    else:
		svgtopng_try = [option_path]

	for exe in svgtopng_try:
	    found = True
	    try:
		exe = exe.strip()
		if exe.find(' ') > 0:
		    exe = '"' + exe + '"'

		debug(2, ' '.join(['-testing: ', exe, '--version']))
		
		proc = subprocess.Popen(' '.join([exe, '--version']),
					shell=True,
					stdout=subprocess.PIPE,
					stderr=subprocess.STDOUT)
		pipe = proc.stdout
		debug(2, '-done. now reading...')
		version = pipe.read()
		debug(1, '-' + version.strip())
		pipe.close()
		r = proc.wait()
		if r != 0: raise None
	    except: found = False
	    if found: break

	if not found:
	    print >> sys.stderr, (
		'%s: cannot find a suitable svgtopng program (inkscape or rsvg)'
		% self.progname)
	    print >> sys.stderr, (
		'%s: please specify a path manually with --svgtopng=<path>'
		% self.progname)
	    sys.exit(1)

	self.svgtopng_prog = self.getSvgToPngProg(exe)
	self.svgtopng_path = exe

    def parseArguments(self, arguments):
	(options, args) = self.parser.parse_args(arguments)

	self.debug	    = int(options.debug)
	debug(1, '-svgtoquiz ' + __version__)

	if args: self.setName(args[0])
	elif options.extract_docs != None:
	    self.setName('noname')
	else:
	    print >> sys.stderr, '%s: no name specified.' % self.progname
	    sys.exit(1)

	if options.srcpath_csv:
	    self.srcpath_csv = options.srcpath_csv.decode(self.encoding)
	if options.csvencoding:
	    self.csvencoding = options.csvencoding
	self.setStateRegex(options.id_regex, options.not_id_regex)

	if options.name:
	    prev_srcpath_svg = self.srcpath_svg
	    prev_srcpath_csv = self.srcpath_csv
	    self.setName(options.name.decode(self.encoding))
	    self.srcpath_svg = prev_srcpath_svg
	    self.srcpath_csv = prev_srcpath_csv

	if options.category:
	    self.category   = options.category.decode(self.encoding)

	if options.dstpath:
	    self.setDstPath(options.dstpath.decode(self.encoding))
	elif self.name:
	    self.setDstPath(os.path.join(u'maps', self.name))

	if options.extract_docs == None:
	    self.setSvgToPng(options.svgtopng_path)
	
	self.zoom	    = options.zoom
	self.random_order   = options.random_order
	self.show_names     = options.show_names
	self.create_normal  = options.create_normal
	self.create_inverse = (options.create_inverse or
			       not options.create_normal)
	self.keep_svg	    = options.keep_svg
	self.overlay	    = not options.no_overlay

	self.style_str	    = options.style_str
	if (options.color != None):
	    self.style_str   = 'fill: ' + options.color

	self.match_csv	    = options.match_csv
	self.run_csvgui	    = options.run_csvgui

	try: self.skip_groups    = int(options.skip_groups)
	except:
	    print >> sys.stderr, ("%s: argument of --groups must be numeric.\n"
				  % self.progname)
	    sys.exit(1)

	if self.setGroupRegex(options.group_enter, options.group_noenter):
	    self.skip_groups = max(0, self.skip_groups)

	self.extract_docs   = options.extract_docs

	if options.prefix_names: self.prefix = self.name + '_'
	else:			 self.prefix = ''

    def debugPrint(self):
	variables = [('dstpath',       self.dstpath),
		     ('exportpath',    self.exportpath),
		     ('srcpath_svg',   self.srcpath_svg),
		     ('srcpath_csv',   self.srcpath_csv),
		     ('dstname_xml',   self.dstname_xml),
		     ('q_img',	       self.q_img),
		     ('svgtopng_prog', self.svgtopng_prog),
		     ('svgtopng_path', self.svgtopng_path)]
	for v in variables: print >> sys.stderr, '- %s:\t%s' % v

    def __init__(self, progname):
	(self.lang, self.encoding) = locale.getdefaultlocale()
	self.csvencoding = self.encoding

	self.setStateRegex()
	self.setGroupRegex()
	self.progname = progname

	self.name = None
	self.debug = 0

	self.setDstPath('maps')
	self.to_png         = True
	self.zoom	    = 1.0
	self.random_order   = True,
	self.show_names     = False
	self.create_inverse = True
	self.match_csv	    = False
	self.style_str	    = 'fill: #ff0000'
	self.skip_groups    = -1
	self.overlay	    = True
	
options = Options(os.path.basename(sys.argv[0]))

