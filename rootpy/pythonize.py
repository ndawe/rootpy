import inspect
import re
import os
import imp
import keyword

from . import log; log = log[__name__]
from .util.cpp import CPPGrammar
from .util.extras import camel_to_snake
from . import userdata, ROOTError
from .extern.lockfile import LockFile


__all__ = [
    'ROOTDescriptor',
    'ROOTStaticDescriptor',
    'pythonized',
]


DESCRIPTOR_PATTERN = re.compile('^(?P<access>([sS]|[gG])et)(?P<prop>.+)$')
CONVERT_SNAKE_CASE = os.getenv('NO_ROOTPY_SNAKE_CASE', False) == False
SOURCE_PATH = os.path.join(userdata.BINARY_PATH, 'source')
if not os.path.exists(SOURCE_PATH):
    os.makedirs(SOURCE_PATH)


class ROOTDescriptor(object):

    def __init__(self, root_setter, root_getter):

        self.root_setter = root_setter
        self.root_getter = root_getter

    def __get__(self, instance, owner):

        return self.root_getter(instance)

    def __set__(self, instance, value):

        self.root_setter(instance, value)


class ROOTStaticDescriptor(ROOTDescriptor):

    def __get__(self, instance, owner):

        return self.root_getter()

    def __set__(self, instance, value):

        self.root_setter(value)


def check_name(cls, name):

    llog = log['check_name']
    llog.debug('{0}.{1}'.format(cls.__name__, name))
    # hasattr(TMemFile, 'flush')
    # Error in <TClass::BuildRealData>: Cannot find any ShowMembers
    # function for G__CINT_FLUSH!
    if name == 'flush':
        return False
    """ This check is slow!
    if hasattr(cls, name):
        llog.debug("{0} is already a member of {1}".format(
            name, cls.__name__))
        return False
    """
    if keyword.iskeyword(name):
        llog.debug("{0} is a python keyword".format(name))
        return False
    return True



class SnakeMethods(object):

    def __init__(self, inherited=False):
        self.inherited = inherited

    @staticmethod
    def get_snake_names(cls, methods=None, inherited=False):

        if not CONVERT_SNAKE_CASE:
            return []
        if methods is None:
            if inherited:
                methods = inspect.getmembers(cls, predicate=inspect.ismethod)
            else:
                methods = [
                    (name, thing) for (name, thing) in cls.__dict__
                        if inspect.ismethod(thing)]

        # filter out any methods that already exist in lower and uppercase forms
        # i.e. TDirectory::cd and Cd...
        names = [name.capitalize() for (name, method) in methods]
        duplicate_idx = set()
        seen = []
        for i, n in enumerate(names):
            try:
                idx = seen.index(n)
                duplicate_idx.add(i)
                duplicate_idx.add(idx)
            except ValueError:
                seen.append(n)
        names = []
        for i, (name, method) in enumerate(methods):
            if i in duplicate_idx:
                continue
            # Don't touch special methods or methods without cap letters
            if name[0] == '_' or name.islower():
                continue
            # convert CamelCase to snake_case
            snake_name = camel_to_snake(name)
            if not check_name(cls, snake_name):
                continue
            names.append((name, snake_name))
        return names

    def __call__(self, cls):
        """
        A class decorator adding snake_case methods
        that alias capitalized ROOT methods
        """
        llog = log['snake_methods']
        names = SnakeMethods.get_snake_names(cls, inherited=self.inherited)
        for name, snake_name in names:
            llog.debug("{0} -> {1}".format(name, snake_name))

            # Use a __dict__ lookup rather than getattr because we _want_ to
            # obtain the _descriptor_, and not what the descriptor gives us when
            # it is `getattr`'d.
            value = None
            for c in inspect.getmro(cls):
                if name in c.__dict__:
                    value = c.__dict__[name]
                    break
            # <neo>Woah, a use for for-else</neo>
            else:
                # Weird. Maybe the item lives somewhere else, such as on the
                # metaclass?
                value = getattr(cls, name)

            setattr(cls, snake_name, value)

    def snake_methods(self, base_cls, methods, cls_proxy):

        llog = log['snake_methods']
        names = SnakeMethods.get_snake_names(base_cls, inherited=self.inherited)
        for name, snake_name in names:
            cls_proxy.attrs.append(
                Attribute(snake_name, '{0}.{1}'.format(
                    base_cls.__name__, name)))


