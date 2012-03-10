""" GSOD data collection tool.

Instruction for accessing NCDC data:
a) Enter:  open ftp.ncdc.noaa.gov    
b) Login:  ftp
c) Password:  your email address
d) To move to the correct subdirectory:  
   cd /pub/data/gsod/<DESIRED YEAR>
e) Annual files:
   eg, gsod_2006.tar - All 2006 files (compressed) by station, in one tar file.
   Station files:
   eg, 010010-99999-2006.op.gz - Files by station & year, identified by WMO 
   number, WBAN number, and year.

Background information:
a) locations:
- WMO location codes are also named 'USAF'. They are distinct from the WBAN
location code. 
- Each station is identified by a unique set of (WMO, WBAN) codes.

###############################################################################
TO DO LIST:
###############################################################################

TODO: Add possibility to store the collected data into a file at collection. 
Implement it with the possibility to write to the file piece by piece.
TODO: Add caching to list the non-existing files. Prepopulate it from the database 
files that contain the range of data existance.
TODO: Refactor the content that is pure NOAA's NCDC related into its own module
TODO: Add other data sources such as weather underground, arm.gov, data.gov,
ECMWF, ... and allow merging of data.
TODO: Create a DataSource class to unify how data collecting classes interact
with data sources. Allow to create new datasources and add them to a
collection. Store a list of the available measurements (TEMP, WIND SPEED,
...) as the list of data sources gets bigger. Also keep track of the source for 
each dataset. 
TODO: Allow for custom ftp and opeDAP retrieval.
TODO: Build a UI on top of all of this. A simple one just to search and store
the files locally. Another one integrating an ipython prompt to load the data
and be able to play with them afterwards.
TODO: Add/explore memory mapping (with pytables?) when collecting VERY large
amounts of data.
"""

# Std lib imports
import datetime
import os
import warnings

# General imports
import numpy as np
import pandas

# ETS imports
from traits.api import HasTraits, Instance, Enum, Array, Dict, Str

# Local imports
from retrieve_remote import retrieve_file, info2filepath
from file_sys_util import untar, unzip
from extend_pandas import downsample, GSOD_DATA_FILE_COLS

###############################################################################

# FTP successful return code
OUT_CWD_SUCCESS = '250 CWD command successful'
OUT_LS_SUCCESS = '226 Transfer complete'

###############################################################################
            
def list_yearly_data(year, ftp_connection):
    """ List the GSOD data file available for a specified year on the server.
    It assumes that an ftp connection is already open and will be close
    externally.

    Returns:
    - list of filenames for the corresponding year
    - list of location tuple (WMO code, WBAN code)
    """
    file_list = []
    location_list = []
    
    def identify_file_location(line):
        filename = line.split()[-1]
        file_list.append(filename)
        if filename.find("-") != -1:
            location_list.append(tuple(filename.split("-")))
        return
    
    folder_location = os.path.join('/pub/data/gsod',str(year))
    out_cwd = ftp_connection.cwd(folder_location)
    if out_cwd != OUT_CWD_SUCCESS:
        raise OSError("Unable to change to directory %s. Is the ftp connection open?"
                      % folder_location)
    out_ls = ftp_connection.retrlines('LIST', callback = identify_file_location)
    if out_ls != OUT_LS_SUCCESS:
        raise OSError("Failed listing the content of %s" % folder_location)
    return file_list, location_list.sort()

def read_ish_history():
    """ Read the ish-history.TXT metadata file: it connects the WMO location to 
    the WBAN location, location name, the country codes, the lattitude, 
    longitude elevation, and range of dates.

    Returns a structured array
    """
    ish_filepath = os.path.join("Data", 'GSOD', 'ish-history.TXT')
    col_names = ["USAF", "WBAN", "STATION_NAME", "CTRY_WMO", "CTRY_FIPS", "ST",
                 "CALL", "LAT", "LON", "ELEV", "BEGIN", "END"]
    starts = np.array([0,7,13,43,46,49,52,58,65,73,83,92])
    # Leave the space between values between columns since there is no
    # separator to provide to genfromtxt
    ends = np.hstack((starts[1:], 100)) 
    widths = ends-starts
    # The datetime64 is not yet accepted by Pandas but will in the future
    #types = [np.int, np.int, "S31", "S3", "S3", "S3", "S5", np.int32,
    #         np.int32, np.int32, np.datetime64, np.datetime64]
    types = [np.int, np.int, "S31", "S3", "S3", "S3", "S5", np.int32, np.int32,
             np.int32, "S9", "S9"]

    def clean_str(x):
        if (x == "." or x == "??"):
            return ""
        return x
    converters = {2: clean_str, 3: clean_str, 4: clean_str}
    
    dtypes = np.dtype([(name,type) for name,type in zip(col_names,types)])
    data = np.genfromtxt(ish_filepath, delimiter = widths,
                         skiprows = 22, dtype = dtypes, autostrip = True, 
                         converters = converters)
    return data

