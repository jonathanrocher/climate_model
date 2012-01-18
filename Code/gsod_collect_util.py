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

Background information:
a) locations:
- WMO location codes are also named 'USAF'. They are distinct from the WBAN location code. 
- Each station is identified by a unique set of (WMO, WBAN) codes.
"""
import datetime
import os
import numpy as np
import pandas
from distutils.dir_util import mkpath
import gzip
import ftplib

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

def unzip(zipped_filepath):
    """ Unzip a file and save it with the same name in the same location or in
    the target directory if provided.
    """
    print "Unziping %s..." % zipped_filepath
    target_filepath = zipped_filepath.replace(".gz", "")
    f_in = gzip.open(zipped_filepath, 'rb')
    f_out = open(target_filepath, 'wb')
    f_out.write(f_in.read())
    f_out.close()
    f_in.close()
    os.remove(zipped_filepath)

def info2filepath(year, location_WMO = None, location_WBAN = None):
    """ Convert a year and location code to a filename where that data is
    stored. If no location is provided, convert the year to the tar file 
    """
    if location_WMO is not None and location_WBAN is not None:
        # Force the format to have WMO loc on 6 char and WBAN on 5. 
        return "{0:0>6d}-{1:0>5d}-{2}.op".format(location_WMO, location_WBAN, year)
    elif location_WMO is None and location_WBAN is None:
        return "gsod_"+str(year)+".tar"
    else:
        raise ValueError("Only 1 location code is provided (WMO = %s, "
                         "WBAN = %s)." % (location_WMO, location_WBAN))
    
def open_ftp(data_source = "NCDC"):
    """ Open the ftp connect of the appropriate ftp site. Return the connection.
    FIXME: Add test that it is not already open.
    """
    if data_source == "NCDC":
        server = 'ftp.ncdc.noaa.gov'
        user = 'ftp'
        passwd = 'jrocher@enthought.com'
    else:
        raise NotImplementedError("The data source %s is currently not supported" % data_source)
    return ftplib.FTP(server, user, passwd)

def datafile2pandas(filepath):
    """ Read a NCDC GSOD file into a pandas dataframe
    """
    data_file_cols = ['STN---', 'WBAN', 'YEARMODA', 'TEMP', 'TEMP-count',
                      'DEWP', 'DEWP-count', 'SLP', 'SLP-count', 'STP',
                      'STP-count', 'VISIB', 'VISIB-count', 'WDSP',
                      'WDSP-count', 'MXSPD', 'GUST', 'MAX', 'MIN', 'PRCP',
                      'SNDP', 'FRSHTT']
    df = pandas.read_table(filepath, sep="\s*", index_col=2, parse_dates = True,
                           names = data_file_cols, skiprows = [0])
    return df

def datafolder2pandas(folderpath):
    """ Read a NCDC GSOD folder into a pandas panel
    """
    data = {}
    for filename in os.listdir(folderpath):
        if os.path.splitext(filename)[1] == ".op":
            file2load = os.path.join(folderpath, filename)
            print "Loading %s ..." % file2load
            key = filename[:13]
            data[key] = datafile2pandas(file2load)
        elif filename.endswith(".op.gz"):
            unzip(os.path.join(folderpath, filename))
            file2load = os.path.join(folderpath, os.path.splitext(filename)[0])
            print "Loading %s ..." % file2load
            key = filename[:13]
            data[key] = datafile2pandas(file2load)
    return pandas.Panel(data)

def retrieve_file(data_source, remote_target, local_filepath):
    """ Retrieve a file

    FIXME: issues with retrieving files: they end up corrupted. Use paramiko? Sniff 
    """
    remote_location, filename = os.path.split(remote_target)
    ftp_connection = open_ftp(data_source)
    out_cwd = ftp_connection.cwd(folder_location)
    if out_cwd != OUT_CWD_SUCCESS:
        raise OSError("Unable to change to directory %s" % remote_location)
    file_out = open(local_filepath, "w")
    ftp_connection.retrlines('RETR '+filename, file_out.write)
    file_out.close()
    ftp_connection.close()

def collect_year_at_loc(year, location_WMO, location_WBAN, data_source = 'NCDC'):
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
                print "Creating locally the folder %s." % target_folder
                mkpath(target_folder)
            # Download the file from the NCDC ftp site
            if data_source == 'NCDC':
                remote_location = os.path.join('/pub/data/gsod', str(year))
            remote_target = os.path.join(remote_location, filename)
            retrieve_file(data_source, remote_target, zipped_filepath)
            unzip(zipped_filepath)
    return datafile2pandas(filepath)

def collect_year(year):
    """ Collect the GSOD data file for all locations for the specified
    year. Look locally for the tar file first. If it is not there, and its gzip
    version is not either, use the ftp connection to retrieve it from data
    source.
    """
    filename = info2filepath(year)
    local_filepath = os.path.join("Data", "GSOD", filename)
    local_folderpath = local_filepath.replace(".tar", "")
    if not os.path.exists(local_folderpath):
        # Folder not already present
        if not os.path.exists(local_filepath):
            # tar file not present either: download it!
            if data_source == 'NCDC':
                remote_location = os.path.join('/pub/data/gsod',str(year))
            remote_target = os.path.join(remote_location, filename)
            retrieve_file(data_source, remote_target, local_filepath)
        
        untar(local_filepath)
        
    return datafolder2pandas(local_folderpath)

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
    L = len(location_db)
    mask = np.ones(L, dtype = np.bool)
    if part_station_name:
        # Allow for partial station name
        match_station_idx = [idx for idx,name in enumerate(location_db['STATION_NAME'])
                             if part_station_name.lower() in name.lower()]
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

    def search_station(self, part_station_name = None, location_WMO = None,
                       location_WBAN = None, country_code = None,
                       state_code = None):
        return search_station(self.location_db, self.location_dict,
                              part_station_name, location_WMO, location_WBAN,
                              country_code, state_code)

    def request_year(self, year=None, part_station_name=None,
                     location_WMO=None, location_WBAN=None,
                     country=None, state=None):
        """ Process a request for data.

        Inputs:
        - year, int. If no year is passed, choose the current one.
        - location WMO code and/or WBAN code, int, int. If no location is selected,
        collect the yearly data for all locations.

        Output:
        - pandas data structure: 2D DataFrame if only one location is
        requested, 3D (panel) if multiple locations are requested
        """
        if year is None:
            year = datetime.datetime.today().year
            print "No year was provided: using the current one (%s)" % year
            
        no_location = (location_WMO is None and location_WBAN is None
                       and part_station_name is None and country is None and
                       state is None)
        if no_location:
            # Requested all data for the year that is at all locations
            return collect_year(year)
        else:
            filtered = search_station(self.location_db, self.location_dict,
                                      part_station_name, location_WMO, location_WBAN,
                                      country, state)
            if len(filtered) == 1:
                return collect_year_at_loc(year, location_WMO, location_WBAN)
            else:
                data = {}
                for layer in filtered:
                     df = collect_year_at_loc(year, layer['USAF'], layer['WBAN'])
                     # reindex over the entire year in case there are missing values
                     df = df.reindex(DateRange(start = '1/1/%s' % year, end = '31/12/%s' % year,
                                              offset = pandas.datetools.day))
                     data[str(location_WMO)+"-"+str(location_WBAN)] = df
                return Panel(data)
