#!/usr/bin/env python2.3
#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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
SchoolTool GUI client.

SchoolTool is a common information systems platform for school administration
Visit http://www.schooltool.org/

Copyright (c) 2003 Shuttleworth Foundation

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""

import sets
from wxPython.wx import *
from wxPython.lib.scrolledpanel import wxScrolledPanel
from guiclient import SchoolToolClient, SchoolToolError, Unchanged

__metaclass__ = type


class ServerSettingsDlg(wxDialog):
    """Server Settings dialog."""

    def __init__(self, *args, **kwds):
        if len(args) < 1: kwds.setdefault('parent', None)
        if len(args) < 2: kwds.setdefault('id', -1)
        if len(args) < 3: kwds.setdefault('title', 'Server Settings')

        # begin wxGlade: ServerSettingsDlg.__init__
        kwds["style"] = wxDIALOG_MODAL|wxCAPTION
        wxDialog.__init__(self, *args, **kwds)
        self.serverLabel = wxStaticText(self, -1, "Server")
        self.serverTextCtrl = wxTextCtrl(self, -1, "localhost")
        self.portLabel = wxStaticText(self, -1, "Port")
        self.portTextCtrl = wxTextCtrl(self, -1, "8080")
        self.okBtn = wxButton(self, wxID_OK, "Ok")
        self.cancelBtn = wxButton(self, wxID_CANCEL, "Cancel")

        self.__set_properties()
        self.__do_layout()
        # end wxGlade

        EVT_BUTTON(self, wxID_OK, self.OnOk)

    def __set_properties(self):
        # begin wxGlade: ServerSettingsDlg.__set_properties
        self.SetTitle("Server Settings")
        self.okBtn.SetDefault()
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: ServerSettingsDlg.__do_layout
        rootSizer = wxBoxSizer(wxVERTICAL)
        btnSizer = wxBoxSizer(wxHORIZONTAL)
        mainSizer = wxFlexGridSizer(2, 2, 16, 16)
        mainSizer.Add(self.serverLabel, 2, 0, 0)
        mainSizer.Add(self.serverTextCtrl, 0, wxEXPAND, 0)
        mainSizer.Add(self.portLabel, 2, 0, 0)
        mainSizer.Add(self.portTextCtrl, 0, wxEXPAND, 0)
        mainSizer.AddGrowableCol(1)
        rootSizer.Add(mainSizer, 1, wxALL|wxEXPAND, 16)
        btnSizer.Add(self.okBtn, 0, 0, 0)
        btnSizer.Add(self.cancelBtn, 0, wxLEFT, 16)
        rootSizer.Add(btnSizer, 0, wxLEFT|wxRIGHT|wxBOTTOM|wxALIGN_RIGHT, 16)
        self.SetAutoLayout(1)
        self.SetSizer(rootSizer)
        rootSizer.Fit(self)
        rootSizer.SetSizeHints(self)
        self.Layout()
        # end wxGlade

    def getServer(self):
        return self.serverTextCtrl.GetValue()

    def setServer(self, value):
        self.serverTextCtrl.SetValue(value)

    def getPort(self):
        return int(self.portTextCtrl.GetValue())

    def setPort(self, value):
        self.portTextCtrl.SetValue(str(value))

    def OnOk(self, event):
        if not self.getServer().strip():
            self.serverTextCtrl.SetFocus()
            wxBell()
            return
        try:
            port = self.getPort()
        except ValueError:
            port = -1
        if not 0 < port <= 65535:
            self.portTextCtrl.SetFocus()
            wxBell()
            return
        self.EndModal(wxID_OK)


