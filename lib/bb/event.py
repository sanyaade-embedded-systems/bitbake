# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-
"""
BitBake 'Event' implementation

Classes and functions for manipulating 'events' in the
BitBake build tools.
"""

# Copyright (C) 2003, 2004  Chris Larson
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


import copy
import logging
try:
    import cPickle as pickle
except ImportError:
    import pickle
import warnings
import bb.utils


logger = logging.getLogger('BitBake.Event')


class EventDispatcher(object):
    """Class to manage firing of and handling of events"""

    def __init__(self):
        self.handlers = []

    @classmethod
    def compile(cls, code):
        context = {}
        defined = 'def _handler(e):\n{0}'.format(code)
        bb.utils.better_exec(defined, context, defined)
        return bb.utils.better_eval('_handler', context)

    def register(self, handler):
        if isinstance(handler, basestring):
            handler = self.compile(handler)
        self.handlers.append(handler)

    def unregister(self, handler):
        self.handlers.remove(handler)

    def fire(self, event):
        for handler in self.handlers:
            logger.info('%s: handling %s with %s', self, event, handler)
            handler(event)

    def __len__(self):
        return len(self.handlers)

    def __contains__(self, handler):
        if isinstance(handler, basestring):
            handler = self.compile(handler)
        return handler in self.handlers

    def __iadd__(self, other):
        return self.register(other)

    def __isub__(self, other):
        return self.unregister(other)

    def __call__(self, event):
        return self.fire(event)

class MetadataDispatcher(EventDispatcher):
    def register_metadata_handlers(self, metadata):
        mdhandler = _MetadataHandler(metadata)
        for var in bb.data.getVar('__BBHANDLERS', metadata) or []:
            value = metadata.getVar(var, True)
            if value:
                mdhandler.register(value)

        self.register(mdhandler)
        return mdhandler

class _MetadataHandler(EventDispatcher):
    """Class to fire events in a particular way for handling by the metadata

    This class injects the metadata at fire-time, so that it can be used
    to run the event handlers in the metadata.
    """
    def __init__(self, metadata):
        self.metadata = metadata
        EventDispatcher.__init__(self)

    def fire(self, event):
        logger.info("%s: handling %s", self, event)
        event = copy.copy(event)
        event.data = self.metadata
        EventDispatcher.fire(self, event)

class ChainedHandler(object):
    def __init__(self, dispatcher):
        self.dispatcher = dispatcher

    def __call__(self, event):
        logger.info("%s: handling %s", self, event)
        self.dispatcher.fire(event)

class PipeHandler(object):
    """Event handler which dispatches events over a pipe"""

    def __init__(self, pipe):
        self.pipe = pipe

    def __call__(self, event):
        logger.info("%s: handling %s", self, event)
        try:
            pickle.dump(event, self.pipe)
        except Exception as exc:
            logger.fatal('Failed to send %s event: %s', event, exc)

class QueueHandler(object):
    """Event handler which dispatches events over a Queue"""

    def __init__(self, queue):
        self.queue = queue

    def __call__(self, event):
        logger.info("%s: handling %s", self, event)
        try:
            pickle.dumps(event)
        except Exception as exc:
            logger.fatal("Unable to pickle event %s: %s", event, exc)

        self.queue.put(event)

class LogHandler(logging.Handler):
    """Dispatch logging messages as bitbake events"""

    def __init__(self, dispatcher):
        self.dispatcher = dispatcher

    def emit(self, record):
        self.dispatcher.fire(record)

class Event(object):
    pass

class ConfigParsed(Event):
    pass

class RecipeParsed(Event):
    def __init__(self, fn):
        self.fn = fn
        Event.__init__(self)

class StampUpdate(Event):
    """Trigger for any adjustment of the stamp files to happen"""

    def __init__(self, targets, stampfns):
        self._targets = targets
        self._stampfns = stampfns
        Event.__init__(self)

    def getStampPrefix(self):
        return self._stampfns

    def getTargets(self):
        return self._targets

    stampPrefix = property(getStampPrefix)
    targets = property(getTargets)

class BuildBase(Event):
    def __init__(self, n, p, failures = 0):
        self._name = n
        self._pkgs = p
        Event.__init__(self)
        self._failures = failures

    def getPkgs(self):
        return self._pkgs

    def setPkgs(self, pkgs):
        self._pkgs = pkgs

    def getName(self):
        return self._name

    def setName(self, name):
        self._name = name

    def getCfg(self):
        return self.data

    def setCfg(self, cfg):
        self.data = cfg

    def getFailures(self):
        return self._failures

    pkgs = property(getPkgs, setPkgs, None, "pkgs property")
    name = property(getName, setName, None, "name property")
    cfg = property(getCfg, setCfg, None, "cfg property")

class BuildStarted(BuildBase):
    pass

class BuildCompleted(BuildBase):
    pass

class NoProvider(Event):
    def __init__(self, item, runtime=False, dependees=None):
        Event.__init__(self)
        self._item = item
        self._runtime = runtime
        self._dependees = dependees

    def getItem(self):
        return self._item

    def isRuntime(self):
        return self._runtime

class MultipleProviders(Event):
    def  __init__(self, item, candidates, runtime = False):
        Event.__init__(self)
        self._item = item
        self._candidates = candidates
        self._is_runtime = runtime

    def isRuntime(self):
        return self._is_runtime

    def getItem(self):
        return self._item

    def getCandidates(self):
        return self._candidates

class ParseStarted(Event):
    def __init__(self, total):
        Event.__init__(self)
        self.total = total

class ParseCompleted(Event):
    def __init__(self, cached, parsed, skipped, masked, virtuals, errors, total):
        Event.__init__(self)
        self.cached = cached
        self.parsed = parsed
        self.skipped = skipped
        self.virtuals = virtuals
        self.masked = masked
        self.errors = errors
        self.sofar = cached + parsed
        self.total = total

class ParseProgress(Event):
    def __init__(self, current):
        self.current = current

class CacheLoadStarted(Event):
    def __init__(self, total):
        Event.__init__(self)
        self.total = total

class CacheLoadProgress(Event):
    def __init__(self, current):
        Event.__init__(self)
        self.current = current

class CacheLoadCompleted(Event):
    def __init__(self, total, num_entries):
        Event.__init__(self)
        self.total = total
        self.num_entries = num_entries

class DepTreeGenerated(Event):
    def __init__(self, depgraph):
        Event.__init__(self)
        self._depgraph = depgraph


# Deprecated events
class MsgBase(Event):
    def __init__(self, msg):
        self._message = msg
        Event.__init__(self)

class MsgDebug(MsgBase):
    pass

class MsgNote(MsgBase):
    pass

class MsgWarn(MsgBase):
    pass

class MsgError(MsgBase):
    pass

class MsgFatal(MsgBase):
    pass

class MsgPlain(MsgBase):
    pass


def getName(event):
    warnings.warn('bb.event.getName will soon be deprecated',
                  PendingDeprecationWarning, stacklevel=2)
    return event.__class__.__name__