def initialize_location_dict(ishdata = None):
    """ Read the conversion between station names and their WMO and WBAN locations.

    Inputs:
    - ishdata: pandas dataframe containing the data from the ish-history.TXT file
    """
    location_dict = {}
    if ishdata is None:
        ishdata = read_ish_history()

    for i in xrange(ishdata.shape[0]):
        if ishdata[i][2]:
            # There is a station name. Store its location codes
            location_dict[ishdata[i][2]] = (ishdata[i][0], ishdata[i][1])
    return location_dict
    
def datafile2pandas(filepath):
    """ Read a NCDC GSOD file into a pandas dataframe
    """
    df = pandas.read_table(filepath, sep="\s*", index_col=2, parse_dates = True,
                           names = GSOD_DATA_FILE_COLS, skiprows = [0])
    return df

def datafolder2pandas(folderpath):
    """ Read a NCDC GSOD folder into a pandas panel
    """
    data = {}
    print "Loading all op files in %s ..." % folderpath
    for filename in os.listdir(folderpath):
        if os.path.splitext(filename)[1] == ".op":
            file2load = os.path.join(folderpath, filename)
            key = filename[:13]
            data[key] = datafile2pandas(file2load)
        elif filename.endswith(".op.gz"):
            unzip(os.path.join(folderpath, filename))
            file2load = os.path.join(folderpath, os.path.splitext(filename)[0])
            key = filename[:17]
            data[key] = datafile2pandas(file2load)
    return pandas.Panel(data)
 
def collect_year_at_loc(year, location_WMO, location_WBAN, data_source = 'NCDC', 
                        internet_connected = True):
    """ Collect the data GSOD data file for specified location and specified
    year. Look locally for the file first. If it is not there, and its gzip
    version is not either, untar the file if it is present and has not been
    untared, or use the ftp connection to retrieve it from data source.
    """
    filename = info2filepath(year, location_WMO, location_WBAN)
    folder_location = os.path.join("Data", "GSOD", "gsod_"+str(year))
    filepath = os.path.join(folder_location, filename)
    print "Attempting to collect %s..." % filepath
    filepath_found = True
    
    if not os.path.exists(filepath):
        zipped_filepath = filepath+".gz"
        if os.path.exists(zipped_filepath):
            unzip(zipped_filepath)
        elif os.path.exists(os.path.join(folder_location,
                                         "gsod_"+str(year)+".tar")):
            # Possible not to rely on outside servers: untar the file if there
            # are no op.gz or op files. If not it means that the file is
            # missing.
            there_are_op_files = False
            for filename in os.listdir(folder_location):
                if os.path.splitext(filename)[1] in [".op", ".op.gz"]:
                    there_are_op_files = True
                    break
            if not there_are_op_files:
                untar(os.path.join(folder_location, "gsod_"+str(year)+".tar"))
            if os.path.isfile(zipped_filepath):
                unzip(zipped_filepath)
            else:
                warnings.warn("File %s is missing from the dataset: skipping "
                              "this location." % zipped_filepath)
                filepath_found = False
        elif internet_connected:
            target_folder = "Data/GSOD/gsod_"+str(year)
            if not os.path.exists(target_folder):
                print "Creating locally the folder %s." % target_folder
                os.mkdir(target_folder)
            # Download the file from NCDC
            if data_source == 'NCDC':
                remote_location = str(year)
            remote_target = os.path.join(remote_location, filename+".gz")
            retrieve_file(data_source, remote_target, zipped_filepath)
            if os.path.isfile(zipped_filepath):
                unzip(zipped_filepath)
            else:
                filepath_found = False
        else:
            filepath_found = False
        
    if filepath_found:
        return datafile2pandas(filepath)


def count_op_files(folder):
    return len([filename for filename in os.listdir(folder) 
                if os.path.splitext(filename)[1] in [".op", ".gz"]])

