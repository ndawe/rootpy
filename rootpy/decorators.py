# Copyright 2012 the rootpy developers
# distributed under the terms of the GNU General Public License
from __future__ import absolute_import

import ROOT
import os
import re
import inspect
import warnings
from .context import preserve_current_directory
from .extern import decorator
from . import gDirectory, ROOT_VERSION


def requires_ROOT(version, exception=False):
    """
    A decorator for functions or methods that require a minimum ROOT version.
    If `exception` is False (the default) a warning is issued and None is
    returned, otherwise a `NotImplementedError` exception is raised. `exception`
    may also be an `Exception` in which case it will be raised instead of
    `NotImplementedError`.
    """
    @decorator.decorator
    def wrap(f, *args, **kwargs):
        if ROOT_VERSION < version:
            msg = "{0} requires at least ROOT {1} but you are using {2}".format(
                f.__name__, version, ROOT_VERSION)
            if inspect.isclass(exception) and issubclass(exception, Exception):
                raise exception
            elif exception:
                raise NotImplementedError(msg)
            warnings.warn(msg)
            return None
        return f(*args, **kwargs)
    return wrap


def _get_qualified_name(thing):

    if inspect.ismodule(thing):
        return thing.__file__
    if inspect.isclass(thing):
        return '%s.%s' % (thing.__module__, thing.__name__)
    if inspect.ismethod(thing):
        return '%s.%s' % (thing.im_class.__name__, thing.__name__)
    if inspect.isfunction(thing):
        return thing.__name__
    return repr(thing)


@decorator.decorator
def method_file_check(f, self, *args, **kwargs):
    """
    A decorator to check that a TFile as been created before f is called.
    This function can decorate methods.
    """
    # This requires special treatment since in Python 3 unbound methods are
    # just functions: http://stackoverflow.com/a/3589335/1002176 but to get
    # consistent access to the class in both 2.x and 3.x, we need self.
    curr_dir = gDirectory()
    if isinstance(curr_dir, ROOT.TROOT):
        raise RuntimeError(
            "You must first create a File before calling %s.%s" % (
            self.__class__.__name__, _get_qualified_name(f)))
    if not curr_dir.IsWritable():
        raise RuntimeError(
            "Calling %s.%s requires that the current File is writable" % (
            self.__class__.__name__, _get_qualified_name(f)))
    return f(self, *args, **kwargs)


@decorator.decorator
def method_file_cd(f, self, *args, **kwargs):
    """
    A decorator to cd back to the original directory where this object was
    created (useful for any calls to TObject.Write).
    This function can decorate methods.
    """
    with preserve_current_directory():
        self.GetDirectory().cd()
        return f(self, *args, **kwargs)


@decorator.decorator
def chainable(f, self, *args, **kwargs):
    """
    Decorator which causes a 'void' function to return self

    Allows chaining of multiple modifier class methods.
    """
    # perform action
    f(self, *args, **kwargs)
    # return reference to class.
    return self
