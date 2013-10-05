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

import xml.dom.minidom, os, os.path, codecs
import datetime
from svgtoquiz import register_export_class, ExportFile, options
from sets import Set
import random
import getpass
from zipfile import ZipFile
import cStringIO

default_card_atts = {
    'card_t'  : '4',
    'fact_v'  : '4.1',

    'e'       : '2.5',
    'gr'      : '-1',
    'rt_rp_l' : '0',
    'lps'     : '0',
    'l_rp'    : '-1',
    'n_rp'    : '-1',
    'ac_rp_l' : '0',
    'rt_rp'   : '0',
    'ac_rp'   : '0',
}

# This function is lifted from libmnemosyne/utils.py
# (r1177, Peter.Bienstman@UGent.be)
def rand_uuid():

    """Importing Python's uuid module brings a huge overhead, so we use
    our own variant: a length 22 random string from a 62 letter alphabet,
    which in terms of randomness is about the same as the traditional hex
    string with length 32, but uses less space.

    """

    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXZY0123456789"
    rand = random.random
    uuid = ""
    for c in range(22):
        uuid += chars[int(rand() * 62.0 - 1)]
    return uuid

def wd(writer, data):
    data = data.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    writer.write(data)

xml.dom.minidom._write_data = wd

class MnemosyneFile2(ExportFile):
    """
    Export plugin for Mnemosyne 2.x.
    """
    name = "mnemosyne2"

    def makeTextNode(self, tagName, text):
        """
        Given an xml dom object, create a tagName element containing text.
        """
        c = self.dom.createElement(tagName)
        c.appendChild(self.dom.createTextNode(text))
        return c

    def __init__(self, category, filepath):
        """
        Initialize an export file with a category name.
        """
        ExportFile.__init__(self, category, 'cards.xml')

        self.dom = xml.dom.minidom.Document()

        self.ids = Set([])
        self.tag_id = self.getId()

        self.images = Set([])
        self.facts = []
        self.cards = []

    def getId(self):
        """
        Return a new, fresh id value.
        """
        new_id = rand_uuid()
        while new_id in self.ids:
            new_id = rand_uuid()
        self.ids.add(new_id)
        return new_id

    def addItem(self, objname, blank, highlighted, addnormal, addinverse):
        """
        Add an item to the export file.

        objname:        The name of the quiz object being highlighted,
                        for use as a question or answer.
                        e.g. 'California'
        blank:          The path to the quiz image with nothing highlighted.
                        e.g. a plain map of the USA.
        highlighted:    The path to the quiz image with objname highlighted.
                        e.g. the USA map with a single state in red.
        addnormal:      add a normal card, i.e, show the highlighted image
                        in the answer.
        addinverse:     add an inverse card, i.e. show the highlighted
                        image in the question.
        """

        # Add images
        if blank != None: self.images.add(blank)
        if highlighted != None: self.images.add(highlighted)

        # Add the fact
        fact_id = self.getId()
        loc = self.makeTextNode('loc', objname)
        marked = self.makeTextNode('marked', '<img src="%s">' % highlighted)
        blank = self.makeTextNode('blank', '<img src="%s">' % blank)

        if addnormal or addinverse:
            self.facts.append((fact_id, [loc, marked, blank]))

        # Add the cards
        card_id = self.getId()
        inv_card_id = card_id + '.inv'
        card_atts = { 'tags' : self.tag_id, 'fact' : fact_id }

        if addnormal:
            self.cards.append((card_id,
                dict(card_atts.items() + default_card_atts.items())))

        if addinverse:
            self.cards.append((inv_card_id,
                dict(card_atts.items() + default_card_atts.items())))

    def addLogItem(self, log_type, attributes={}, children=None, o_id=None):
        """
        Add a log entry of the given type with optional child elements and
        attributes. Return the generated o_id.
        """
        e = self.dom.createElement('log')
        e.setAttribute('type', str(log_type))

        if o_id == False:
            o_id = None
        else:
            if o_id is None:
                o_id = self.getId()

            e.setAttribute('o_id', o_id)
            e.setIdAttribute('o_id')

        for att in attributes.iteritems():
            e.setAttribute(*att)

        if type(children) is not list:
            if children is None:
                children = []
            else:
                children = [children]

        for child in children:
            e.appendChild(child)

        self.mnemosyne.appendChild(e)
        return o_id

    def write(self):
        """
        Create a file at path and write all items to it.
        """

        m = self.dom.createElement('openSM2sync')

        m.setAttribute('number_of_entries',
            str(1 + len(self.images) + len(self.facts) + len(self.cards)))
        self.dom.appendChild(m)
        self.mnemosyne = m

        tag_id = self.addLogItem(10,
                    children=self.makeTextNode('name', self.category),
                    o_id=self.tag_id)

        for img in self.images:
            self.addLogItem(13,
                    children=self.makeTextNode('fname', img), o_id=False)

        for (fact_id, fact_ele) in self.facts:
            self.addLogItem(16, children=fact_ele, o_id=fact_id)

        for (card_id, card_atts) in self.cards:
            self.addLogItem(6, attributes=card_atts, o_id=card_id)

        xfp = codecs.open(self.filepath, 'wb', 'UTF-8')
        self.dom.writexml(xfp, encoding='UTF-8', addindent='  ', newl='\n')
        xfp.close()

        # Write the metadata skeleton
        md = codecs.open('METADATA', 'wb', 'UTF-8')
        md.write('tags: %s\n' % self.category)
        md.write('author_email: \n')
        md.write('notes: \n')
        md.write('author_name: %s\n' % getpass.getuser())
        md.write('card_set_name: %s\n' % self.category)
        md.write('date: %s\n' % datetime.date.today().isoformat())
        md.write('revision: 1\n')

        # Create a zip file
        czip_name = '%s.cards' % self.category.replace(' ', '_').lower()
        with ZipFile(czip_name, 'w') as czip:
            czip.write('cards.xml')
            czip.write('METADATA')
            for img in self.images:
                czip.write(img)

    def init(cls, args = []):
        """
        Called just after options have been parsed, but before any other
        work is done.
        """
        cls.setExportDefaultPath(os.getcwd(), '')

    init = classmethod(init)

register_export_class(MnemosyneFile2)

