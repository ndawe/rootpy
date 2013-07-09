import inspect
import re
import os
import imp

from . import log; log = log[__name__]
from .util.cpp import CPPGrammar
from .util.extras import camel_to_snake

__all__ = [
    'ROOTDescriptor',
    'ROOTStaticDescriptor',
    'pythonize',
]


DESCRIPTOR_PATTERN = re.compile('^(?P<access>([sS]|[gG])et)(?P<prop>.+)$')


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


def autoprops(cls, cls_proxy):

    setters = dict()
    getters = dict()
    for name, thing in inspect.getmembers(cls):
        if not inspect.ismethod(thing):
            continue
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
            log.warning(
                "Set{0} does not have an associated Get{0}".format(name))
            continue
        setter, setter_static = setters[name]
        getter, getter_static = getters[name]
        if setter_static != getter_static:
            log.warning("only one of Set{0} and Get{0} is static".format(name))
            continue
        snake_name = camel_to_snake(name)
        log.debug('creating {0}descriptor `{1}`'.format(
            'static ' if setter_static else '', snake_name))
        desc_cls = 'ROOTStaticDescriptor' if setter_static else 'ROOTDescriptor'
        cls_proxy.attrs.append(
            Attribute(
                snake_name,
                '{0}(ROOT_CLS.{1}, ROOT_CLS.{2})'.format(
                    desc_cls, setter.__name__, getter.__name__)))


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

ROOT_CLS = QROOT.{0}

class {1}(ROOT_CLS):
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


def pythonize(cls):
    """
    Write out a pythonized subclass of `cls` to the file `cls.__name__`.py if
    this class has not yet been pythonized, otherwise import the existing
    pythonized class.

    Returns
    -------
    pythonized_cls: the pythonized class
    """
    cls_name = cls.__name__
    out_name = '{0}.py'.format(cls_name)
    subcls_name = '{0}_pythonized'.format(cls_name)
    if not os.path.isfile(out_name):
        # create new pythonized class
        log.info("generating pythonized subclass of `{0}`".format(cls_name))
        with open(out_name, 'w') as out_file:
            subcls_src = Class(subcls_name, cls_name)
            autoprops(cls, subcls_src)
            out_file.write(str(subcls_src))
    # import existing file and get the class
    log.debug(
        "using existing pythonized subclass of `{0}`".format(cls_name))
    modhandle = imp.load_source('ROOT_pythonized', out_name)
    return getattr(modhandle, subcls_name)