class RollCallDlg(wxDialog):
    """Roll call dialog."""

    def __init__(self, parent, group_title, rollcall):
        wxDialog.__init__(self, parent, -1, "Roll Call for %s" % group_title,
              style=wxDIALOG_MODAL|wxCAPTION|wxRESIZE_BORDER|wxTHICK_FRAME)

        vsizer = wxBoxSizer(wxVERTICAL)

        scrolled_panel = wxScrolledPanel(self, -1)
        grid = wxFlexGridSizer(len(rollcall), 5, 4, 8)
        self.items = []
        for title, href, presence in rollcall:
            if presence == 'present':
                was_absent = False
                presence = ""
            else:
                was_absent = True
                presence = 'reported\n%s' % presence
            grid.Add(wxStaticText(scrolled_panel, -1, title),
                     0, wxALIGN_CENTER_VERTICAL|wxRIGHT, 4)
            grid.Add(wxStaticText(scrolled_panel, -1, presence),
                     0, wxALIGN_CENTER_VERTICAL|wxRIGHT, 4)
            radio_sizer = wxBoxSizer(wxVERTICAL)
            abutton0 = wxRadioButton(scrolled_panel, -1, "Unset",
                                     style=wxRB_GROUP)
            abutton0.Hide()
            abutton1 = wxRadioButton(scrolled_panel, -1, "Absent")
            abutton2 = wxRadioButton(scrolled_panel, -1, "Present")
            if was_absent:
                EVT_RADIOBUTTON(self, abutton1.GetId(), self.OnPresenceChanged)
                EVT_RADIOBUTTON(self, abutton2.GetId(), self.OnPresenceChanged)
            radio_sizer.Add(abutton2)
            radio_sizer.Add(abutton1)
            grid.Add(radio_sizer)
            text_ctrl = wxTextCtrl(scrolled_panel, -1, style=wxTE_MULTILINE)
            grid.Add(text_ctrl, 1, wxEXPAND)
            radio_sizer = wxBoxSizer(wxVERTICAL)
            rbutton0 = wxRadioButton(scrolled_panel, -1, "Unset",
                                     style=wxRB_GROUP)
            rbutton0.Hide()
            rbutton1 = wxRadioButton(scrolled_panel, -1, "Resolve")
            rbutton2 = wxRadioButton(scrolled_panel, -1, "Do not resolve")
            rbutton1.Disable()
            rbutton2.Disable()
            radio_sizer.Add(rbutton1)
            radio_sizer.Add(rbutton2)
            grid.Add(radio_sizer)
            self.items.append((href, was_absent, abutton1, abutton2, text_ctrl,
                               rbutton1, rbutton2))
        scrolled_panel.SetSizer(grid)
        scrolled_panel.SetupScrolling(scroll_x=False)
        grid.AddGrowableCol(3)
        grid.Fit(scrolled_panel)
        vsizer.Add(scrolled_panel, 1, wxEXPAND|wxALL, 8)

        static_line = wxStaticLine(self, -1)
        vsizer.Add(static_line, 0, wxEXPAND, 0)

        button_bar = wxBoxSizer(wxHORIZONTAL)
        ok_btn = wxButton(self, wxID_OK, "OK")
        cancel_btn = wxButton(self, wxID_CANCEL, "Cancel")
        ok_btn.SetDefault()
        EVT_BUTTON(self, wxID_OK, self.OnOk)
        button_bar.Add(ok_btn, 0, wxRIGHT, 16)
        button_bar.Add(cancel_btn, 0, 0, 0)
        vsizer.Add(button_bar, 0, wxALIGN_RIGHT|wxALL, 16)

        self.SetSizer(vsizer)
        vsizer.SetSizeHints(self)
        self.Layout()

    def OnPresenceChanged(self, event):
        """Enable/disable resolved radio buttons when presence is set."""
        for (href, was_absent, absent, present, comment,
             resolve, dontresolve) in self.items:
             if was_absent:
                 enabled = present.GetValue()
                 resolve.Enable(enabled)
                 dontresolve.Enable(enabled)

    def OnOk(self, event):
        """Verify that all required data is entered before closing the dialog.
        """
        for (href, was_absent, absent, present, comment,
             resolve, dontresolve) in self.items:
            if absent.GetValue() == present.GetValue():
                absent.SetFocus()
                wxBell()
                return
            if (present.GetValue() and was_absent
                and resolve.GetValue() == dontresolve.GetValue()):
                resolve.SetFocus()
                wxBell()
                return
        self.EndModal(wxID_OK)

    def getRollCall(self):
        """Collect the data for sending a roll call."""
        rollcall = []
        for (href, was_absent, absent, present, comment,
             resolve, dontresolve) in self.items:
            if absent.GetValue() == present.GetValue():
                presence = None
            else:
                presence = present.GetValue()
            if resolve.GetValue() == dontresolve.GetValue():
                resolved = None
            else:
                resolved = resolve.GetValue()
            comment = comment.GetValue()
            rollcall.append((href, presence, comment, resolved))
        return rollcall


