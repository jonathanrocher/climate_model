""" Mixin to make Component classes adhere to the EnamlFactory
interface.
"""

from enaml.core.toolkit import Toolkit
from enaml.core.base_component import BaseComponent


class NeighborLookupMixin(object):
    """ Mixin to provide an EnamlFactory interface for BaseComponent
    subclasses.

    Note that the classes themselves obey the interface, not instances
    of them.

    The semantics are as follows:

        * Find the current toolkit's prefixes, i.e. for the Qt
          implementation of the Foo component, the toolkit
          implementation will be in the file named qt_foo.py and the
          class will be named QtFoo.
        * The implementation modules will be found *next* to the module
          providing the Component class.
    """

    @classmethod
    def __enaml_call__(cls, identifiers=None, toolkit=None):
        """ Instantiate the shell class and load its abstract object.
        """
        if identifiers is None:
            identifiers = {}
        if toolkit is None:
            toolkit = Toolkit.active_toolkit()
        # Look up the toolkit prefixes.
        file_prefix, class_prefix = cls.__get_toolkit_prefixes(toolkit)
        shell_obj = cls()
        abstract_obj = cls.__load_abstract_obj(file_prefix, class_prefix)
        shell_obj.abstract_obj = abstract_obj
        abstract_obj.shell_obj = shell_obj
        shell_obj.toolkit = toolkit
        shell_obj._bases.insert(0, cls)
        return shell_obj

    @classmethod
    def __get_toolkit_prefixes(cls, toolkit):
        """ Return the file prefix and the class prefix for the given
        toolkit.
        """
        # FIXME: we can modify the toolkits in standard Enaml to simply
        # provide these instead of inferring them.
        shell_name = 'Container'
        abstract_obj = toolkit[shell_name].abstract_loader()
        assert abstract_obj.__name__.endswith(shell_name)
        class_prefix = abstract_obj.__name__[:-len(shell_name)]
        file_prefix = class_prefix.lower()
        return file_prefix, class_prefix

    @classmethod
    def __load_abstract_obj(cls, file_prefix, class_prefix):
        """ Find and load the abstract object given the toolkit
        prefixes.
        """
        errors = []
        # Walk up the MRO looking for classes that have a toolkit
        # implementation.
        for klass in cls.mro():
            if not issubclass(klass, BaseComponent):
                # Don't look for things that are not Enaml components.
                continue
            cls_module = klass.__module__
            if '.' not in cls_module:
                # Module, not a package.
                abstract_modname = '{0}_{1}'.format(file_prefix, cls_module)
            else:
                base_package, base_modname = cls_module.rsplit('.', 1)
                abstract_modname = '{0}.{1}_{2}'.format(base_package, file_prefix, base_modname)
            abstract_class_name = class_prefix + klass.__name__
            # Import the module.
            try:
                # Use a fromlist to make sure that we get the leaf
                # module, not the root package.
                abstract_module = __import__(abstract_modname, fromlist=[abstract_class_name])
            except ImportError, e:
                errors.append(e)
                continue
            # If the class does not exist, then this should raise the
            # appropriate error.
            abstract_class = getattr(abstract_module, abstract_class_name)
            break
        else:
            raise ImportError('Could not import a matching abstract class: {0}'.format(
                '\n'.join([str(e) for e in errors])))
        abstract_obj = abstract_class()
        return abstract_obj


