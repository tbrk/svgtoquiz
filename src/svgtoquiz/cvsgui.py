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
# 20080402 T. Bourke
#   Original code to present a basic GUI for creating csv files that map svg
#   ids to text strings.
#   This module is imported from svgtoquiz.py
#
# REQUIRES:
#   * Developed in python 2.5
#   * Tkinter, and tkMessageBox (python-tk)
#   * Python Image Library (python-imaging,
#			    python-imaging-tk)
#
#----------------------------------------------------------------------

import sys, os, time
import threading
from options import options
from svgmanip import make_image, write_name_map

# for the gui csv editor
from Tkinter import *
import tkMessageBox
from PIL import Image, ImageTk

IGNORE = '_ignore_' # must match decl in svgtoquiz.py

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

class Application(Frame):
    def showImage(self):
	if self.converter.isDone(self.current):
	    path = os.path.join(self.tmpdir, self.names[self.current] + '.png')
	    img = Image.open(path)
	    self.lastImageSize = img.size
	    self.image = ImageTk.PhotoImage(img)
	    self.labImage['image'] = self.image
	else:
	    if self.blankImage == None:
		self.blankImage = ImageTk.PhotoImage(Image.new('RGB',
							       self.lastImageSize,
							       'white'))
	    self.labImage['image'] = self.blankImage
	    self.converter.setCurrent(self.current)
	    self.after(500, self.showImage)
    
    def showStatus(self):
	numdone = self.converter.numberDone()
	self.labStatus['text'] = '%d / %d [%d done]' % (self.current+1,
						        self.numnames,
						        numdone)
	if numdone < self.numnames:
	    self.after(100, self.showStatus)
    
    def showCurrentName(self):
	if self.name_map.has_key(self.names[self.current]):
	    self.dataName.set(self.name_map[self.names[self.current]])
	else:
	    self.dataName.set(self.names[self.current])
    
    def updateWindow(self):
	self.showImage()
	self.showCurrentName()
	self.showStatus()
    
    def setCurrentName(self, value=None):
	if value == None:
	    value = unicode(self.dataName.get())

	if (not self.name_map.has_key(self.names[self.current])
	    or self.name_map[self.names[self.current]] != value):
	    self.name_map[self.names[self.current]] = value
	    self.dirty = True
    
    def skip(self, i):
	return (self.dataHideIgnored.get()
		and self.name_map.has_key(self.names[i])
		and self.name_map[self.names[i]] == IGNORE)

    def gotoNext(self):
	curr = self.current + 1
	while (curr < self.numnames and self.skip(curr)):
	    curr += 1

	if (curr < self.numnames):
	    self.setCurrentName()
	    self.current = curr
	    self.updateWindow()

    def gotoPrev(self):
	curr = self.current - 1
	while (curr > 0 and self.skip(curr)):
	    curr -= 1

	if (curr >= 0 and not self.skip(curr)):
	    self.setCurrentName()
	    self.current = curr
	    self.updateWindow()

    def ignore(self):
	self.dataName.set(IGNORE)
	self.gotoNext()

    def saveData(self):
	self.setCurrentName()
	if self.dirty and tkMessageBox.askokcancel(message='Really save?'):
	    write_name_map(self.name_map)
	    self.dirty = False
    
    def cleanTmpDir(self):
	for f in os.listdir(self.tmpdir):
	    os.unlink(os.path.join(self.tmpdir, f))
	os.rmdir(self.tmpdir)

    def quitApp(self):
	self.setCurrentName()
	if (not self.dirty) or tkMessageBox.askokcancel(
		message='The data have not been saved. Really quit?'):
	    self.converter.requestStop()
	    self.converter.join(5)
	    try: self.cleanTmpDir()
	    except:
		print >> sys.stderr, 'could not remove ' + self.tmpdir + '...'
	    self.quit()

    def createWidgets(self):
	self.frameGraphics = Frame(self)
	self.frameData     = Frame(self)
	self.frameButtons  = Frame(self)
	self.frameGraphics.pack(side='top',    fill='both', expand='yes')
	self.frameButtons.pack (side='bottom', fill='x',    expand='no')
	self.frameData.pack    (side='bottom', fill='x',    expand='no')

	self.labImage = Label(self.frameGraphics)
	self.labImage.pack(fill='both', expand='yes')

	self.dataHideIgnored = IntVar()
	self.chkHideIgnored = Checkbutton(self.frameButtons,
					  text="skip ignored",
					  variable=self.dataHideIgnored)
	self.chkHideIgnored.pack(side='left')
	self.dataHideIgnored.set(1)

        self.butQuit = Button(self.frameButtons, text='quit',
			      command=self.quitApp)
        self.butQuit.pack(side='right')

        self.butSave = Button(self.frameButtons, text='save',
			      command=self.saveData)
        self.butSave.pack(side='right')

	self.labStatus = Label(self.frameButtons, text='status')
	self.labStatus.pack(side='right', fill='x', expand='yes')

        self.butPrev = Button(self.frameData, text='prev',
			      command=self.gotoPrev)
        self.butPrev.pack(side='left')

        self.butIgnore = Button(self.frameData, text='ignore',
				command=self.ignore)
        self.butIgnore.pack(side='right')

        self.butNext = Button(self.frameData, text='next',
			      command=self.gotoNext)
        self.butNext.pack(side='right')

	self.dataName = StringVar()
	self.dataName.set('')

	self.entryName = Entry(self.frameData, textvariable=self.dataName)
	self.entryName.pack(side='left', fill='x', expand='yes')

    def __init__(self, svg, mapdom, name_map={}, master=None):
	self.tmpdir = mkdtemp()

	if name_map:
	    self.name_map = name_map
	else:
	    self.name_map = {}

	namesAndNodes = read_names_and_nodes(svg, name_map)
	self.converter = ConverterThread(mapdom, svg, namesAndNodes, tmpdir, '')

	self.names = self.converter.getNames()
	self.numnames = len(self.names)
	if self.numnames == 0:
	    print >> sys.stderr, 'No paths in file.'
	    sys.exit(1)
	self.current = 0

	self.converter.start()
	while not (self.converter.isDone(0)):
	    time.sleep(.5)
	self.lastImageSize = (0,0)
	self.blankImage = None

        Frame.__init__(self, master)
        self.pack(fill='both', expand='yes')
        self.createWidgets()
	self.dirty = False

	self.updateWindow()

def guicsv_main(mapdom, svg, name_map):
    root = Tk()
    root.title('svgtoquiz: edit csv file')
    app = Application(svg, mapdom, name_map=name_map, master=root)
    root.protocol("WM_DELETE_WINDOW", app.quitApp)
    app.mainloop()
    try: root.destroy()
    except: print >> sys.stderr, 'warning: could not destroy tcl/tk root.'
    sys.exit(1)

