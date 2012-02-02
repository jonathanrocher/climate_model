""" GSOD data collection tool.

Instruction for accessing NCDC data:
a) Enter:  open ftp.ncdc.noaa.gov    
b) Login is:  ftp
c) Password is:  your email address
d) To move to the correct subdirectory, enter:  
   cd /pub/data/gsod/<DESIRED YEAR>
e) Annual files:
   eg, gsod_2006.tar - All 2006 files (compressed) by station, in one tar file.
   Station files:
   eg, 010010-99999-2006.op.gz - Files by station year, identified by WMO number, 
   WBAN number (if appropriate), and year.

Background information:
a) locations:
- WMO location codes are also named 'USAF'. They are distinct from the WBAN
location code. 
- Each station is identified by a unique set of (WMO, WBAN) codes.

###############################################################################
TO DO LIST:
###############################################################################
TODO: Add the possibility to load several years for one location inside the
same DF/panel.
TODO: Add other data sources such as weather underground, arm.gov, data.gov,
... and allow merging data. Create a DataSource class to unify how data
collecting classes interact with data sources?
TODO: Allow for custom ftp and opeDAP retrieval
TODO: Build a UI on top of all of this. A simple one just to search and store
the files locally. Another one integrating an ipython prompt to load the data
and be able to play with them afterwards.
"""

# Std lib imports
import datetime
import os
import numpy as np
import pandas
import warnings

# ETS imports
from traits.api import HasTraits, Instance, Enum, Array, Dict

# Local imports
from retrieve_remote import retrieve_file, info2filepath
from file_sys_util import untar, unzip
from extend_pandas import append_panels

###############################################################################

# FTP successful return code
OUT_CWD_SUCCESS = '250 CWD command successful'
OUT_LS_SUCCESS = '226 Transfer complete'

DATA_FILE_COLS = ['STN---', 'WBAN', 'YEARMODA', 'TEMP', 'TEMP-count',
                      'DEWP', 'DEWP-count', 'SLP', 'SLP-count', 'STP',
                      'STP-count', 'VISIB', 'VISIB-count', 'WDSP',
                      'WDSP-count', 'MXSPD', 'GUST', 'MAX', 'MIN', 'PRCP',
                      'SNDP', 'FRSHTT']

###############################################################################

def list_WMO_locations_per_country():
    """ List the range of location for each country found in file
    NCDC-country-list.txt. The file is of the form below with a number of
    country code that is unknown. It relies on the fact that the first 13
    characters describe the range and everything after character 45 is the
    country.

    910000-914999 HI, KA, LN, MH, MY, NZ, PN, WK Pacific Ocean Islands
    915000-915299 SO                             Solomon Islands
    915300-915399 NW, NZ                         Detached Islands (Nauru, New Zealand)

    FIXME: instead of manual loading, use genfromtxt. It can split a line
    on a number of characters.
    """
    loc_range_dict = {}
    
    country_list_filemame = os.path.join("Data", "GSOD", "NCDC-country-list.txt")
    f_country_list = open(country_list_filemame, "r")
    line = f_country_list.readline()
    # Skip header
    while not line.startswith('0'):
        line = f_country_list.readline()
        
    for line in f_country_list:
        line = line.strip()
        if line:
            val_range = tuple([int(val) for val in line[:13].split("-")])
            country_codes = line[13:45].strip().split(",")
            country_name = line[45:]
            loc_range_dict[country_name] = (country_codes, val_range)
            
    f_country_list.close()
    return loc_range_dict

