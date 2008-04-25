#!/usr/bin/env python
#
# $Id: svgtoquiz.py 104 2008-04-03 06:54:33Z tbourke $
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

import sys, re, os
import version
from optparse import OptionParser

class Options:
    parser = OptionParser(usage="%prog [options] <name>",
			  version="%prog " + version.__version__,
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
	name = re.sub(r'.svg$', '', name)
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
	else:
	    print >> sys.stderr, '%s: no name specified.' % self.progname
	    sys.exit(1)

	if options.srcpath_csv:
	    self.srcpath_csv = options.srcpath_csv.decode('utf-8')
	self.setStateRegex(options.id_regex, options.not_id_regex)
	if options.dstpath:
	    self.setDstPath(options.dstpath.decode('utf-8'))
	if options.name:
	    prev_srcpath_svg = self.srcpath_svg
	    prev_srcpath_csv = self.srcpath_csv
	    self.setName(options.name.decode('utf-8'))
	    self.srcpath_svg = prev_srcpath_svg
	    self.srcpath_csv = prev_srcpath_csv
	if options.category:
	    self.category    = options.category.decode('utf-8')

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

    def __init__(self, progname):
	self.setStateRegex()
	self.progname = progname

	self.name = None

	self.setDstPath('maps')
	self.to_png         = True
	self.zoom	    = 1.0
	self.random_order   = True,
	self.show_names     = False
	self.create_inverse = True
	self.match_csv	    = False
	self.color	    = '#ff0000'
	
options = Options(os.path.basename(sys.argv[0]))