class AbsenceFrame(wxFrame):
    """Window showing the list of person's absences."""

    def __init__(self, client, person_id, title, parent=None, id=-1,
                 persons=True):
        """Create an absence list window."""
        wxFrame.__init__(self, parent, id, title, size=wxSize(400, 300))
        self.client = client
        self.title = title
        self.person_id = person_id
        self.absence_data = []
        self.persons = persons

        main_sizer = wxBoxSizer(wxVERTICAL)
        splitter = wxSplitterWindow(self, -1, style=wxSP_NOBORDER)
        ID_ABSENCE_LIST = wxNewId()
        self.absence_list = wxListCtrl(splitter, ID_ABSENCE_LIST,
                style=wxLC_REPORT|wxSUNKEN_BORDER|wxLC_SINGLE_SEL)
        self.absence_list.InsertColumn(0, "Date", width=110)
        self.absence_list.InsertColumn(1, "Ended?", width=110)
        self.absence_list.InsertColumn(2, "Resolved?", width=110)
        self.absence_list.InsertColumn(3, "Expected Presence", width=150)
        if self.persons:
            self.absence_list.InsertColumn(1, "Person", width=110)
        EVT_LIST_ITEM_SELECTED(self, ID_ABSENCE_LIST, self.DoSelectAbsence)
        self.comment_list = wxListCtrl(splitter, -1,
                style=wxLC_REPORT|wxSUNKEN_BORDER|wxLC_SINGLE_SEL)
        self.comment_list.InsertColumn(0, "Date", width=110)
        self.comment_list.InsertColumn(1, "Reporter", width=110)
        self.comment_list.InsertColumn(2, "Absent From", width=110)
        self.comment_list.InsertColumn(3, "Ended?", width=110)
        self.comment_list.InsertColumn(4, "Resolved?", width=110)
        self.comment_list.InsertColumn(5, "Expected Presence", width=150)
        self.comment_list.InsertColumn(6, "Comment", width=200)
        splitter.SetMinimumPaneSize(50)
        splitter.SplitHorizontally(self.absence_list, self.comment_list, 100)
        main_sizer.Add(splitter, 1, wxEXPAND|wxLEFT|wxRIGHT|wxTOP, 8)

        button_bar = wxBoxSizer(wxHORIZONTAL)
        close_btn = wxButton(self, wxID_CLOSE, "Close")
        EVT_BUTTON(self, wxID_CLOSE, self.OnClose)
        close_btn.SetDefault()
        button_bar.Add(close_btn)
        main_sizer.Add(button_bar, 0, wxALIGN_RIGHT|wxALL, 16)

        self.SetSizer(main_sizer)
        self.SetSizeHints(minW=200, minH=200)
        self.Layout()

        self.DoRefresh()

    def OnClose(self, event=None):
        """Close the absence window."""
        self.Close(True)

    def DoRefresh(self, event=None):
        """Refresh the absence list."""
        self.absence_list.DeleteAllItems()
        self.absence_data = []
        self.comment_list.DeleteAllItems()
        self.comment_data = []
        try:
            self.absence_data = self.client.getAbsences(self.person_id)
        except SchoolToolError, e:
            wxMessageBox("Could not get list of absences: %s" % e, self.title,
                         wxICON_ERROR|wxOK)
            return
        # sort newest absences first
        self.absence_data.sort()
        self.absence_data.reverse()
        for idx, absence in enumerate(self.absence_data):
            self.absence_list.InsertStringItem(idx,
                    absence.datetime.isoformat(' '))
            self.absence_list.SetItemData(idx, idx)
            if self.persons:
                self.absence_list.SetStringItem(idx, 1, absence.person_title)
                n = 1
            else:
                n = 0
            self.absence_list.SetStringItem(idx, n+1,
                    absence.ended and "Yes" or "No")
            self.absence_list.SetStringItem(idx, n+2,
                    absence.resolved and "Yes" or "No")
            if absence.expected_presence is not None:
                self.absence_list.SetStringItem(idx, n+3,
                        absence.expected_presence.isoformat(' '))
            if not absence.ended:
                item = self.absence_list.GetItem(idx)
                item.SetTextColour(wxRED)
                self.absence_list.SetItem(item)
            elif not absence.resolved:
                item = self.absence_list.GetItem(idx)
                item.SetTextColour(wxBLUE)
                self.absence_list.SetItem(item)

    def DoSelectAbsence(self, event):
        """Refresh the absence comment list."""
        self.comment_list.DeleteAllItems()
        self.comment_data = []

        key = self.absence_list.GetItemData(event.m_itemIndex)
        absence = self.absence_data[key]
        try:
            self.comment_data = self.client.getAbsenceComments(absence.uri)
        except SchoolToolError, e:
            return
        # sort newest comments first
        self.comment_data.sort()
        self.comment_data.reverse()
        for idx, comment in enumerate(self.comment_data):
            self.comment_list.InsertStringItem(idx,
                    comment.datetime.isoformat(' '))
            self.comment_list.SetItemData(idx, idx)
            self.comment_list.SetStringItem(idx, 1, comment.reporter_title)
            self.comment_list.SetStringItem(idx, 2, comment.absent_from_title)
            if comment.ended is not Unchanged:
                self.comment_list.SetStringItem(idx, 3,
                        comment.ended and "Yes" or "No")
            if comment.resolved is not Unchanged:
                self.comment_list.SetStringItem(idx, 4,
                        comment.resolved and "Yes" or "No")
            if comment.expected_presence is not Unchanged:
                if comment.expected_presence is not None:
                    self.comment_list.SetStringItem(idx, 5,
                            comment.expected_presence.isoformat(' '))
                else:
                    self.comment_list.SetStringItem(idx, 5, "-")
            self.comment_list.SetStringItem(idx, 6, comment.text)


