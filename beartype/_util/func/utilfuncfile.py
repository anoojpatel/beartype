#!/usr/bin/env python3
# --------------------( LICENSE                            )--------------------
# Copyright (c) 2014-2024 Beartype authors.
# See "LICENSE" for further details.

'''
Project-wide **callable origin** (i.e., uncompiled source from which a compiled
callable originated) utilities.

This private submodule implements supplementary callable-specific utility
functions required by various :mod:`beartype` facilities, including callables
generated by the :func:`beartype.beartype` decorator.

This private submodule is *not* intended for importation by downstream callers.
'''

# ....................{ TODO                               }....................
#FIXME: *FILE UPSTREAM CPYTHON ISSUES.* Unfortunately, this submodule exposed a
#number of significant issues in the CPython stdlib -- all concerning parsing
#of lambda functions. These include:
#
#1. The inspect.getsourcelines() function raises unexpected
#   "tokenize.TokenError" exceptions when passed lambda functions preceded by
#   one or more triple-quoted strings: e.g.,
#       >>> import inspect
#       >>> built_to_fail = (
#       ...     ('''Uh-oh.
#       ... ''', lambda obj: 'Oh, Gods above and/or below!'
#       ...     )
#       ... )
#       >>> inspect.getsourcelines(built_to_fail[1])}
#       tokenize.TokenError: ('EOF in multi-line string', (323, 8))
#FIXME: Contribute get_func_code_or_none() back to this StackOverflow question
#as a new answer, as this is highly non-trivial, frankly:
#    https://stackoverflow.com/questions/59498679/how-can-i-get-exactly-the-code-of-a-lambda-function-in-python/64421174#64421174

# ....................{ IMPORTS                            }....................
from beartype.typing import Optional
from beartype._util.func.utilfunccodeobj import get_func_codeobj_or_none
from collections.abc import Callable
from linecache import cache as linecache_cache

# ....................{ TESTERS                            }....................
def is_func_file(func: Callable) -> bool:
    '''
    :data:`True` only if the passed callable is defined **on-disk** (e.g., by a
    script or module whose pure-Python source code is accessible to the active
    Python interpreter as a file on the local filesystem).

    Equivalently, this tester returns :data:`False` if that callable is
    dynamically defined in-memory (e.g., by a prior call to the :func:`exec` or
    :func:`eval` builtins).

    Parameters
    ----------
    func : Callable
        Callable to be inspected.

    Returns
    ----------
    bool
        :data:`True` only if the passed callable is defined on-disk.
    '''

    # One-liners for abstruse abstraction.
    return get_func_filename_or_none(func) is not None

# ....................{ GETTERS                            }....................
def get_func_filename_or_none(
    # Mandatory parameters.
    func: Callable,

    # Optional parameters.
    # exception_cls: TypeException = _BeartypeUtilCallableException,
) -> Optional[str]:
    '''
    Absolute filename of the file on the local filesystem containing the
    pure-Python source code for the script or module defining the passed
    callable if that callable is defined on-disk *or* :data:`None` otherwise
    (i.e., if that callable is dynamically defined in-memory by a prior call to
    the :func:`exec` or :func:`eval` builtins).

    Parameters
    ----------
    func : Callable
        Callable to be inspected.

    Returns
    ----------
    Optional[str]
        Either:

        * If that callable was physically declared by a file, the absolute
          filename of that file.
        * If that callable was dynamically declared in-memory, :data:`None`.
    '''

    # Code object underlying the passed callable if that callable is pure-Python
    # *OR* "None" otherwise (i.e., if that callable is C-based).
    #
    # Note that we intentionally do *NOT* test whether this callable is
    # explicitly pure-Python or C-based: e.g.,
    #     # If this callable is implemented in C, this callable has no code
    #     # object with which to inspect the filename declaring this callable.
    #     # In this case, defer to a C-specific placeholder string.
    #     if isinstance(func, CallableCTypes):
    #         func_origin_label = '<C-based>'
    #     # Else, this callable is implemented in Python. In this case...
    #     else:
    #         # If this callable is a bound method wrapping an unbound function,
    #         # unwrap this method into the function it wraps. Why? Because only
    #         # the latter provides the code object for this callable.
    #         if isinstance(func, MethodBoundInstanceOrClassType):
    #             func = func.__func__
    #
    #         # Defer to the absolute filename of the Python file declaring this
    #         # callable, dynamically retrieved from this callable's code object.
    #         func_origin_label = func.__code__.co_filename
    #
    # Why? Because PyPy. The logic above succeeds for CPython but fails for
    # PyPy, because *ALL CALLABLES ARE C-BASED IN PYPY.* Adopting the above
    # approach would unconditionally return the C-specific placeholder string
    # for all callables -- including those originally declared as pure-Python in
    # a Python module. So it goes.
    func_codeobj = get_func_codeobj_or_none(func)

    # If the passed callable has *NO* code object and is thus *NOT* pure-Python,
    # that callable was *NOT* defined by a pure-Python source code file. In this
    # case, return "None".
    if not func_codeobj:
        return None
    # Else, that callable is pure-Python.

    # Absolute filename of the pure-Python source code file defining that
    # callable if this code object offers that metadata *OR* "None" otherwise.
    #
    # Note that we intentionally do *NOT* assume all code objects to offer this
    # metadata (e.g., by unconditionally returning "func_codeobj.co_filename").
    # Why? Because PyPy yet again. For inexplicable reasons, PyPy provides
    # *ALL* C-based builtins (e.g., len()) with code objects failing to provide
    # this metadata. Yes, this is awful. Yes, this is the Python ecosystem.
    func_filename = getattr(func_codeobj, 'co_filename', None)

    # If either this code object does not provide this filename *OR*...
    if not func_filename or (
        # This filename is a "<"- and ">"-bracketed placeholder string, this
        # filename is a placeholder signifying this callable to be dynamically
        # declared in-memory rather than by an on-disk module. Examples include:
        # * "<string>", signifying a callable dynamically declared in-memory.
        # * "<@beartype(...) at 0x...}>', signifying a callable dynamically
        #   declared in-memory by the
        #   beartype._util.func.utilfuncmake.make_func() function, possibly
        #   cached with the standard "linecache" module.
        func_filename[ 0] == '<' and
        func_filename[-1] == '>' and
        # This in-memory callable's source code was *NOT* cached with the
        # "linecache" module and has thus effectively been destroyed.
        func_filename not in linecache_cache
    # Then return "None", as this filename is useless for almost all purposes.
    ):
        return None
    # Else, this filename is either:
    # * That of an on-disk module, which is good.
    # * That of an in-memory callable whose source code was cached with the
    #   "linecache" module. Although less good, this filename *CAN* technically
    #   be used to recover this code by querying the "linecache" module.

    # Return this filename as is, regardless of whether this file exists.
    # Callers are responsible for performing further validation if desired.
    # print(f'func_filename: {func_filename}')
    return func_filename