def collect_year(year, data_source = 'NCDC'):
    """ Collect the GSOD data file for all locations for the specified
    year. Look locally for the tar file first. If it is not there, and its gzip
    version is not either, use the ftp connection to retrieve it from data
    source.
    """
    filename = info2filepath(year)
    local_folderpath = os.path.join("Data", "GSOD", "gsod_"+str(year))
    local_filepath = os.path.join(local_folderpath, filename)
    if not os.path.isdir(local_folderpath):
        # Folder not already present
        os.mkdir(local_folderpath)
    if count_op_files(local_folderpath) < 10:
        # probably not all the data files are present
        if not os.path.exists(local_filepath):
            # tar file not present either: download it!
            if data_source == 'NCDC':
                remote_location = str(year)
            print("Retrieving archive %s... This may take several minutes." 
                  % local_filepath)
            remote_target = os.path.join(remote_location, filename)
            retrieve_file(data_source, remote_target, local_filepath)
        untar(local_filepath)
    try:
        panda = datafolder2pandas(local_folderpath)
    except MemoryError:
        # For years where there is a large amount of data, it is not possible to
        # load everything in memory
        # FIXME: load the data in a memory mapped/pytable stored pandas in this
        # case? Clarify because the memory error is thrown by mmap. It may be
        # doing this already, but be running into mmap limitations?
        warnings.warn("The year %s contains too much data to be loaded into a "
                      "single object in memory")
        panda = None
    return panda

def search_station_codes(part_station_name, location_dict):
    """ Search for all station names that contain the string part_station_name
    and return their location codes. 
    FIXME: Add regex support
    """
    return [(key, location_dict[key]) for key in location_dict.keys()
            if key.lower().find(part_station_name.lower()) != -1]

def search_station(location_db, location_dict, station_name = None, 
                   exact_station = False, WMO_location = None,
                   WBAN_location = None, country_code = None, state_code = None):
    """ Search for a station from part of its name, its location, its country code and/or its state.
    Inputs:
    - location_db, struct array: database of locations and all its metadata (location codes,
      country, state, coord, elevation, ...). It is generated from the function
      read_ish_history() for the NCDC data source. 
    """
    L = len(location_db)
    mask = np.ones(L, dtype = np.bool)
    if station_name:
        if exact_station:
            match_station = location_db['STATION_NAME'] == station_name
        else:
            # Allow for partial station name
            match_station_idx = [idx for idx,name in enumerate(location_db['STATION_NAME'])
                                 if station_name.lower() in name.lower()]
            match_station = np.zeros(L, dtype = np.bool)
            match_station[match_station_idx] = True
        mask = mask & match_station
    if WMO_location:
        match_wmo = location_db['USAF'] == WMO_location
        mask = mask & match_wmo
    if WBAN_location:
        match_wban = location_db['WBAN'] == WBAN_location
        mask = mask & match_wban
    if country_code:
        match_country = location_db['CTRY_WMO'] == country_code
        mask = mask & match_country
    if state_code:
        match_state = location_db['ST'] == state_code
        mask = mask & match_state
    return location_db[mask]

