# Copyright 2012 the rootpy developers
# distributed under the terms of the GNU General Public License
"""
This module handles conversion of ROOT's TFile and contained TTrees into HDF5
format.
"""
from __future__ import absolute_import

import os
import sys
import warnings
from pkg_resources import parse_version

import h5py
from root_numpy import tree2array, RootNumpyUnconvertibleWarning
from numpy.lib import recfunctions

from .io import root_open, TemporaryFile
from . import log; log = log[__name__]
from .extern.progressbar import ProgressBar, Bar, ETA, Percentage
from .extern.six import string_types
from .logger.utils import check_tty

from . import QROOT

__all__ = [
    'tree2hdf5',
    'root2hdf5',
]


def _drop_object_col(rec, warn=True):
    # ignore columns of type `object` since these are not supported
    if rec.dtype.hasobject:
        object_fields = []
        fields = rec.dtype.fields
        for name in rec.dtype.names:
            if fields[name][0].kind == 'O':
                object_fields.append(name)
                if warn:
                    log.warning(
                        "ignoring unsupported object branch '{0}'".format(
                            name))
        # NumPy 1.7.1: TypeError: Cannot change data-type for object array.
        #return rec[non_object_fields]
        if object_fields:
            rec = recfunctions.rec_drop_fields(rec, object_fields)
    return rec


def tree2hdf5(tree, hfile, group=None,
              entries=-1, selection=None,
              show_progress=False,
              **kwargs):
    """
    Convert a TTree into a HDF5 table.

    Parameters
    ----------

    tree : ROOT.TTree
        A ROOT TTree.

    hfile : string or HDF5 File
        A HDF5 file handle or string path to an existing HDF5 file.

    group : string or group instance, optional (default=None)
        Write the table at this location in the HDF5 file.

    entries : int, optional (default=-1)
        The number of entries to read at once while converting a ROOT TTree
        into an HDF5 table. By default read the entire TTree into memory (this
        may not be desired if your TTrees are large).

    selection : string, optional (default=None)
        A ROOT selection expression to be applied on the TTree before
        conversion.

    show_progress : bool, optional (default=False)
        If True, then display and update a progress bar on stdout as the TTree
        is converted.

    kwargs : dict, optional
        Additional keyword arguments passed to the Group.create_dataset()
        method.

    """
    show_progress = show_progress and check_tty(sys.stdout)
    if show_progress:
        widgets = [Percentage(), ' ', Bar(), ' ', ETA()]

    own_h5file = False
    if isinstance(hfile, string_types):
        hfile = h5py.File(hfile, 'w')
        own_h5file = True

    log.info("Converting tree '{0}' with {1:d} entries ...".format(
        tree.GetName(),
        tree.GetEntries()))

    if not group:
        group = hfile
    elif isinstance(group, string_types):
        group = hfile.create_group(group)

    if tree.GetName() in group:
        log.warning(
            "Tree '{0}' already exists "
            "in the output file".format(tree.GetName()))
        return

    total_entries = tree.GetEntries()
    pbar = None
    if show_progress and total_entries > 0:
        pbar = ProgressBar(widgets=widgets, maxval=total_entries)

    if entries <= 0:
        # read the entire tree
        if pbar is not None:
            pbar.start()
        array = tree2array(tree, selection=selection)
        array = _drop_object_col(array)
        dset = group.create_dataset(
            tree.GetName(), array,
            maxshape=[None,] + list(array.shape)[1:],
            **kwargs)
        # flush all pending data
        hfile.flush()
    else:
        # read the tree in chunks
        start = 0
        while start < total_entries or start == 0:
            if start > 0:
                with warnings.catch_warnings():
                    warnings.simplefilter(
                        "ignore",
                        RootNumpyUnconvertibleWarning)
                    array = tree2array(
                        tree,
                        selection=selection,
                        start=start,
                        stop=start + entries)
                array = _drop_object_col(array, warn=False)
                prev_size = dset.shape[0]
                dset.resize(prev_size + array.shape[0], axis=0)
            else:
                array = tree2array(
                    tree,
                    selection=selection,
                    start=start,
                    stop=start + entries)
                array = _drop_object_col(array)
                if pbar is not None:
                    # start after any output from root_numpy
                    pbar.start()
                dset = group.create_dataset(
                    tree.GetName(), array.shape, dtype=array.dtype,
                    maxshape=[None,] + list(array.shape)[1:],
                    **kwargs)
                prev_size = 0
            dset[prev_size:] = array
            start += entries
            if start <= total_entries and pbar is not None:
                pbar.update(start)
            # flush all pending data
            hfile.flush()

    if pbar is not None:
        pbar.finish()

    if own_h5file:
        hfile.close()


