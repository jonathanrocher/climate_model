""" Missing functionalities on pandas I believe. Contribute that to pandas project?
"""

import pandas
import numpy as np

def append_panels(p1,p2):
    """ Append panels to each other in the index (time) dimension (major axis)

    FIXME: This is too restrictive to be pushed to pandas in general: should
    add NaN in dimensions that are not comon to both panels.
    TODO: Add capability to append along any dimension.
    TODO: Add capability to add many panels at once.
    """
    # Shape testing
    if not (p1.items.shape == p2.items.shape):
        raise ValueError("The number of items is not the same in both panels.")
    if not (p1.minor_axis.shape == p2.minor_axis.shape):
        raise ValueError("The number of minor axis is not the same in both panels.")
        
    # Testing elements in each dimension
    if not np.all(p1.items.values == p2.items.values):
        raise ValueError("The elements of the items dimension are not the same in both panels.")
    if not np.all(p1.minor_axis.values == p2.minor_axis.values):
        raise ValueError("The elements of the minor axis dimension are not the same in both panels.")

    # Values
    p3 = np.hstack((p1.values,p2.values))
    # Dimension labels
    result_items = p1.items
    result_major_axis = np.hstack((p1.major_axis.values, p2.major_axis.values))
    result_minor_axis = p1.minor_axis
    return pandas.Panel(p3, items = result_items, major_axis = result_major_axis, minor_axis = result_minor_axis)
