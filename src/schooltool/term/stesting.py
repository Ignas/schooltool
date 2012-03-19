#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
Selenium functional tests setup for schooltool.term
"""

import os

from schooltool.testing.selenium import SeleniumLayer

dir = os.path.abspath(os.path.dirname(__file__))
filename = os.path.join(dir, 'stesting.zcml')

term_selenium_layer = SeleniumLayer(filename,
                                    __name__,
                                    'term_selenium_layer')

def registerSeleniumSetup():
    try:
        import selenium
    except ImportError:
        return
    from schooltool.testing import registry
    import schooltool.testing.selenium

    def addTerm(browser, schoolyear, title, first, last):
        browser.query.link('School').click()
        browser.query.link('Terms').click()
        browser.query.link(schoolyear).click()
        browser.query.link('Term').click()
        browser.query.name('form.widgets.title').type(title)
        browser.query.name('form.widgets.first').ui.enter_date(first)
        browser.query.name('form.widgets.last').ui.enter_date(last)
        page = browser.query.tag('html')
        browser.query.button('Next').click()
        browser.wait(lambda: page.expired)
        page = browser.query.tag('html')
        browser.query.button('Submit').click()
        browser.wait(lambda: page.expired)

    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerBrowserUI(
            'term.add', addTerm))

registerSeleniumSetup()
del registerSeleniumSetup
