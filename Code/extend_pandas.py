""" General functionalities on pandas.

TODO: Implement downsampling of panels
TODO: Contribute that to pandas project?
"""
import datetime
import types
import pandas
import numpy as np
from numpy.random import randint

GSOD_DATA_FILE_COLS = ['STN---', 'WBAN', 'YEARMODA', 'TEMP', 'TEMP-count',
                      'DEWP', 'DEWP-count', 'SLP', 'SLP-count', 'STP',
                      'STP-count', 'VISIB', 'VISIB-count', 'WDSP',
                      'WDSP-count', 'MXSPD', 'GUST', 'MAX', 'MIN', 'PRCP',
                      'SNDP', 'FRSHTT']
                      
NUM2STR_MONTH = {1: "01-Jan", 2: "02-Feb", 3: "03-Mar", 4: "04-Apr", 5: "05-May", 6: "06-Jun",
                 7: "07-Jul", 8: "08-Aug", 9: "09-Sep", 10: "10-Oct", 11: "11-Nov", 12: "12-Dec"}

def rand_sample(arr):
    """ Select a random value inside an array
    """
    ind = randint(0,len(arr))
    return arr[ind]

def select_first(arr):
    """ Select a random value inside an array
    """
    return arr[0]

def select_last(arr):
    """ Select a random value inside an array
    """
    return arr[-1]

def _downsample_df(df, method = "average", offset = "unique_week"):
    """ Downsample the DF provided along the time dimension.
    Inputs:
    - method, str or callable. Method to downsample the timeseries. Must be in
    ['average', 'std', 'min', 'max', 'first', 'last', 'rand_sample']. It can also be a custom callable.
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
        offset = "unique_week"
        
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
    group_by_func = eval("get_"+offset)
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
    elif method == "first":
        new_df = grouped.aggregate(select_first)
    elif method == "last":
        new_df = grouped.aggregate(select_last)
    elif method == "rand_sample":
        new_df = grouped.aggregate(rand_sample)
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


def filter_data(panel, locations = [], measurements = [],
                date_start = None, date_end = None,
                offset = None, downsampling_method = ""):
    """ Extract specific data from a panel: reduce the minor axis to only the
    type of data listed in data_list, reduce the major axis to a smaller range
    of dates or reduce the number of items to a list of locations.

    Inputs:
    - measurements, list(str).  List of column names to select (must be in
    GSOD_DATA_FILE_COLS)
    - date_start, date_end. start and end dates for slicing in the time
    dimension. Can be a datetime object or a string in the format YYYY/MM/DD.
    - offset. Used to disseminate data or to downsample data if a
    downsampling_method is given. Can be 'unique_week', 'month',
    'unique_month', 'year'. 
    - downsampling_method, str. Method to downsample the dataset. Can be
    'average', 'std', 'min', 'max', 'first', 'last', 'rand_sample'.

    Outputs:
    - slice/sub-part of the original panel. If only one measurement is 
    requested, returns a DF with the locations as the columns.
    """
    #####################
    # Rationalize inputs
    #####################
    if isinstance(measurements, str):
        measurements = [measurements]
    if isinstance(locations, str):
        locations = [locations]
    if date_end and not date_start:
        date_start = panel.major_axis[0]
    if date_start and not date_end:
        date_end = panel.major_axis[-1]

    if isinstance(date_start, str):
        date_start = datetime.datetime.strptime(date_start, '%Y/%m/%d')
    elif isinstance(date_start, int) and date_start > 1800:
        # Input was a year
        date_start = "%s/01/01" % date_start
        date_start = datetime.datetime.strptime(date_start, '%Y/%m/%d')
    if isinstance(date_end, str):
        date_end = datetime.datetime.strptime(date_end, '%Y/%m/%d')
    elif isinstance(date_end, int) and date_end > 1800:
        # Input was a year
        date_end = "%s/01/01" % date_end
        date_end = datetime.datetime.strptime(date_end, '%Y/%m/%d')

    #########
    # FILTERS
    #########
    # filter items
    if locations:
        panel = panel.filter(locations)

    # Filter major and minor axis
    if not set(measurements).issubset(set(GSOD_DATA_FILE_COLS)):
        raise ValueError("%s is not a valid data type. Allowed values are %s."
                         % (set(measurements)-set(GSOD_DATA_FILE_COLS), GSOD_DATA_FILE_COLS))
    if len(measurements) > 1:
        result = panel.ix[:,date_start:date_end, measurements]
    elif len(measurements) == 1:
        # This will automatically convert result to a DF. Passing measurements
        # directly will result in a Panel with length 1 minor_axis
        result = panel.ix[:,date_start:date_end, measurements[0]]
    else:
        result = panel.ix[:,date_start:date_end,:]

    if offset and downsampling_method:
        result = downsample(result, downsampling_method, offset)
    elif offset or downsampling_method:
        warnings.warn("An offset or a downsampling method has been provided "
                      "but both are needed.")
    return result
    
    
def store_pandas(pandas_dict, filename, complevel = 9 , complib = "blosc"):
    """ Take a dictionary of pandas and stores them in an HDF5 file. If a list 
    of pandas is passed instead of a dict, 
    """
    # If it is a list, convert to a dict with made-up names
    if isinstance(pandas_dict, list):
        keys = ["pandas%s" % i for i in range(len(pandas_dict))]
        real_pandas_dict = {}
        for key, val in zip(keys,pandas_dict):
            real_pandas_dict[key] = val
        pandas_dict = real_pandas_dict
        
    store = pandas.HDFStore(filename, mode = "a", complevel = complevel, 
                            complib = complib)
    for name,panda in pandas_dict.items():
        store[name] = panda
    store.close()
