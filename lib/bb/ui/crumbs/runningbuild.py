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

import gtk
import gobject
import logging

class RunningBuildModel (gtk.TreeStore):
    (COL_TYPE, COL_PACKAGE, COL_TASK, COL_MESSAGE, COL_ICON, COL_COLOR, COL_NUM_ACTIVE) = (0, 1, 2, 3, 4, 5, 6)
    def __init__ (self):
        gtk.TreeStore.__init__ (self,
                                gobject.TYPE_STRING,
                                gobject.TYPE_STRING,
                                gobject.TYPE_STRING,
                                gobject.TYPE_STRING,
                                gobject.TYPE_STRING,
                                gobject.TYPE_STRING,
                                gobject.TYPE_INT)

class RunningBuild (gobject.GObject):
    __gsignals__ = {
          'build-succeeded' : (gobject.SIGNAL_RUN_LAST,
                               gobject.TYPE_NONE,
                               ()),
          'build-failed' : (gobject.SIGNAL_RUN_LAST,
                            gobject.TYPE_NONE,
                            ())
          }
    pids_to_task = {}
    tasks_to_iter = {}

    def __init__ (self):
        gobject.GObject.__init__ (self)
        self.model = RunningBuildModel()

    def handle_event (self, event, pbar=None):
        # Handle an event from the event queue, this may result in updating
        # the model and thus the UI. Or it may be to tell us that the build
        # has finished successfully (or not, as the case may be.)

        parent = None
        pid = 0
        package = None
        task = None

        # If we have a pid attached to this message/event try and get the
        # (package, task) pair for it. If we get that then get the parent iter
        # for the message.
        if hasattr(event, 'pid'):
            pid = event.pid
        if hasattr(event, 'process'):
            pid = event.process

        if pid in self.pids_to_task:
            (package, task) = self.pids_to_task[pid]
            parent = self.tasks_to_iter[(package, task)]

        if(isinstance(event, logging.LogRecord)):
            if (event.msg.startswith ("Running task")):
                return # don't add these to the list


            if event.levelno >= logging.ERROR:
                icon = "dialog-error"
                color = "#ffaaaa"
            elif event.levelno >= logging.WARNING:
                icon = "dialog-warning"
                color = "#F88017"
            else:
                icon = None
                color = "#ffffff"

            if event.args:
                message = event.msg % event.args
            else:
                message = event.msg
            self.model.append(parent,
                              (None,
                               package,
                               task,
                               message,
                               icon,
                               color,
                               0))

        if isinstance(event, bb.build.TaskStarted):
            (package, task) = (event._package, event._task)

            # Save out this PID.
            self.pids_to_task[pid] = (package, task)

            # Check if we already have this package in our model. If so then
            # that can be the parent for the task. Otherwise we create a new
            # top level for the package.
            if ((package, None) in self.tasks_to_iter):
                parent = self.tasks_to_iter[(package, None)]
            else:
                parent = self.model.append (None, (None,
                                                   package,
                                                   None,
                                                   "Package: %s" % (package),
                                                   None,
                                                   "#FFFFFF",
                                                   0))
                self.tasks_to_iter[(package, None)] = parent

            # Because this parent package now has an active child mark it as
            # such.
            # @todo if parent is already in error, don't mark it green
            # But will this ever happen?  Do we always bail immediately when
            # oen task fails?  Hell if I know...
            self.model.set(parent, self.model.COL_ICON, "gtk-execute")
            self.model.set(parent, self.model.COL_COLOR, "#aaffaa")

            # Add an entry in the model for this task
            i = self.model.append (parent, (None,
                                            package,
                                            task,
                                            "Task: %s" % (task),
                                            "gtk-execute",
                                            "#aaffaa",
                                            0))

            # update the parent's active task count
            num_active = self.model.get(parent, self.model.COL_NUM_ACTIVE)[0] + 1
            self.model.set(parent, self.model.COL_NUM_ACTIVE, num_active)

            # Save out the iter so that we can find it when we have a message
            # that we need to attach to a task.
            self.tasks_to_iter[(package, task)] = i

        elif isinstance(event, bb.build.TaskBase):
            current = self.tasks_to_iter[(package, task)]
            parent = self.tasks_to_iter[(package, None)]

            # update the parent's active count
            num_active = self.model.get(parent, self.model.COL_NUM_ACTIVE)[0] - 1
            self.model.set(parent, self.model.COL_NUM_ACTIVE, num_active)

            if isinstance(event, bb.build.TaskFailed):
                # Mark the task and parent as failed
                icon = "dialog-error"
                color = "#ffaaaa"

                for i in (current, parent):
                    self.model.set(i, self.model.COL_ICON, icon)
                    self.model.set(i, self.model.COL_COLOR, color)
            else:
                icon = None
                color = "#ffffff"

                # Mark the task as inactive
                self.model.set(current, self.model.COL_ICON, icon)
                self.model.set(current, self.model.COL_COLOR, color)

                # Mark the parent package as inactive, but make sure to
                # preserve error and active states
                i = self.tasks_to_iter[(package, None)]
                if self.model.get(parent, self.model.COL_ICON) != 'dialog-error':
                    self.model.set(parent, self.model.COL_ICON, icon)
                    if num_active == 0:
                        self.model.set(parent, self.model.COL_COLOR, "#ffffff")

            # Clear the iters and the pids since when the task goes away the
            # pid will no longer be used for messages
            del self.tasks_to_iter[(package, task)]
            del self.pids_to_task[pid]

        elif isinstance(event, bb.event.BuildCompleted):
            failures = int (event._failures)

            # Emit the appropriate signal depending on the number of failures
            if (failures > 1):
                self.emit ("build-failed")
            else:
                self.emit ("build-succeeded")

        elif isinstance(event, bb.event.CacheLoadStarted) and pbar:
            pbar.set_title("Loading cache")
            self.progress_total = event.total
            pbar.update(0, self.progress_total)
        elif isinstance(event, bb.event.CacheLoadProgress) and pbar:
            pbar.update(event.current, self.progress_total)
        elif isinstance(event, bb.event.CacheLoadCompleted) and pbar:
            pbar.update(self.progress_total, self.progress_total)

        elif isinstance(event, bb.event.ParseStarted) and pbar:
            pbar.set_title("Processing recipes")
            self.progress_total = event.total
            pbar.update(0, self.progress_total)
        elif isinstance(event, bb.event.ParseProgress) and pbar:
            pbar.update(event.current, self.progress_total)
        elif isinstance(event, bb.event.ParseCompleted) and pbar:
            pbar.hide()

        return


class RunningBuildTreeView (gtk.TreeView):
    def __init__ (self):
        gtk.TreeView.__init__ (self)

        # The icon that indicates whether we're building or failed.
        renderer = gtk.CellRendererPixbuf ()
        col = gtk.TreeViewColumn ("Status", renderer)
        col.add_attribute (renderer, "icon-name", 4)
        self.append_column (col)

        # The message of the build.
        renderer = gtk.CellRendererText ()
        col = gtk.TreeViewColumn ("Message", renderer, text=3)
        col.add_attribute(renderer, 'background', 5)
        self.append_column (col)
