#!/usr/bin/make
#
# Makefile for SchoolTool
#
# $Id$

PYTHON=python2.3
PYTHONDIR=/usr/lib/python2.3
TESTFLAGS=-w
PO=$(wildcard src/schooltool/locales/*/LC_MESSAGES/*.po)
PYTHONPATH=src:Zope3/src


all: build

build: build-translations
	$(PYTHON) setup.py schoolbell build_ext -i
	$(PYTHON) setup.py schooltool build_ext -i
	cd Zope3 && $(PYTHON) setup.py build_ext -i
	$(PYTHON) remove-stale-bytecode.py

build-translations: $(MO)

clean:
	find . \( -path './src/schooltool/*.mo' -o -name '*.o' \
	         -o -name '*.py[co]' \) -exec rm -f {} \;
	rm -rf build

realclean: clean
	find . \( -name '*.so' -o -name '*.pyd' \) -exec rm -f {} \;
	rm -f Data.fs* *.csv tags ID *.log
	rm -f scripts/import-sampleschool
	rm -f MANIFEST.schoolbell
	rm -f MANIFEST.schooltool
	rm -rf dist

test: build
	LC_ALL="C" $(PYTHON) test.py $(TESTFLAGS) schooltool

testall: build
	LC_ALL="C" $(PYTHON) test.py $(TESTFLAGS)

ftest: build
	@LC_ALL="C" $(PYTHON) schooltool-server.py -c test.conf -d \
	&& ($(PYTHON) test.py -f $(TESTFLAGS) ; \
	kill `cat testserver.pid`)

run: build
	$(PYTHON) schooltool-server.py

runtestserver: build
	LC_ALL="C" $(PYTHON) schooltool-server.py -c test.conf

runclient: build
	$(PYTHON) schooltool-client.py

runwxclient: build
	$(PYTHON) wxschooltool.py

sampledata persons.csv groups.csv resources.csv timetable.csv roster.txt:
	$(PYTHON) generate-sampleschool.py

sampleschool: build persons.csv groups.csv resources.csv timetable.csv roster.txt
	@$(PYTHON) schooltool-server.py -d && \
	($(PYTHON) import-sampleschool.py ; \
	 kill `cat schooltool.pid`)

coverage: build
	rm -rf coverage
	LC_ALL="C" $(PYTHON) test.py $(TESTFLAGS) --coverage schooltool

coverage-report:
	@cd coverage && ls schooltool* | grep -v tests | xargs grep -c '^>>>>>>' | grep -v ':0$$'

coverage-report-list:
	@cd coverage && ls schooltool* | grep -v tests | xargs grep -l '^>>>>>>'

edit-coverage-reports:
	@cd coverage && $(EDITOR) `ls schooltool* | grep -v tests | xargs grep -l '^>>>>>>'`

vi-coverage-reports:
	@cd coverage && vi '+/^>>>>>>/' `ls schooltool* | grep -v tests | xargs grep -l '^>>>>>>'`

scripts/import-sampleschool: scripts/import-sampleschool.head
	(cat $< && sed -ne '/^# -- Do not remove this line --$$/,$$p' \
	    import-sampleschool.py) > $@

.PHONY: schooltooldist
schooltooldist: realclean build extract-translations \
	sampledata scripts/import-sampleschool clean
	rm -rf dist
	fakeroot ./debian/rules clean
	./setup.py schooltool sdist --formats=gztar,zip

.PHONY: schoolbelldist
schoolbelldist: realclean build extract-translations clean
	rm -rf dist
	fakeroot ./debian/rules clean
	./setup.py schoolbell sdist --formats=gztar,zip

.PHONY: signtar
signtar: dist
	md5sum dist/school*.{tar.gz,zip} > dist/md5sum
	gpg --clearsign dist/md5sum
	mv dist/md5sum.asc dist/md5sum

.PHONY: all build clean test ftest run coverage sampleschool

.PHONY: extract-translations
extract-translations:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) \
		Zope3/utilities/i18nextract.py -d schooltool \
			-o locales -p src/schooltool schooltool

.PHONY: update-translations
update-translations:
	for f in $(PO); do			\
	     msgmerge -U $$f $(POT);		\
	     msgfmt -o $${f%.po}.mo $$f;	\
	done
