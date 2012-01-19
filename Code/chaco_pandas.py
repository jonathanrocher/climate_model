""" Utilities for deal with pandas objects
"""

import pandas
import numpy as np
import time

def pandas_hdf_to_data_dict(filename):
    """ Explore the content of the pandas store (HDF5) and create a dictionary
    of timeseries (numpy arrays) found in it. The key will be used as names
    for the curves. All indexes must be the same and stored once with key
    "index".

    2 possible approches here: dealing with v objects which are pytables
    groups containing directly the numpy arrays used for plotting, or
    reconstructing the pandas for the simplicity of the code. 

    FIXME: Add check that index is always the same. 
    """
    store = pandas.HDFStore(filename, "r")
    pandas_list = [store[key] for key in store.handle.root._v_children.keys()]
    names = store.handle.root._v_children.keys()
    return pandas2array_dict(pandas_list, names = names)
    
def pandas2array_dict(pandas_list, names = []):
    """ Convert a list of pandas into a dict of arrays for plotting.
    They must have the same index. One of the entries in the output dict is one
    of these indexes with key "index". The arrays will be stored with the name
    of the pandas (.name attr), and if applicable the name of the column and of
    the item. Optionally a list of names to use can be passed to override the
    .name attribute. 
    """
    array_dict = {}
    # If there is only 1 pandas, make up a name
    if len(pandas_list) == 1 and not pandas_list[0].name and not names:
        names = ["pandas"]
    # If datetime index, convert to an array of ints, and create tick labels
    first_index = np.array(pandas_list[0].index)
    if first_index.is_all_dates():
        index_is_dates = True
        array_dict["index"] = [time.mktime(d.timetuple()) for d in first_index]
    else:
        index_is_dates = False
        array_dict["index"] = first_index
    for i, pandas_ds in enumerate(pandas_list):
        if names:
            name = names[i]
        elif pandas_ds.name:
            name = pandas_ds.name
        else:
            raise ValueError("The pandas number %s in the list doesn't have a "
                             "name." % i)
            
        if isinstance(pandas_ds, pandas.core.series.Series):
            entry = name
            array_dict[entry] = pandas_ds.values
        elif isinstance(pandas_ds, pandas.core.frame.DataFrame):
            for col_name,series in pandas_ds.iteritems():
                entry = name+"-"+col_name
                array_dict[entry] = pandas_ds[col_name].values
        else:
            for item, df in pandas_ds.iteritems():
                for col_name,series in df.iteritems():
                    entry = name+"-"+item+"-"+col_name
                    array_dict[entry] = df[col_name].values
    assert("index" in array_dict)
    return array_dict, index_is_dates
