""" Supporting module dealing with retrieving remote files from data sources. 
"""

from urllib import urlretrieve
import os.path
import warnings

def info2filepath(year, location_WMO = None, location_WBAN = None, data_source = 'NCDC'):
    """ Convert a year and location code to a filename where that data is
    stored. If no location is provided, convert the year to the tar file 
    """
    if data_source == 'NCDC':
        if location_WMO is not None and location_WBAN is not None:
            # Force the format to have WMO loc on 6 char and WBAN on 5. 
            return "{0:0>6}-{1:0>5}-{2}.op".format(location_WMO, location_WBAN, year)
        elif location_WMO is None and location_WBAN is None:
            return "gsod_"+str(year)+".tar"
        else:
            raise ValueError("Only 1 location code is provided (WMO = %s, "
                             "WBAN = %s)." % (location_WMO, location_WBAN))
    else:
        raise NotImplementedError("The data source %s is currently not supported" % data_source)


def retrieve_file(data_source, remote_target, local_filepath):
    """ Retrieve a file from a data source. 

    ENH: Add sniffing capabilities to test what type of connection it is. Use Paramiko if SFTP.
    """
    print "Attempting to retrieve %s from the servers..." % remote_target
    if data_source == "NCDC":
        url_base = "ftp://ftp.ncdc.noaa.gov/pub/data/gsod"
        url = os.path.join(url_base, remote_target)
        try:
            received = urlretrieve(url, local_filepath)
        except IOError as e:
            received = False
        if not received:
            warnings.warn("Failed receiving the file %s from the server." % url)
    else:
        raise NotImplementedError("Unable to retrieve data from %s" % data_source)