def root2hdf5(rfile, hfile, rpath='',
              entries=-1, userfunc=None,
              selection=None,
              show_progress=False,
              ignore_exception=False,
              **kwargs):
    """
    Convert all trees in a ROOT file into HDF5 format.

    Parameters
    ----------

    rfile : string or asrootpy'd ROOT File
        A ROOT File handle or string path to an existing ROOT file.

    hfile : string or an HDF5 File
        An h5py HDF5 File handle or string path to an existing HDF5 file.

    rpath : string, optional (default='')
        Top level path to begin traversal through the ROOT file. By default
        convert everything in and below the root directory.

    entries : int, optional (default=-1)
        The number of entries to read at once while converting a ROOT TTree
        into an HDF5 table. By default read the entire TTree into memory (this
        may not be desired if your TTrees are large).

    userfunc : callable, optional (default=None)
        A function that will be called on every tree and that must return a
        tree or list of trees that will be converted instead of the original
        tree.

    selection : string, optional (default=None)
        A ROOT selection expression to be applied on all trees before
        conversion.

    show_progress : bool, optional (default=False)
        If True, then display and update a progress bar on stdout as each tree
        is converted.

    ignore_exception : bool, optional (default=False)
        If True, then ignore exceptions raised in converting trees and instead
        skip such trees.

    kwargs : dict, optional
        Additional keyword arguments passed to the Group.create_dataset()
        method.

    """
    own_rootfile = False
    if isinstance(rfile, string_types):
        rfile = root_open(rfile)
        own_rootfile = True

    own_h5file = False
    if isinstance(hfile, string_types):
        hfile = h5py.File(hfile, 'w')
        own_h5file = True

    for dirpath, dirnames, treenames in rfile.walk(
            rpath, class_ref=QROOT.TTree):

        # skip directories w/o trees
        if not treenames:
            continue

        treenames.sort()

        group_path = '/' + dirpath
        if group_path == '/':
            group = hfile
        else:
            group = hfile.create_group(group_path)

        ntrees = len(treenames)
        log.info(
            "Will convert {0:d} tree{1} in {2}".format(
                ntrees, 's' if ntrees != 1 else '',
                group_path))

        for treename in treenames:
            input_tree = rfile.Get(os.path.join(dirpath, treename))

            if userfunc is not None:
                tmp_file = TemporaryFile()
                # call user-defined function on tree and get output trees
                log.info("Calling user function on tree '{0}'".format(
                    input_tree.GetName()))
                trees = userfunc(input_tree)

                if not isinstance(trees, list):
                    trees = [trees]

            else:
                trees = [input_tree]
                tmp_file = None

            for tree in trees:
                try:
                    tree2hdf5(tree, hfile, group=group,
                              entries=entries, selection=selection,
                              show_progress=show_progress,
                              **kwargs)
                except Exception as e:
                    if ignore_exception:
                        log.error("Failed to convert tree '{0}': {1}".format(
                            tree.GetName(), str(e)))
                    else:
                        raise

            input_tree.Delete()

            if userfunc is not None:
                for tree in trees:
                    tree.Delete()
                tmp_file.Close()

    if own_h5file:
        hfile.close()
    if own_rootfile:
        rfile.Close()