class GSODDataReader(HasTraits):
    """ Data reader for GSOD data retrieved from NCDC servers
    """
    data_source = Enum("All", "NCDC")
    
    # Metadata
    location_db = Array()
    location_dict = Dict()

    def __init__(self, data_source = 'NCDC'):
        """ Initialization of the reader
        """
        self.location_db = read_ish_history()
        self.location_dict = initialize_location_dict(self.location_db)
        
    def search_station_codes(self, part_station_name):
        return search_station_codes(part_station_name, self.location_dict)

    def search_station(self, station_name = None, exact_station = False, 
                       location_WMO = None, location_WBAN = None, 
                       country = None, state = None):
        return search_station(self.location_db, self.location_dict,
                              station_name, exact_station, location_WMO, 
                              location_WBAN, country, state)

    def collect_year(self, year=None, station_name=None, exact_station = False, 
                    location_WMO=None, location_WBAN=None, country=None, 
                    state=None, internet_connected = True):
        """ Process a request for data for a given year at a given location 
        optionaly.

        Inputs:
        - year, int. If no year is passed, choose the current one.
        - station_name, str. (Part of) Name of the station to collect data at. 
        The station names are search for in the ish-history txt file stored in 
        self.location_db.
        - exact_station, bool. If false, all station names are search and the 
          ones containing the string station_name are selected.
        - location WMO code and/or WBAN code, int, int. If no location is selected,
        collect the yearly data for all locations.

        Output:
        - pandas data structure: 2D (DataFrame) if only one location is
        requested, 3D (panel) if multiple locations are requested
        """
        if year is None:
            year = datetime.datetime.today().year
            warnings.warn("No year was provided: using the current one (%s)" 
                          % year)
            
        no_location = (location_WMO is None and location_WBAN is None
                       and station_name is None and country is None and
                       state is None)
        if no_location:
            # Requested all data for the year that is at all locations. Returns
            # a panel if it can fit in memory, and None if not. In the latter
            # case, the data files are still stored locally. 
            return collect_year(year)
        else:
            filtered = search_station(self.location_db, self.location_dict,
                                      station_name, exact_station, location_WMO, location_WBAN,
                                      country, state)
            if len(filtered) == 1:
                result = collect_year_at_loc(year, location_WMO = filtered['USAF'][0],
                                             location_WBAN = filtered['WBAN'][0], 
                                             internet_connected = internet_connected)
            else:
                data = {}
                for layer in filtered:
                    df = collect_year_at_loc(year, layer['USAF'], layer['WBAN'], 
                                             internet_connected = internet_connected)
                    # reindex over the entire year in case there are missing values
                    if df is None:
                        continue
                    df = df.reindex(pandas.DateRange(start = '1/1/%s' % year,
                                                     end = '31/12/%s' % year,
                                                     offset = pandas.datetools.day))
                    key = "%s-%s" % (layer['USAF'], layer['WBAN'])
                    data[key] = df
                result = pandas.Panel(data)
            return result
                
    def collect_data(self, year_list=[], year_start = None, year_end = None, 
                station_name=None, exact_station = False, location_WMO=None,
                location_WBAN=None, country=None, state=None, 
                internet_connected = True):
        """ Process a request for data possibly over multiple years. If the list
        is empty, 

        Inputs:
        - year_list, list(int). The list of years the data should be collected.
        - year_start, year_end, int, int. Fed to range if year_list is empty. 
        - other inputs are identical to collect_year method

        Output:
        - pandas data structure: 2D (DataFrame) if only one location is
        requested, 3D (panel) if multiple locations are requested
        """
        if len(year_list) == 0:
            year_list = range(year_start, year_end, 1)
        else:
            year_list.sort()

        result = None
        print "Collecting data for years %s." % year_list
        for year in year_list:
            year_data = self.collect_year(year, station_name, exact_station,
                                          location_WMO, location_WBAN, country,
                                          state, internet_connected = internet_connected)
            if year_data is None:
                continue
            else:
                print "Data found:", year_data
            if result:
                if isinstance(year_data, pandas.DataFrame):
                    result = result.append(year_data)
                elif isinstance(year_data, pandas.DataFrame):
                    result = pandas.concat([result, year_data], axis = 1)
            else:
                result = year_data
        return result
            
if __name__ == "__main__":

    # Sample code for data collection tools usage description
    dr = GSODDataReader()
    dr.search_station("austin", country = "US", state = "TX")
    dr.search_station("pari", country = "FR")
    paris_data =  dr.collect_data([2007, 2008], station_name = "PARIS", country = "FR")
    
    # Pandas manipulation
    from extend_pandas import filter_data
    paris_data_temp = filter_data(paris_data, measurements = "TEMP")    
    paris_data_temp_downsampled = downsample(paris_data_temp, method = "average", offset = "unique_month")

    # Custom filtration
    def weighted_average(arr):
        weights = np.array([1,2,3,4,3,2,1])
        if len(arr) == 7:
            return (arr*weights).sum()/weights.sum()
        else:
            return arr.mean()
    filtered = filter_data(paris_data, measurements = ["TEMP", "WDSP"],
                           date_start = "2007/1/2", date_end = "2008/12/15",
                           downsampling_method = weighted_average, offset = "unique_week")
    filtered2 = filter_data(paris_data, measurements = ["TEMP", "WDSP"],
                           date_start = "2007/1/2", date_end = "2008/12/15",
                           downsampling_method = "average", offset = "unique_week")

    # Storage
    from extend_pandas import store_pandas
    data_dict = {"fil1": filtered, "fil2": filtered2}
    for complib in [None, 'zlib', 'bzip2', "blosc"]: 
        store_pandas(data_dict, "compare_downsampling_%s.h5" % complib, 
                     complevel = 9 , complib = complib)
    
    # See gsod_plot_3 for visualization of the content of these pandas or file. 
