# Copyright 2012 the rootpy developers
# distributed under the terms of the GNU General Public License
from rootpy.pythonize import pythonized
from nose.tools import assert_equal, assert_true


def test_snake_case_methods():

    class A(object):
        def SomeMethod(self): pass
        def some_method(self): pass
        def OtherMethod(self): pass
        def Write(self): pass
        def Cd(self): pass
        def cd(self): pass
        def LongMethodName(self): pass

    class B(A):
        def write(self): pass

    B = pythonized(B)

    assert_true(hasattr(B, 'some_method'))
    assert_true(hasattr(B, 'cd'))
    assert_true(hasattr(B, 'long_method_name'))
    assert_true(hasattr(B, 'write'))
    assert_true(hasattr(B, 'other_method'))


def test_snake_case_methods_descriptor():

    def f(_): pass

    class A(object):
        Prop = property(f)
        Sm = staticmethod(f)
        Cm = classmethod(f)
        M = f

    class B(A):
        cm = A.__dict__["Cm"]
        m = A.__dict__["M"]
        prop = A.__dict__["Prop"]
        sm = A.__dict__["Sm"]

    snakeB = pythonized(A)

    # Ensure that no accidental descriptor dereferences happened inside
    # `snake_case_methods`. This is checked by making sure that the types
    # are the same between B and snakeB.

    for member in dir(snakeB):
        if member.startswith("_"): continue
        assert_equal(type(getattr(B, member)), type(getattr(snakeB, member)))


if __name__ == "__main__":
    import nose
    nose.runmodule()
