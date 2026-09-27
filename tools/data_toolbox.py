# rev 1.2

import glob
import pickle

# PY3-PORT: the original imported both cPickle and pickle and used them
# interchangeably. In Python 3, `pickle` already is the C implementation.

# PY3-PORT: pickle streams are ALWAYS bytes in Python 3, including protocol 0.
# The original 'asc' mode opened the file in text mode, which raises TypeError
# on Python 3. Both modes now open binary; only the protocol number differs.
_PY2_STR_ENCODING = 'latin1'


def load_pickle(path):
    """Load a pickle written by either Python 2 or Python 3.

    PY3-PORT: added. Python 2 pickled `str` as bytes, so historical .pys/.pyd
    files either raise UnicodeDecodeError on Python 3 or come back with every
    string as bytes. latin-1 maps bytes 0-255 one-to-one, so numpy arrays and
    ASCII dict keys both survive the round trip. It is a no-op for pickles
    written by Python 3, which store str with unicode opcodes.

    Use this instead of pickle.load() anywhere that touches historical data.
    """
    with open(path, 'rb') as fil:
        data = fil.read()
    try:
        return pickle.loads(data)
    except (UnicodeDecodeError, TypeError):
        return pickle.loads(data, encoding=_PY2_STR_ENCODING)

_file_mode_map = {'asc': 'b', 'bin': 'b'}  # PY3-PORT: 'asc' was text mode
_pickle_mode_map = {'asc': 0, 'bin': 1}


def writeDictToFile(dict, filename):
    if filename.find('.txt') != -1 or filename.find('.asc') != -1:
        d = dictToAscii(dict)
        stringToFile(d, filename)
    elif filename.find('.pys') != -1:
        mode = 'bin'
        fil = open(filename, 'w' + _file_mode_map[mode])
        pickle.dump(dict, fil, _pickle_mode_map[mode])
        fil.close()
    elif filename.find('.pyd') != -1:
        mode = 'asc'
        fil = open(filename, 'w' + _file_mode_map[mode])
        pickle.dump(dict, fil, _pickle_mode_map[mode])
        fil.close()
    else:
        filename = filename + '.pys'
        mode = 'bin'
        fil = open(filename, 'w' + _file_mode_map[mode])
        pickle.dump(dict, fil, _pickle_mode_map[mode])
        fil.close()
        # interacts with __get_state__


def keysFromDict(dict, keys=None):
    """extract any number of keys from a dictionary"""
    d = {}
    if keys == None:  # return entire dict
        return dict
    else:
        if not hasattr(keys, '__iter__'):  # only one key
            d[keys] = dict[keys]
        else:  # tuple of keys
            for key in keys:
                d[key] = dict[key]
    return d


def pickleFile2Dict(path, keys=None):
    """(path, [(keys)]) Extracts the whole or a key of a dictionary from a pickled file"""
    dict = {}
    try:
        # PY3-PORT: was open(path, 'rU') + pickle.load(). 'U' was removed in
        # 3.11, and text mode cannot carry a pickle stream at all in Python 3.
        dict = load_pickle(path)
    except IOError:
        print('Error importing data')
    d = keysFromDict(dict, keys)
    return d


def blub(value):
    if hasattr(value, '__iter__'):
        blub(value.subitem)


def dict2Ascii(dict, keys=None):
    """Converts a dictionary or parts of it to a string"""
    try:  # if there is a doc string put it up front
        datastring = '#__doc__\n' + dict['__doc__'] + '\n'
        del dict['__doc__']
    except:
        datastring = ''
    for key, value in list(dict.items()):
        datastring += '#' + key + '\n'  # header for each key
        # blub(value)
        if hasattr(value, '__iter__'):  # array?
            if value != []:
                if hasattr(value[0], '__iter__'):  # 2d array?

                    # 2d array
                    for i in range(value.shape[0]):
                        for j in range(value.shape[1]):
                            datastring += (str(value[i, j]) + ', ')
                            if j == value.shape[1] - 1:
                                datastring += '\n'

                else:
                    # 1d array
                    try:
                        n = value.shape[0]
                    except:
                        n = len(value)
                    for i in range(n):
                        datastring += (str(value[i]) + '\n')
            else:
                datastring = datastring + ' ' + '/n'

        else:
            # value no array
            datastring = datastring + str(value) + '\n'
    return datastring


# def write(item, string):
#    if hasattr(value,'__iter__'): # array?
#        for subitem in item:
#            write(subitem, string)
#    else: 
#        string=string+str(value)+'\n'
#    return string

def string_to_file(datastring, path, mode='a'):
    """(adds) datastring to file"""
    try:
        f = open(path, mode)
        try:
            f.write(datastring)
        finally:
            f.close()
    except IOError:
        print('Error exporting data')
        return False
    return True


def file_to_string(path, mode='r'):
    """reads datastring from file"""
    try:
        f = open(path, mode)
        try:
            datastring = f.read()
        finally:
            f.close()
    except IOError:
        print('Error reading data')
        return None
    return datastring


def string_in_files_2_file(source_path, dest_path='temp.txt', r_mode='r', w_mode='w', source_suffix='txt',
                           seperator=', '):
    try:
        datastring = ''
        files = glob.glob(source_path + '*.' + source_suffix)
        for file in files:
            datastring += str(file) + seperator + file_to_string(file, mode=r_mode)
        string_to_file(datastring, dest_path, w_mode)
    except IOError:
        print('Error')


# def list_to_file(list, path, separator=', '):
#    """writes simple list to file"""
#    datastring = ''
#    for m in range(len(list)):
#        datastring = datastring + separator + str(list[m])
#    datastring = datastring.strip(separator) + '\n'
#    string_to_file(datastring, path)
#
# def file_to_list(path, seperator=', '):
#    """reads list from file"""
#    datastring = file_to_string()
#    for m in range(len(list)):
#        datastring = datastring + ', ' + str(list[m])
#    datastring = datastring.strip(', ') + '\n'
#    string_to_file(datastring, path)
#    return list

def pickleFile2AscFile(sourcefile, targetfile=None, keys=None):
    """dump pickle from pickled file to ascii file (source, [target], [(keys)])"""
    dict = {}
    dict = pickleFile2Dict(sourcefile, keys)
    datastring = dict2Ascii(dict, keys)
    if targetfile == None:
        String2File(datastring, sourcefile + '.asc')
    else:
        String2File(datastring, targetfile)
