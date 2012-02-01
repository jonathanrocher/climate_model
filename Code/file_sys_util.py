import gzip
import tarfile
import os


def unzip(zipped_filepath):
    """ Unzip a file and save it with the same name in the same location.
    """
    #print "Unziping %s..." % zipped_filepath
    target_filepath = zipped_filepath.replace(".gz", "")
    f_in = gzip.open(zipped_filepath, 'rb')
    f_out = open(target_filepath, 'wb')
    f_out.write(f_in.read())
    f_out.close()
    f_in.close()
    os.remove(zipped_filepath)

def untar(filepath):
    """ Untar a tar file in its present location.
    FIXME: add inspection of data before untaring everything onto local disk...?
    """
    print "Extraction tar archive %s..." % filepath
    arch = tarfile.TarFile(filepath)
    target_folder = os.path.split(filepath)[0]
    arch.extractall(path = target_folder)
    arch.close()

