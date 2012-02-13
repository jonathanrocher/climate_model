""" General functionalities on pandas.

TODO: Implement downsampling of panels
TODO: Contribute that to pandas project?
"""
import types
import pandas
import numpy as np

NUM2STR_MONTH = {1: "01-Jan", 2: "02-Feb", 3: "03-Mar", 4: "04-Apr", 5: "05-May", 6: "06-Jun",
                 7: "07-Jul", 8: "08-Aug", 9: "09-Sep", 10: "10-Oct", 11: "11-Nov", 12: "12-Dec"}

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
    result_major_axis = pandas.Index(result_major_axis)
    result_minor_axis = p1.minor_axis
    return pandas.Panel(p3, items = result_items, major_axis = result_major_axis, minor_axis = result_minor_axis)



def _downsample_df(df, method = "average", offset = "unique_week"):
    """ Downsample the DF provided in the time dimension.
    Inputs:
    - method, str or callable. Method to downsample the timeseries. Must be in
    ['average', 'std', 'min', 'max']. It can also be a custom callable.
    - offset, str or int. Describes over what period of time the dates should
    be grouped for downsampling. Must be an int (for the number of days) or a
    string in ['unique_week', 'month', 'unique_month', 'year']. If 'month' is
    chosen, all january values are grouped together ignoring the year. If
    'unique_month', Jan 2012 is treated as a different month from Jan 2011.

    TODO: improve the groupby method of a DF to pass arguments to the function
    used to group (see get_unique_week). 
    """
    date_start = df.index[0]
    if type(offset) not in [int, str]:
        raise ValueError("The offset key word should be a string or an int but"
                         " %s of type %s was passed." % (offset, type(offset)))

    # Parameters to group dates
    if offset == "unique_week":
        num_day_grouped = 7
    elif isinstance(offset, int):
        num_day_grouped = offset
        
    def get_unique_week(date):    
        """ Compute the number of weeks since start.

        FIXME: I would want to pass num_day_grouped and date_start to the
        function instead of using global vars tricks. 
        """ 
        diff_days =  (date - date_start).days
        return diff_days / num_day_grouped

    def get_month(date):
        """ Group dates by month, ignoring years
        """
        return NUM2STR_MONTH[date.month]
    
    def get_unique_month(date):
        """ Group dates by month, not ignoring years: january 2012 is treated
        as a different month as january 2011. 
        """
        return "%s-%s" % (date.year, NUM2STR_MONTH[date.month])
        
    def get_year(date):
        """ Group dates by month, ignoring years
        """
        return date.year

    # Grouping the dates
    if isinstance(offset, str):
        group_by_func = eval("get_"+offset)
    else:
        group_by_func = get_week
    grouped = df.groupby(group_by_func)

    # Applying the aggregation function
    if method == "average":
        new_df = grouped.mean()
    elif method == "std":
        new_df = grouped.std()
    elif method == "min":
        new_df = grouped.aggregate(np.min)
    elif method == "max":
        new_df = grouped.aggregate(np.max)
    elif isinstance(method, types.FunctionType):
        new_df = grouped.aggregate(method)
    else:
        raise NotImplementedError("This downsampling method (%s) is not yet "
                                  "implemented." % method)
    return new_df

def _downsample_panel(panel, method = "average", offset = "unique_week"):
    """ Downsample the panel provided in the time dimension (major axis).

    TODO: Is there a more efficient way to do this?
    """
    data = {}
    for item_name, df in panel.iteritems():
        data[item_name] = _downsample_df(df, method, offset)
    return pandas.Panel(data)

def downsample(obj, method = "average", offset = "unique_week"):
    """ Format the object content to floats and dispatch to the appropriate
    function based on the type of pandas. 
    """
    # Formating the result
    if obj.values.dtype != np.float:
        obj = obj.astype(float)
    
    if isinstance(obj, pandas.DataFrame):
        return _downsample_df(obj, method, offset)
    elif isinstance(obj, pandas.Panel):
        return _downsample_panel(obj, method, offset)
    else:
        raise NotImplementedError("The object %s (of type %s) is not supported"
                                  " for downsampling" % (obj, type(obj)))
    
