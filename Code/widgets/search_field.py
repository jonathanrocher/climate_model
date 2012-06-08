from __future__ import absolute_import

import abc 

from traits.api import Bool, Instance
from enaml.components.control import Control, AbstractTkControl

from .neighbor_lookup_mixin import NeighborLookupMixin

class AbstractTkSearchField(AbstractTkControl):
    """ The abstract search field widget
    """

    #@abc.abstractmethod
    #def shell_something_changed(self):
    #    pass

class SearchField(Control, NeighborLookupMixin):
    """ The Enaml search field widget
    """
    # Overriden parent class traits
    abstract_obj = Instance(AbstractTkSearchField)

    hug_width = 'ignore'

