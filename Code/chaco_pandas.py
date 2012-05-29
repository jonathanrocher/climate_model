""" Utilities for deal with pandas objects.

FIXME: Is there a smarter way for implement things in the out-of-core
paradigm (a la memmap) instead of reading everything into memory? It is likely
not going to fit inside CPU cache so that paradigm may be useful. 
"""

import pandas
import tables
import numpy as np
import time
import warnings

def pandas_hdf_to_data_dict(filename):
    """ Explore the content of the pandas HDFStore (HDF5) and create a dictionary
    of timeseries (numpy arrays) found in it. The key will be used as names
    for the curves. All indexes must be the same and stored once with key
    "index".

    Note: This assumes that the file was created via the pandas' HDFStore
    interface: all pandas are stored inside a group containing the data and the
    array of indexes in each direction. Dataframes and panels are stored
    respectively as 2, and 3 dimensional nd-arrays.

    Returns:
    - content of all (1D) timeseries found in the hdf5 file including the index
    - whether the index representes dates. In that case, the index is stored
    with a kind keyword with value 'datetime' and its values are the times in
    seconds since Epoch. 

    NOTE: The version 1 accesses the pandas, by reconstructing them from the
    HDFStore. But this is inefficient as pandas stores all the pandas components
    in the form of numpy arrays even for DateRange instances. This is an deeper
    implementation that accesses uses the numpy arrays directly inside the HDF
    file (2x gain). 

    Each group and array is stored with a set of attributes accessible via its
    _v_attrs. For example each series contains an index with several attributes
    including 'kind'. It stores if the index was a DateRange in pandas. 
    """
    h5file = tables.openFile(filename, "r")
    content = {}
    index_dict = {}
    # All pandas stored using the HDFStore interface are organized one per
    # group. DateRange indexes possess a 'kind' attribute that specifies
    # that it is an array of datetime objects.
    for key, _ in h5file.root._v_children.items():
        group = getattr(h5file.root, key)
        pandas_type = getattr(group._v_attrs, "pandas_type", "other")
        if pandas_type == 'series':
            # only the read method forces to load the content into memory.
            # Cast to an array of float because sometimes an object array
            # is returned. 
            # FIXME: how to deal with nan?
            content[key] = np.asarray(group.values.read(), dtype = np.float)
            index_dict[key] = group.index
        elif pandas_type == 'frame':
            index_dict[key] = group.axis1
            data = group.block0_values.read()
            if isinstance(data, list):
                # FIXME: this is a hack: pandas sometimes stores a df into a list with 1 array!!
                data = data[0]
            assert(data.ndim == 2)
            for i, col_name in enumerate(group.axis0):
                content[key+"_"+col_name] = np.asarray(data[i,:], dtype = np.float)
        elif pandas_type == 'wide':
            index_dict[key] = group.axis1
            data = group.block0_values.read()
            assert(data.ndim == 3)
            for i, item_name in enumerate(group.axis0):
                for j, col_name in enumerate(group.axis2):
                    entry = key+"_"+item_name+"_"+col_name
                    content[entry] = np.asarray(data[i,:,j], dtype = np.float)
        else:
            raise ValueError("The group found in the file %s is not a standard type." % filename)

    key0,index0 = index_dict.items()[0]
    arr_index0 = index0.read()
    content["index"] = arr_index0
    # Check indexes are all the same.
    # FIXME: do this by creating a 2D np array?
    for k,v in index_dict.items()[1:]:
        if not np.all(v.read() == arr_index0):
            warnings.warn("Error: the index of %s is not equal to the index of %s" % (k, key0))
    index_is_dates = getattr(index0._v_attrs, 'kind', "numeric") == "datetime"
    h5file.close()
    return content, index_is_dates

def pandas2array_dict(pandas_list, names = []):
    """ Convert a list of pandas into a dict of arrays for plotting.
    They must have the same index. One of the entries in the output dict is one
    of these indexes with key "index". The arrays will be stored with the name
    of the pandas (.name attr), and if applicable the name of the column and of
    the item. Optionally a list of names to use can be passed to override the
    .name attribute.
    
    FIXME: Add check that index is always the same. 
    """
    array_dict = {}
    # If there is only 1 pandas, make up a name
    if len(pandas_list) == 1 and not pandas_list[0].name and not names:
        names = ["pandas"]
    # If datetime index, convert to an array of ints, and create tick labels
    first_index = pandas_list[0].index
    if first_index.is_all_dates():
        index_is_dates = True
        array_dict["index"] = [time.mktime(d.timetuple()) for d in np.array(first_index)]
    else:
        index_is_dates = False
        array_dict["index"] = np.array(first_index)
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