class CountryDatabase(dict):
    """ Create an object that behaves like a dictionary but also possess a
    search method for searching a country's name.

    FIXME: is the super in the __init__ needed? Seems fine without it
    """
    def __init__(self, *args, **kw):
        super(CountryDatabase, self).__init__(*args, **kw)
        # Note that self = list...() wouldn't work because it would create
        # a new var in the method's local namespace
        self.update(list_WMO_locations_per_country())

    def search_country(self, part_name):
        """ Search for all country with part_name in their name, ignoring cases.
        FIXME: Add regex support
        """
        results = [country for country in self.keys()
                   if country.lower().find(part_name.lower()) != -1]
        return results

    def __getitem__(self, item):
        """ Make the dict smarter by being able to guess the key if the part given is unambigious
        """
        options = self.search_keys(item)
        if item in self:
            return super(CountryDatabase, self).__getitem__(item)
        elif len(options) == 1:
            return super(CountryDatabase, self).__getitem__(options[0])
        else:
            if len(options) == 0:
                raise KeyError("%s is not a valid key nor a part of a key." % item)
            else:
                raise KeyError("%s is part of more than 1 key: %s. Which did you mean?"
                               % (item, options))
            
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
    """ Read the ish-history.TXT metadata file: it connects the WMO location to the WBAN location,
    location name, the country codes, the lattitude, longitude elevation, and range of dates.

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
                           names = DATA_FILE_COLS, skiprows = [0])
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
 
def collect_year_at_loc(year, location_WMO, location_WBAN, data_source = 'NCDC'):
    """ Collect the data GSOD data file for specified location and specified
    year. Look locally for the file first. If it is not there, and its gzip
    version is not either, use the ftp connection to retrieve it from data
    source.
    """
    filename = info2filepath(year, location_WMO, location_WBAN)
    folder_location = os.path.join("Data", "GSOD", "gsod_"+str(year))
    filepath = os.path.join(folder_location, filename)
    filepath_found = True
    
    if not os.path.exists(filepath):
        zipped_filepath = filepath+".gz"
        if os.path.exists(zipped_filepath):
            unzip(zipped_filepath)
        elif os.path.exists(os.path.join(folder_location, "gsod_"+str(year)+".tar")):
            # Possible not to rely on outside servers... 
            untar(os.path.join(folder_location, "gsod_"+str(year)+".tar"))
            if os.path.isfile(zipped_filepath):
                unzip(zipped_filepath)
            else:
                warnings.warn("File %s is missing from the dataset: skipping this location." % zipped_filepath)
                filepath_found = False
        else:
            target_folder = "Data/GSOD/gsod_"+str(year)
            if not os.path.exists(target_folder):
                print "Creating locally the folder %s." % target_folder
                os.mkdir(target_folder)
            # Download the file from NCDC
            if data_source == 'NCDC':
                remote_location = str(year)
            remote_target = os.path.join(remote_location, filename+".gz")
            retrieve_file(data_source, remote_target, zipped_filepath)
            unzip(zipped_filepath)
        
    if filepath_found:
        return datafile2pandas(filepath)


def count_op_files(folder):
    return len([filename for filename in os.listdir(folder) if os.path.splitext(filename)[1] in [".op", ".gz"]])

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
            print "Retrieving archive %s... This may take several minutes." % local_filepath
            remote_target = os.path.join(remote_location, filename)
            retrieve_file(data_source, remote_target, local_filepath)
        untar(local_filepath)
    try:
        panda = datafolder2pandas(local_folderpath)
    except MemoryError:
        # For years where there is a large amount of data, it is not possible to load everything in memory
        # FIXME: load the data in a memory mapped/pytable stored pandas in this
        # case? Clarify because the memory error is thrown by mmap. It may be
        # doing this already, but be running into mmap limitations?
        warnings.warn("The year %s contains too much data to be loaded into a single object in memory")
        panda = None
    return panda

def search_station_codes(part_station_name, location_dict):
    """ Search for all station names that contain the string part_station_name
    and return their location codes. 
    FIXME: Add regex support
    """
    return [(key, location_dict[key]) for key in location_dict.keys()
            if key.lower().find(part_station_name.lower()) != -1]

def search_station(location_db, location_dict, station_name = None, exact_station = False, WMO_location = None,
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
    data_source = Enum("NCDC")
    
    # Metadata
    country_db = Instance(CountryDatabase)
    location_db = Array()
    location_dict = Dict()

    def __init__(self, data_source = 'NCDC'):
        """ Initialization of the reader
        """
        self.country_db = CountryDatabase()
        self.location_db = read_ish_history()
        self.location_dict = initialize_location_dict(self.location_db)
        
    def search_station_codes(self, part_station_name):
        return search_station_codes(part_station_name, self.location_dict)

    def search_station(self, station_name = None, exact_station = False, location_WMO = None,
                       location_WBAN = None, country = None,
                       state = None):
        return search_station(self.location_db, self.location_dict,
                              station_name, exact_station, location_WMO, location_WBAN,
                              country, state)

    def collect_year(self, year=None, station_name=None, exact_station = False, location_WMO=None,
                     location_WBAN=None, country=None, state=None):
        """ Process a request for data for a given year at a given location optionaly.

        Inputs:
        - year, int. If no year is passed, choose the current one.
        - station_name, str. (Part of) Name of the station to collect data at. The station
        names are search for in the ish-history txt file stored in self.location_db.
        - exact_station, bool. If false, all station names are search and the ones
          containing the string station_name are selected.
        - location WMO code and/or WBAN code, int, int. If no location is selected,
        collect the yearly data for all locations.

        Output:
        - pandas data structure: 2D DataFrame if only one location is
        requested, 3D (panel) if multiple locations are requested
        """
        if year is None:
            year = datetime.datetime.today().year
            warnings.warn("No year was provided: using the current one (%s)" % year)
            
        no_location = (location_WMO is None and location_WBAN is None
                       and station_name is None and country is None and
                       state is None)
        if no_location:
            # Requested all data for the year that is at all locations
            return collect_year(year)
        else:
            filtered = search_station(self.location_db, self.location_dict,
                                      station_name, exact_station, location_WMO, location_WBAN,
                                      country, state)
            if len(filtered) == 1:
                return collect_year_at_loc(year, location_WMO = filtered['USAF'][0],
                                           location_WBAN = filtered['WBAN'][0])
            else:
                data = {}
                for layer in filtered:
                    df = collect_year_at_loc(year, layer['USAF'], layer['WBAN'])
                    # reindex over the entire year in case there are missing values
                    if df is None:
                        continue
                    df = df.reindex(pandas.DateRange(start = '1/1/%s' % year, end = '31/12/%s' % year,
                                                     offset = pandas.datetools.day))
                    key = str(layer['USAF'])+"-"+str(layer['WBAN'])
                    data[key] = df
                return pandas.Panel(data)

    def collect_data(self, year_list=[], year_start = None, year_end = None, 
                station_name=None, exact_station = False, location_WMO=None,
                location_WBAN=None, country=None, state=None):
        """ Process a request for data possibly over multiple years. If the list
        is empty, 

        Inputs:
        - year_list, list(int). The list of years the data should be collected.
        - year_start, year_end, int, int. Fed to range if year_list is empty. 
        - other inputs are identical to collect_year method

        Output:
        - pandas data structure: 2D DataFrame if only one location is
        requested, 3D (panel) if multiple locations are requested
        """
        if len(year_list) == 0:
            year_list = range(year_start, year_end, 1)
        else:
            year_list.sort()

        result = None
        for year in year_list:
            year_data = self.collect_year(year, station_name, exact_station, location_WMO,
                                          location_WBAN, country, state)
            if result:
                result = append_panels(result, year_data)
            else:
                result = year_data
        return result
            
            
def filter_data(panel, measurements = [],
                date_start = None, date_end = None, offset = None,
                locations = []):
    """ Extract specific data from a panel: reduce the minor axis to only the
    type of data listed in data_list (must be in DATA_FILE_COLS), or reduce
    the major axis to a smaller range of dates or reduce the number of items
    to a list of locations. 

    Note: This is to illustrate the fancy indexing on a panel.
    """
    # Convert 1 element to a list
    if isinstance(measurement_list, str):
        measurement_list = [measurement_list]
    if isinstance(location_list, str):
        location_list = [location_list]

    # Filter items
    if location_list:
        panel = panel.filter(location_list)

    # Filter major and minor axis
    if not set(measurement_list).issubset(set(DATA_FILE_COLS)):
        raise ValueError("%s is not a valid data type. Allowed values are %s."
                         % (set(measurements)-set(DATA_FILE_COLS), DATA_FILE_COLS))
    if measurements:
        result = panel.ix[:,date_start:date_end,measurements]
    else:
        result = panel.ix[:,date_start:date_end,:]
    return result
            
if __name__ == "__main__":
    # Sample code for usage description
    dr = GSODDataReader()
    dr.search_station("austin", country = "US", state = "TX")
    dr.search_station("pari", country = "FR")
    paris_data =  dr.collect_data([2007, 2008], station_name = "PARIS", country = "FR")
    paris_temp_data = filter_data(paris_data, ["TEMP", "VISIB"])
    
    store = pandas.HDFStore("paris_temp_data.h5", "w")
    store["data"] = paris_temp_data
    store.close()

    # See gsod_plot_3 for visualization of the content of that pandas or file. 
