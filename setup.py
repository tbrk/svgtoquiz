#!/usr/bin/env python
#
# $Id$
#
import ez_setup
ez_setup.use_setuptools()
from setuptools import setup

setup(name		= 'svgtoquiz',
      version		= '1.4.0',
      packages		= ['svgtoquiz'],

      # for gui:
      extras_require = { 'gui' : ['Tkinter>=2.5', 'PIL>=1.1.6'] },

      include_package_data = True,
      entry_points = {
	    'console_scripts'	      : [ 'svgtoquiz = svgtoquiz:main' ],
	    'setuptools.installation' : [ 'svgtoquiz = svgtoquiz:main' ]},

      # metadata
      author	= 'Timothy Bourke',
      author_email = 'timbob@bigpond.com',
      description  = 'Generate graphical flashcards from svg images.',
      keywords  = "svg mnemosyne maps",
      license	= 'BSD',
      url	= 'http://www.cse.unsw.edu.au/~tbourke/software/svgtoquiz.html',

      long_description = """\
Work through an svg file turning every path whose id matches a given
regular expression into a Mnemosyne entry where the question is the id, or
looked up in a separate csv file, and the answer is the svg graphic with
the given path hilighted.

The script produces a set of image files and xml ready for import into
Mnemosyne."""
     )

