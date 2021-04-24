#!/usr/bin/env python3
# --------------------( LICENSE                           )--------------------
# Copyright (c) 2014-2021 Beartype authors.
# See "LICENSE" for further details.

'''
**Beartype** `PEP 593`_-compliant :class:`typing.Annotated` **type hint
exception raisers** (i.e., functions raising human-readable exceptions called
by :mod:`beartype`-decorated callables on the first invalid parameter or return
value failing a type-check against the `PEP 593`_-compliant
:class:`typing.Annotated` type hint annotating that parameter or return).

This private submodule is *not* intended for importation by downstream callers.

.. _PEP 593:
   https://www.python.org/dev/peps/pep-0593
'''

# ....................{ IMPORTS                           }....................
from beartype.roar._roarexc import _BeartypeCallHintPepRaiseException
from beartype.vale._valeissub import SubscriptedIs
from beartype._decor._code._pep._error._peperrortype import (
    get_cause_or_none_type)
from beartype._decor._code._pep._error._peperrorsleuth import CauseSleuth
from beartype._util.hint.data.pep.utilhintdatapepsign import (
    HINT_PEP593_SIGN_ANNOTATED)
from beartype._util.hint.pep.proposal.utilhintpep593 import (
    get_hint_pep593_metadata,
    get_hint_pep593_type,
)
from beartype._util.text.utiltextcause import get_cause_object_representation
from typing import Optional

# See the "beartype.cave" submodule for further commentary.
__all__ = ['STAR_IMPORTS_CONSIDERED_HARMFUL']

# ....................{ GETTERS                           }....................
def get_cause_or_none_annotated(sleuth: CauseSleuth) -> Optional[str]:
    '''
    Human-readable string describing the failure of the passed arbitrary object
    to satisfy the passed `PEP 593`_-compliant :mod:`beartype`-specific
    **metahint** (i.e., type hint annotating a standard class with one or more
    :class:`SubscriptedIs` objects, each produced by subscripting the
    :class:`beartype.vale.Is` class or a subclass of that class) if this object
    actually fails to satisfy this hint *or* ``None`` otherwise (i.e., if this
    object satisfies this hint).

    Parameters
    ----------
    sleuth : CauseSleuth
        Type-checking error cause sleuth.

    .. _PEP 593:
       https://www.python.org/dev/peps/pep-0593
    '''
    assert isinstance(sleuth, CauseSleuth), f'{repr(sleuth)} not cause sleuth.'
    assert sleuth.hint_sign is HINT_PEP593_SIGN_ANNOTATED, (
        f'{repr(sleuth.hint_sign)} not annotated.')

    # Non-"typing" class annotated by this metahint.
    hint_annotated = get_hint_pep593_type(sleuth.hint)

    # If this pith is *NOT* an instance of this class, defer to the getter
    # handling non-"typing" classes.
    if not isinstance(sleuth.pith, hint_annotated):
        return get_cause_or_none_type(sleuth.permute(hint=hint_annotated))
    # Else, this pith is an instance of that class.

    # For each arbitrary object annotating that class...
    for hint_metadatum in get_hint_pep593_metadata(sleuth.hint):
        # If this object is *NOT* beartype-specific, raise an exception.
        #
        # Note that this object should already be beartype-specific, as the
        # @beartype decorator enforces this constraint at decoration time.
        if not isinstance(hint_metadatum, SubscriptedIs):
            raise _BeartypeCallHintPepRaiseException(
                f'{sleuth.exception_label} PEP 593 type hint '
                f'{repr(sleuth.hint)} argument {repr(hint_metadatum)} not '
                f'not subscription of "beartype.vale.Is*" class.'
            )
        # Else, this object is beartype-specific.

        # If this pith fails to satisfy this validator and is thus the cause of
        # this failure, return this cause.
        if not hint_metadatum.is_valid(sleuth.pith):
            return (
                f'{get_cause_object_representation(sleuth.pith)} violates '
                f'data constraint {repr(hint_metadatum)}.'
            )
        # Else, this pith satisfies this data validator. Ergo, this validator
        # *NOT* the cause of this failure. Silently continue to the next.

    # Return "None", as this pith satisfies both this non-"typing" class itself
    # *AND* all data validators annotating that class, implying this pith to
    # deeply satisfy this metahint.
    return None