class MainFrame(wxFrame):
    """Main frame."""

    def __init__(self, client, parent=None, id=-1, title="SchoolTool"):
        """Create the main application window."""
        wxFrame.__init__(self, parent, id, title, size=wxSize(500, 400))
        self.client = client
        self.CreateStatusBar()

        # Menu bar

        def menubar(*items):
            menubar = wxMenuBar()
            for menu, title in items:
                menubar.Append(menu, title)
            return menubar

        def popupmenu(*items):
            menu = wxMenu()
            for item in items:
                getattr(menu, item[0])(*item[1:])
            return menu

        def menu(title, *items):
            return popupmenu(*items), title

        def separator():
            return ('AppendSeparator', )

        def item(title, description='', action=None, id=None):
            if not id:
                id = wxNewId()
            if action:
                EVT_MENU(self, id, action)
            return ('Append', id, title, description)

        def submenu(title, *items, **kw):
            description = kw.get('description', '')
            id = kw.get('id', None)
            if not id:
                id = wxNewId()
            submenu, title = menu(title, items)
            return ('AppendMenu', id, title, submenu, description)

        self.SetMenuBar(menubar(
            menu("&File",
                item("E&xit\tAlt+X", "Terminate the program", self.DoExit),
                ),
            menu("&View",
                item("All &Absences", "List all absences in the system",
                     self.DoViewAllAbsences),
                separator(),
                item("&Refresh\tAlt+R", "Refresh data from the server",
                     self.DoRefresh),
                ),
            menu("&Settings",
                item("&Server", "Server settings", self.DoServerSettings),
                ),
            menu("&Help",
                item("&About", "About SchoolTool", self.DoAbout),
                ),
            ))

        # client area: vertical splitter
        splitter = wxSplitterWindow(self, -1, style=wxSP_NOBORDER)

        # left pane of the splitter: group tree control
        ID_GROUP_TREE = wxNewId()
        self.groupTreeCtrl = wxTreeCtrl(splitter, ID_GROUP_TREE,
                style=wxTR_HAS_BUTTONS|wxTR_HIDE_ROOT|wxSUNKEN_BORDER)
        EVT_TREE_SEL_CHANGED(self, ID_GROUP_TREE, self.DoSelectGroup)
        # XXX temporarily allow doing roll calls with a double click
        EVT_TREE_ITEM_ACTIVATED(self, ID_GROUP_TREE, self.DoRollCall)
        self.treePopupMenu = popupmenu(
                item("&Refresh", "Refresh", self.DoRefresh),
                item("Roll &Call", "Do a roll call", self.DoRollCall)
            )
        EVT_RIGHT_DOWN(self.groupTreeCtrl, self.DoTreeRightDown)
        # looks like I need both for this to work on Gtk and MSW
        EVT_RIGHT_UP(self.groupTreeCtrl, self.DoTreePopup)
        EVT_COMMAND_RIGHT_CLICK(self.groupTreeCtrl, ID_GROUP_TREE,
                                self.DoTreePopup)

        # right pane of the splitter: horizontal splitter
        splitter2 = wxSplitterWindow(splitter, -1, style=wxSP_NOBORDER)

        # top pane of the second splitter: member list
        panel2a = wxPanel(splitter2, -1)
        label2a = wxStaticText(panel2a, -1, "Members")
        self.personListCtrl = wxListCtrl(panel2a,
                                         style=wxSUNKEN_BORDER|wxLC_SINGLE_SEL)
        self.personPopupMenu = popupmenu(
                item("View &Absences", "View a list of person's absences",
                     self.DoViewPersonAbsences)
            )
        EVT_RIGHT_DOWN(self.personListCtrl, self.DoPersonRightDown)
        # looks like I need both for this to work on Gtk and MSW
        EVT_RIGHT_UP(self.personListCtrl, self.DoPersonPopup)
        EVT_COMMAND_RIGHT_CLICK(self.personListCtrl, ID_GROUP_TREE,
                                self.DoPersonPopup)
        sizer2a = wxBoxSizer(wxVERTICAL)
        sizer2a.Add(label2a)
        sizer2a.Add(self.personListCtrl, 1, wxEXPAND)
        panel2a.SetSizer(sizer2a)

        # bottom pane of the second splitter: relationship list
        panel2b = wxPanel(splitter2, -1)
        label2b = wxStaticText(panel2b, -1, "Relationships")
        self.relationshipListCtrl = wxListCtrl(panel2b,
                style=wxSUNKEN_BORDER|wxLC_REPORT)
        self.relationshipListCtrl.InsertColumn(0, "Title", width=110)
        self.relationshipListCtrl.InsertColumn(1, "Role", width=110)
        self.relationshipListCtrl.InsertColumn(2, "Relationship", width=110)
        sizer2b = wxBoxSizer(wxVERTICAL)
        sizer2b.Add(label2b)
        sizer2b.Add(self.relationshipListCtrl, 1, wxEXPAND)
        panel2b.SetSizer(sizer2b)

        # connect panes to the second splitter
        splitter2.SetMinimumPaneSize(50)
        splitter2.SplitHorizontally(panel2a, panel2b, 150)

        # connect panes to the first splitter
        splitter.SetMinimumPaneSize(20)
        splitter.SplitVertically(self.groupTreeCtrl, splitter2, 150)

        # finishing touches
        self.SetSizeHints(minW=100, minH=150)
        self.DoRefresh()

    def DoExit(self, event):
        """Exit the application.

        Accessible via Alt+X and from File|Exit.
        """
        self.Close(True)

    def DoServerSettings(self, event):
        """Show the Server Settings dialog.

        Accessible from Settings|Server settings.
        """
        dlg = ServerSettingsDlg(self)
        dlg.setServer(self.client.server)
        dlg.setPort(self.client.port)
        if dlg.ShowModal() == wxID_OK:
            self.client.setServer(dlg.getServer(), dlg.getPort())
            self.DoRefresh()
        dlg.Destroy()

    def DoAbout(self, event):
        """Show the About dialog.

        Accessible from Help|About.
        """
        dlg = wxMessageDialog(self, __doc__, "About SchoolTool", wxOK)
        dlg.ShowModal()
        dlg.Destroy()

    def DoSelectGroup(self, event):
        """Update member and relationship lists for the selected group.

        Called when the group tree control selection is changed and in
        some other cases (e.g. from DoRefresh).
        """

        # Clear lists and see if a group is selected
        self.personListData = []
        self.personListCtrl.DeleteAllItems()
        self.relationshipListData = []
        self.relationshipListCtrl.DeleteAllItems()
        item = self.groupTreeCtrl.GetSelection()
        if not item.IsOk():
            return
        group_id = self.groupTreeCtrl.GetPyData(item)

        # Fill in group member list
        try:
            info = self.client.getGroupInfo(group_id)
        except SchoolToolError, e:
            self.SetStatusText(str(e))
            return
        self.SetStatusText(self.client.status)
        self.personListData = info.members
        for idx, (title, person_id) in enumerate(self.personListData):
            self.personListCtrl.InsertStringItem(idx, title)
            self.personListCtrl.SetItemData(idx, idx)

        def compare(x, y):
            return cmp(self.personListData[x], self.personListData[y])

        self.personListCtrl.SortItems(compare)

        # Fill in group relationship list
        try:
            self.relationshipListData = self.client.getObjectRelationships(
                                                                    group_id)
        except SchoolToolError, e:
            self.SetStatusText(str(e))
            return
        self.SetStatusText(self.client.status)
        self.relationshipListData.sort()
        for idx, (arcrole, role, title, href) in enumerate(
                                                    self.relationshipListData):
            self.relationshipListCtrl.InsertStringItem(idx, title)
            self.relationshipListCtrl.SetItemData(idx, idx)
            self.relationshipListCtrl.SetStringItem(idx, 1, role)
            self.relationshipListCtrl.SetStringItem(idx, 2, arcrole)

    def DoTreeRightDown(self, event):
        """Select the group under mouse cursor.

        Called when the right mouse buton is pressed on the group tree
        control.
        """
        item, flags = self.groupTreeCtrl.HitTest(event.GetPosition())
        if item.IsOk():
            self.groupTreeCtrl.SelectItem(item)
        event.Skip()

    def DoTreePopup(self, event):
        """Show the popup menu for the group tree control.

        Called when the right mouse buton released on the group tree
        control.
        """
        self.groupTreeCtrl.PopupMenu(self.treePopupMenu, event.GetPosition())

    def DoPersonRightDown(self, event):
        """Select the person under mouse cursor.

        Called when the right mouse buton is pressed on the person list
        control.
        """
        item, flags = self.personListCtrl.HitTest(event.GetPosition())
        if flags & wxLIST_HITTEST_ONITEM:
            self.personListCtrl.Select(item)
        event.Skip()

    def DoPersonPopup(self, event):
        """Show the popup menu for the person list control.

        Called when the right mouse buton released on the person list
        control.
        """
        self.personListCtrl.PopupMenu(self.personPopupMenu,
                                      event.GetPosition())

    def DoRefresh(self, event=None):
        """Refresh data from the server.

        Accessible via Alt+R, from View|Refresh and from the group tree
        popup menu.

        XXX there are reentrancy problems -- hold down Alt-R and watch.
            it looks like wxWindows can call DoRefresh while another
            "thread" is still inside DoRefresh
        """

        # Get the tree from the server
        try:
            group_tree = self.client.getGroupTree()
        except SchoolToolError, e:
            self.SetStatusText(str(e))
            group_tree = []
        else:
            self.SetStatusText(self.client.status)

        # Remember current selection
        old_selection = None
        item = self.groupTreeCtrl.GetSelection()
        if item.IsOk():
            old_selection = self.groupTreeCtrl.GetPyData(item)

        # Remember which items were expanded
        expanded = sets.Set()
        stack = []
        root = self.groupTreeCtrl.GetRootItem()
        stack = [root]
        while stack:
            item = stack.pop()
            if item is not root and self.groupTreeCtrl.IsExpanded(item):
                expanded.add(self.groupTreeCtrl.GetPyData(item))
            next, cookie = self.groupTreeCtrl.GetFirstChild(item, 0)
            if next.IsOk():
                stack.append(next)
            next = self.groupTreeCtrl.GetNextSibling(item)
            if next.IsOk():
                stack.append(next)

        # Reload tree
        self.groupTreeCtrl.Freeze()
        self.groupTreeCtrl.DeleteAllItems()
        root = self.groupTreeCtrl.AddRoot("Roots")
        self.groupTreeCtrl.Expand(root)
        stack = [(root, None)]
        selected_item = None
        for level, title, href in group_tree:
            while len(stack) > level + 1:
                last = stack.pop()[0]
                self.groupTreeCtrl.SortChildren(last)
            assert len(stack) == level+1
            item = self.groupTreeCtrl.AppendItem(stack[-1][0], title)
            if level == 1 or stack[-1][1] in expanded:
                self.groupTreeCtrl.Expand(stack[-1][0])
            self.groupTreeCtrl.SetPyData(item, href)
            if href == old_selection and selected_item is None:
                selected_item = item
                self.groupTreeCtrl.SelectItem(item)
            stack.append((item, href))
        while stack:
            last = stack.pop()[0]
            self.groupTreeCtrl.SortChildren(last)

        if selected_item is None:
            self.groupTreeCtrl.Unselect()
            self.DoSelectGroup(None)
        else:
            self.groupTreeCtrl.EnsureVisible(selected_item)
        self.groupTreeCtrl.Thaw()

    def DoRollCall(self, event=None):
        """Open the roll call dialog.

        Accessible from group tree popup menu.
        """
        item = self.groupTreeCtrl.GetSelection()
        if not item.IsOk():
            self.SetStatusText("No group selected")
            return
        group_id = self.groupTreeCtrl.GetPyData(item)
        group_title = self.groupTreeCtrl.GetItemText(item)
        try:
            rollcall = self.client.getRollCall(group_id)
        except SchoolToolError, e:
            self.SetStatusText(str(e))
            return
        rollcall.sort()
        dlg = RollCallDlg(self, group_title, rollcall)
        if dlg.ShowModal() == wxID_OK:
            rollcall = dlg.getRollCall()
            try:
                self.client.submitRollCall(group_id, rollcall)
            except SchoolToolError, e:
                self.SetStatusText(str(e))
            else:
                self.SetStatusText(self.client.status)
        dlg.Destroy()

    def DoViewPersonAbsences(self, event=None):
        """Open the absences window for the currently selected person.

        Accessible from person list popup menu.
        """
        item = self.personListCtrl.GetFirstSelected()
        if item == -1:
            self.SetStatusText("No person selected")
            return
        key = self.personListCtrl.GetItemData(item)
        title, person_id = self.personListData[key]
        window = AbsenceFrame(self.client, "%s/absences" % person_id,
                              parent=self, title="%s's absences" % title,
                              persons=False)
        window.Show()

    def DoViewAllAbsences(self, event=None):
        """Open the absences window for the whole system person.

        Accessible via View|All Absences.
        """
        window = AbsenceFrame(self.client, "/utils/absences", parent=self,
                              title="All absences", persons=True)
        window.Show()


class SchoolToolApp(wxApp):
    """Main application."""

    def __init__(self, client):
        self.client = client
        wxApp.__init__(self)

    def OnInit(self):
        """Initialize the application (create the main window)."""
        self.frame = MainFrame(self.client)
        self.frame.Show(True)
        self.SetTopWindow(self.frame)
        return True


def main():
    wxInitAllImageHandlers()
    client = SchoolToolClient()
    app = SchoolToolApp(client)
    app.MainLoop()


# XXX libxml2 errors are noisy on the stderr, should register an error handler

if __name__ == '__main__':
    main()
