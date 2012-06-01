from __future__ import absolute_import

import abc

from traits.api import Bool, Instance
from enaml.components.control import Control, AbstractTkControl

from .neighbor_lookup_mixin import NeighborLookupMixin

class AbstractTkSpinner(AbstractTkControl):
    """ The abstract toolkit spinner
    """

    @abc.abstractmethod
    def shell_spinning_changed(self):
        """ The change handler for the 'spinning' attribute on the shell
        component.

        """
        raise NotImplementedError

class Spinner(Control, NeighborLookupMixin):
    """ The Enaml spinner widget
    """
    # Overriden parent class traits
    abstract_obj = Instance(AbstractTkSpinner)

    spinning = Bool

    hug_width = 'required'
    hug_height = 'required'

