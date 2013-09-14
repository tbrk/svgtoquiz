# $Id$

STAGINGDIR=develop
SRCDIR=src

PYTHON=python

#

all: develop

develop: env.sh
	mkdir -p $(STAGINGDIR)
	PYTHONPATH=`pwd`/$(STAGINGDIR):${PYTHONPATH} \
	$(PYTHON) setup.py develop --install-dir=$(STAGINGDIR)

dist: bdist_egg sdist bdist_wininst

bdist_egg:
	$(PYTHON) setup.py bdist_egg

sdist:
	$(PYTHON) setup.py sdist

bdist_wininst:
	$(PYTHON) setup.py bdist_wininst

env.sh:
	echo PYTHONPATH=`pwd`/$(STAGINGDIR):${PYTHONPATH} > env.sh

tags:
	(cd svgtoquiz; exctags *.py)

clean:
	-@rm $(SRCDIR)/svgtoquiz/*.pyc
	-@rm ez_setup.pyc
	-@rm -r build

clobber: clean
	-@rm -r svgtoquiz.egg-info
	-@rm svgtoquiz/tags
	-@rm -r develop dist
	-@rm env.sh

.PHONY: develop bdist_egg sdist bdist_wininst

