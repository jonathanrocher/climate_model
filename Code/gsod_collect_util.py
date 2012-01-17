""" GSOD data collection tool.

Instruction:
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
"""
import datetime
import os
import numpy as np
import pandas
import distutils

from traits.api import HasTraits, Bool, Instance, Enum, Array, Dict

# FTP successful return code
OUT_CWD_SUCCESS = '250 CWD command successful'
OUT_LS_SUCCESS = '226 Transfer complete'
    
def list_WMO_locations_per_country():
    """ List the range of location for each country found in file
    NCDC-country-list.txt. The file is of the form below with a number of
    country code that is unknown. It relies on the fact that the first 13
    characters describe the range and everything after character 45 is the
    country.

    910000-914999 HI, KA, LN, MH, MY, NZ, PN, WK Pacific Ocean Islands
    915000-915299 SO                             Solomon Islands
    915300-915399 NW, NZ                         Detached Islands (Nauru, New Zealand)
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
    """ List the GSOD data file available for a specified year. It assumes that
    an ftp connection is already open and will be close externally.
    """
    file_list = []
    location_WMO_list = []
    location_WBAN_list = []
    
    def identify_file_location(line):
        filename = line.split()[-1]
        file_list.append(filename)
        if filename.find("-") != -1:
            location_WMO_list.append(filename.split("-")[0])
            location_WBAN_list.append(filename.split("-")[1])
        return
    
    folder_location = os.path.join('/pub/data/gsod',str(year))
    out_cwd = ftp_connection.cwd(folder_location)
    if out_cwd != OUT_CWD_SUCCESS:
        raise OSError("Unable to change to directory %s" % folder_location)

    out_ls = ftp_connection.retrlines('LIST', callback = identify_file_location)
    if out_ls != OUT_LS_SUCCESS:
        raise OSError("Failed listing the content of %s" % folder_location)

    return file_list, location_WMO_list.sort(), location_WBAN_list.sort()

def read_ish_history():
    """ Read the ish-history.TXT metadata file: it connects the WMO location to the WBAN location,
    location name, the country codes, the lattitude, longitude elevation, and range of dates.

    Returns a structured array
    """
    ish_filepath = os.path.join("Data", 'GSOD', 'ish-history.TXT')
    col_names = ["USAF", "WBAN", "STATION_NAME", "CTRY_WMO", "CTRY_FIPS", "ST", "CALL", "LAT", "LON", "ELEV", "BEGIN", "END"]
    starts = np.array([0,7,13,43,46,49,52,58,65,73,83,92])
    ends = np.hstack((starts[1:], 100)) # leave the space between values between columns since there is no sep
    widths = ends-starts
    # The datetime64 is not yet accepted by Pandas but will in the future
    #types = [np.int, np.int, "S31", "S3", "S3", "S3", "S5", np.int32, np.int32, np.int32, np.datetime64, np.datetime64]
    types = [np.int, np.int, "S31", "S3", "S3", "S3", "S5", np.int32, np.int32, np.int32, "S9", "S9"]

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

def unzip(zipped_filepath, target_dir = None):
    """ Unzip a file and save it with the same name in the same location or in
    the target directory if provided.
    """
    import gzip
    filepath = zipped_filepath.replace(".gz", "")
    if target_dir:
        filepath = os.path.join(target_dir, filepath)
    f_in = gzip.open(zipped_filepath, 'rb')
    f_out = open(filepath, 'wb')
    f_out.writelines(f_in)
    f_out.close()
    f_in.close()
    os.remove(zipped_filepath)
    
def info2filepath(year, location_WMO, location_WBAN):
    """ Convert a year and location code to a filename where that data is stored
    """
    return str(location_WMO)+"-"+ str(location_WBAN)+"-"+str(year)+".op"

def open_ftp(data_source = "NCDC"):
    """ Open the ftp connect of the appropriate ftp site. Return the connection.
    FIXME: Add test that it is not already open.
    """
    import ftplib
    if data_source == "NCDC":
        server = 'ftp.ncdc.noaa.gov'
        user = 'ftp'
        passwd = 'jrocher@enthought.com'
    else:
        raise NotImplementedError("The data source %s is currently not supported" % data_source)

    ftp_connection = ftplib.FTP(server, user, passwd)
    return ftp_connection

def datafile2pandas(filepath):
    """ Read a NCDC GSOD file into a pandas dataframe
    """
    sample_file = os.path.join(".", "sample_file.op")
    f = open(sample_file, "r")
    headers = f.readline()
    header_list = headers.strip().split()
    f.close()
    # Insert missing column names to header
    for mean_vals in ['TEMP', 'DEWP', 'SLP', 'STP', 'VISIB', 'WDSP']:
        header_list.insert(header_list.index(mean_vals)+1, mean_vals+"-count")

    df = pandas.read_table(filepath, sep="\s*", index_col=2, parse_dates = True,
                           names = header_list, skiprows = [0])
    return df

def collect_yearly_data(year, location_WMO, location_WBAN, data_source = 'NCDC'):
    """ Collect the data GSOD data file for specified location and specified
    year. Look locally for the file first. If it is not there, and its gzip
    version is not either, use the ftp connection to retrieve it from data
    source.
    """
    filename = info2filepath(year, location_WMO, location_WBAN)
    filepath = os.path.join("Data", "GSOD", "gsod_"+str(year), filename)
    if not os.path.exists(filepath):
        zipped_filepath = filepath+".gz"
        if os.path.exists(zipped_filepath):
            unzip(zipped_filepath)
        else:
            target_folder = "Data/GSOD/gsod_"+str(year)
            if not os.path.exists(target_folder):
                distutils.dir_util.mkpath(target_folder)
            # Download the file from the NCDC ftp site
            ftp_connection = open_ftp(data_source)
            folder_location = os.path.join('/pub/data/gsod',str(year))
            out_cwd = ftp_connection.cwd(folder_location)
            if out_cwd != OUT_CWD_SUCCESS:
                raise OSError("Unable to change to directory %s" % folder_location)
            file_obj = open(zipped_filepath, "w")
            ftp_connection.retrlines('RETR '+filename+".gz", file_obj.write)
            file_obj.close()
            unzip(zipped_filepath, target_dir = target_folder)
            ftp_connection.close()
    return datafile2pandas(filepath)

def search_station_codes(part_station_name, location_dict):
    """ Search for all station names that contain the string part_station_name
    and return their location codes. 
    FIXME: Add regex support
    """
    return [(key, location_dict[key]) for key in location_dict.keys()
            if key.lower().find(part_station_name.lower()) != -1]

def search_station(location_db, location_dict, part_station_name = None, WMO_location = None,
                       WBAN_location = None, country_code = None, state_code = None):
    """ Search for a station from part of its name, its location, its country code and/or its state.
    """
    mask = np.ones(len(location_db), dtype = np.bool)
    if part_station_name:
        match_station = location_db['STATION_NAME'] == part_station_name
        # Allow for partial station name
        #match_station = np.empty(len(mask), dtype = np.bool)
        #for i in xrange(len(mask)):
        #    match_station[i] = location_db['STATION_NAME'][i] in search_station_codes(part_station_name, location_dict)
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

    def search_station(self, part_station_name = None, WMO_location = None,
                       WBAN_location = None, country_code = None,
                       state_code = None):
        return search_station(self.location_db, self.location_dict,
                              part_station_name, WMO_location, WBAN_location,
                              country_code, state_code)

    def request_year(self, year=None, location_WMO=None, location_WBAN=None):
        """ Process a request.

        Inputs:
        - year, int. If no year is passed, choose the current one.
        - location WMO code and/or WBAN code, int, int. If no location is selected,
        raise an exception.

        Output:
        -
        - 
        """
        if year is None:
            year = datetime.datetime.today().year
        if location_WMO is None and location_WBAN is None:
            raise OSError("collect_yearly_data: no location specified")

        return collect_yearly_data(year, location_WMO, location_WBAN)