def descriptors(base_cls, methods, cls_proxy):

    llog = log['descriptors']
    setters = dict()
    getters = dict()
    for name, thing in methods:
        desc_match = re.match(DESCRIPTOR_PATTERN, name)
        if not desc_match:
            continue
        doc = getattr(thing, 'func_doc', None)
        if doc is None:
            continue
        sig = CPPGrammar.parse_method(doc)
        if not sig:
            continue
        if desc_match.group('access')[0].upper() == 'S':
            if sig['return'] != 'void':
                continue
            setters[desc_match.group('prop')] = (thing, sig[0] == 'static')
        elif desc_match.group('access')[0].upper() == 'G':
            if sig['return'] == 'void':
                continue
            getters[desc_match.group('prop')] = (thing, sig[0] == 'static')
    for name in setters:
        if name not in getters:
            llog.debug(
                "Set{0} does not have an associated Get{0}".format(name))
            continue
        setter, setter_static = setters[name]
        getter, getter_static = getters[name]
        if setter_static != getter_static:
            llog.debug("only one of Set{0} and Get{0} is static".format(name))
            continue
        snake_name = camel_to_snake(name)
        llog.debug('creating {0}descriptor `{1}`'.format(
            'static ' if setter_static else '', snake_name))
        if not check_name(base_cls, snake_name):
            continue
        desc_cls = 'ROOTStaticDescriptor' if setter_static else 'ROOTDescriptor'
        cls_proxy.attrs.append(
            Attribute(
                snake_name,
                '{0}({1}.{2}, {1}.{3})'.format(
                    desc_cls, base_cls.__name__,
                    setter.__name__, getter.__name__)))


class Argument(object):

    def __init__(self, name, value=None):
        self.name = name
        self.value = value

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        if self.value is not None:
            return '{0}={1}'.format(self.name, self.value)
        return self.name


class Method(object):

    TEMPLATE = '''\
    def {0}({1}):
        {2}
    '''

    def __init__(self, name, args, body):
        self.name = name
        self.args = args
        self.body = body

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return self.TEMPLATE.format(self.name,
            ', '.join(map(str, self.args)))


class Attribute(object):

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return '    {0} = {1}'.format(self.name, self.value)


class Class(object):

    TEMPLATE = '''\
from rootpy.pythonize import ROOTDescriptor, ROOTStaticDescriptor
from rootpy import asrootpy, QROOT

{0} = QROOT.{0}

class {1}({0}):
{2}
    '''

    def __init__(self, name, base):
        self.name = name
        self.base = base
        self.attrs = []

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return self.TEMPLATE.format(self.base, self.name,
            '\n'.join(map(str, self.attrs)))


def pythonized(cls):
    """
    Write out a pythonized subclass of `cls` to the file `cls.__name__`.py if
    this class has not yet been pythonized, otherwise import the existing
    pythonized class.

    Returns
    -------
    pythonized_cls: the pythonized class
    """
    cls_name = cls.__name__
    out_name = os.path.join(SOURCE_PATH, '{0}.py'.format(cls_name))
    subcls_name = '{0}_pythonized'.format(cls_name)
    with LockFile(os.path.join(SOURCE_PATH, "lock")):
        if not os.path.isfile(out_name):
            # create new pythonized class
            log.info("generating pythonized subclass of `{0}`".format(cls_name))
            try:
                with open(out_name, 'w') as out_file:
                    subcls_src = Class(subcls_name, cls_name)
                    methods = inspect.getmembers(cls, predicate=inspect.ismethod)
                    descriptors(cls, methods, subcls_src)
                    SnakeMethods(True).snake_methods(cls, methods, subcls_src)
                    out_file.write(str(subcls_src))
            except:
                os.unlink(out_name)
                raise
    # import existing file and get the class
    log.debug(
        "using existing pythonized subclass of `{0}`".format(cls_name))
    modhandle = imp.load_source('ROOT_pythonized', out_name)
    return getattr(modhandle, subcls_name)
