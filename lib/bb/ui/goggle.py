#
# BitBake Graphical GTK User Interface
#
# Copyright (C) 2008        Intel Corporation
#
# Authored by Rob Bradford <rob@linux.intel.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import gobject
import gtk
import xmlrpclib
from bb.ui.crumbs.runningbuild import RunningBuildTreeView, RunningBuild
from bb.ui.crumbs.progress import ProgressBar

import Queue

def event_handle_idle_func (eventHandler, build, pbar):

    # Consume as many messages as we can in the time available to us
    try:
        event = eventHandler.get(False)
        while event:
            build.handle_event (event, pbar)
            event = eventHandler.get(False)
    except Queue.Empty:
        pass
    
    return True

def scroll_tv_cb (model, path, iter, view):
    view.scroll_to_cell (path)

class MainWindow (gtk.Window):
    def __init__ (self):
        gtk.Window.__init__ (self, gtk.WINDOW_TOPLEVEL)

        # Setup tree view and the scrolled window
        scrolled_window = gtk.ScrolledWindow ()
        self.add (scrolled_window)
        self.cur_build_tv = RunningBuildTreeView()
        self.connect("delete-event", gtk.main_quit)
        self.set_default_size(640, 480)
        scrolled_window.add (self.cur_build_tv)

def main (server, eventHandler):
    gobject.threads_init()
    gtk.gdk.threads_init()

    window = MainWindow ()
    window.show_all ()
    pbar = ProgressBar(window)

    # Create the object for the current build
    running_build = RunningBuild ()
    window.cur_build_tv.set_model (running_build.model)
    running_build.model.connect("row-inserted", scroll_tv_cb, window.cur_build_tv)
    try:
        cmdline = server.runCommand(["getCmdLineAction"])
        print(cmdline)
        if not cmdline:
            return 1
        ret = server.runCommand(cmdline)
        if ret != True:
            print("Couldn't get default commandline! %s" % ret)
            return 1
    except xmlrpclib.Fault as x:
        print("XMLRPC Fault getting commandline:\n %s" % x)
        return 1

    # Use a timeout function for probing the event queue to find out if we
    # have a message waiting for us.
    gobject.timeout_add (100,
                         event_handle_idle_func,
                         eventHandler,
                         running_build,
                         pbar)

    gtk.main()