def main():

    import rootpy
    from rootpy.extern.argparse import (
        ArgumentParser,
        ArgumentDefaultsHelpFormatter, RawTextHelpFormatter)

    class formatter_class(ArgumentDefaultsHelpFormatter,
                          RawTextHelpFormatter):
        pass

    parser = ArgumentParser(formatter_class=formatter_class,
        description="Convert ROOT files containing TTrees into HDF5 files")
    parser.add_argument('--version', action='version',
                        version=rootpy.__version__,
                        help="show the version number and exit")
    parser.add_argument('-n', '--entries', type=int, default=100000,
                        help="number of entries to read at once")
    parser.add_argument('-f', '--force', action='store_true', default=False,
                        help="overwrite existing output files")
    parser.add_argument('-u', '--update', action='store_true', default=False,
                        help="update existing output files")
    parser.add_argument('--ext', default='h5',
                        help="output file extension")
    parser.add_argument('-c', '--complevel', type=int, default=5,
                        choices=range(0, 10),
                        help="compression level")
    parser.add_argument('-l', '--complib', default=None,
                        choices=('none', 'gzip', 'lzf', 'szip'),
                        help="compression algorithm")
    parser.add_argument('-s', '--selection', default=None,
                        help="apply a selection on each "
                             "tree with a cut expression")
    parser.add_argument(
        '--script', default=None,
        help="Python script containing a function with the same name \n"
             "that will be called on each tree and must return a tree or \n"
             "list of trees that will be converted instead of the \n"
             "original tree")
    parser.add_argument('-q', '--quiet', action='store_true', default=False,
                        help="suppress all warnings")
    parser.add_argument('-d', '--debug', action='store_true', default=False,
                        help="show stack trace in the event of "
                             "an uncaught exception")
    parser.add_argument('--no-progress-bar', action='store_true', default=False,
                        help="do not show the progress bar")
    parser.add_argument('--ignore-exception', action='store_true',
                        default=False,
                        help="ignore exceptions raised in converting trees "
                             "and instead skip such trees")
    parser.add_argument('files', nargs='+')
    args = parser.parse_args()

    rootpy.log.basic_config_colorized()
    import logging
    if hasattr(logging, 'captureWarnings'):
        logging.captureWarnings(True)

    def formatwarning(message, category, filename, lineno, line=None):
        return "{0}: {1}".format(category.__name__, message)

    warnings.formatwarning = formatwarning
    args.ext = args.ext.strip('.')

    if args.quiet:
        warnings.simplefilter(
            "ignore",
            RootNumpyUnconvertibleWarning)

    userfunc = None
    if args.script is not None:
        # get user-defined function
        try:
            exec(compile(open(args.script).read(), args.script, 'exec'),
                 globals(), locals())
        except IOError:
            sys.exit('Could not open script {0}'.format(args.script))
        funcname = os.path.splitext(os.path.basename(args.script))[0]
        try:
            userfunc = locals()[funcname]
        except KeyError:
            sys.exit(
                "Could not find the function '{0}' in the script {1}".format(
                    funcname, args.script))

    kwargs = {}
    if args.complib:
        kwargs['compression'] = args.complib
        if args.complib == 'gzip':
            kwargs['compression_opts'] = args.complevel

    for inputname in args.files:
        outputname = os.path.splitext(inputname)[0] + '.' + args.ext
        output_exists = os.path.exists(outputname)
        if output_exists and not (args.force or args.update):
            sys.exit(
                "Output {0} already exists. "
                "Use the --force option to overwrite it".format(outputname))
        try:
            rootfile = root_open(inputname)
        except IOError:
            sys.exit("Could not open {0}".format(inputname))
        try:
            hd5file = h5py.File(outputname, 'a' if args.update else 'w')
        except IOError:
            sys.exit("Could not create {0}".format(outputname))
        try:
            log.info("Converting {0} ...".format(inputname))
            root2hdf5(rootfile, hd5file,
                      entries=args.entries,
                      userfunc=userfunc,
                      selection=args.selection,
                      show_progress=not args.no_progress_bar,
                      ignore_exception=args.ignore_exception,
                      **kwargs)
            log.info("{0} {1}".format(
                "Updated" if output_exists and args.update else "Created",
                outputname))
        except KeyboardInterrupt:
            log.info("Caught Ctrl-c ... cleaning up")
            hd5file.close()
            rootfile.Close()
            if not output_exists:
                log.info("Removing {0}".format(outputname))
                os.unlink(outputname)
            sys.exit(1)
        except Exception as e:
            if args.debug:
                # If in debug mode show full stack trace
                import traceback
                traceback.print_exception(*sys.exc_info())
            log.error(str(e))
            sys.exit(1)
        finally:
            hd5file.close()
            rootfile.Close()
