# Copyright 2012 the rootpy developers
# distributed under the terms of the GNU General Public License
import ROOT
from rootpy.core import Object
from rootpy.decorators import method_file_check, method_file_cd
from rootpy.io import TemporaryFile
import rootpy
from nose.tools import assert_equal, assert_true, raises


class Foo(Object, ROOT.TH1D):

    @method_file_check
    def something(self, foo):
        self.file = rootpy.gDirectory()
        return foo

    @method_file_cd
    def write(self):
        assert_true(self.GetDirectory() == rootpy.gDirectory())


def test_method_file_check_good():

    foo = Foo()
    with TemporaryFile():
        foo.something(42)


@raises(RuntimeError)
def test_method_file_check_bad():

    foo = Foo()
    foo.something(42)


def test_method_file_cd():

    file1 = TemporaryFile()
    foo = Foo()
    foo.SetDirectory(file1)
    file2 = TemporaryFile()
    foo.write()


if __name__ == "__main__":
    import nose
    nose.runmodule()
