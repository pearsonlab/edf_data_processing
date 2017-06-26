#!/usr/bin/env python
# run "ln -s <this-script's-location> /usr/local/bin/edf_split" to make this script executable from anywhere
# read an edf header and print contents to stdout
from __future__ import print_function

import os
import argparse
from datetime import date, time, timedelta
import datetime

def head_parser(thisFile, file_size):
    header = {}
    header['filename'] = thisFile.name.split('/')[-1]
    # extract info from header
    thisFile.read(168)
    file_given_date = tuple(int(i) for i in thisFile.read(8).decode("utf-8").strip().split('.')) # makes tuple for day, month, year 
    file_start_date = file_given_date[::-1] # getting the date in year, month, day format
    file_date = date(file_start_date[0], file_start_date[1], file_start_date[2]) # getting the date in python date format
    
    header['start_date'] = file_date
    header['start_time'] = time(*tuple(int(i) for i in thisFile.read(8).decode("utf-8").strip().split('.')))  # makes time object of hour, minute, second
    header['head_length'] = int(thisFile.read(8).decode("utf-8").strip())
    thisFile.read(44)
    header['numRecs'] = int(thisFile.read(8).decode("utf-8").strip())
    header['recDur'] = float(thisFile.read(8).decode("utf-8").strip())
    header['numSigs'] = int(thisFile.read(4).decode("utf-8").strip())
    header['sigLabels'] = []
    for i in range(header['numSigs']):
        header['sigLabels'].append(thisFile.read(16).decode("utf-8").strip())
    thisFile.read(header['numSigs']*(80))
    
    header['phyDimension'] = []
    for i in range(header['numSigs']):
        header['phyDimension'].append(thisFile.read(8).decode("utf-8").strip())
    
    header['phyMinimum'] = []
    for i in range(header['numSigs']):
        header['phyMinimum'].append(thisFile.read(8).decode("utf-8").strip())
    header['phyMaximum'] = []
    for i in range(header['numSigs']):
        header['phyMaximum'].append(thisFile.read(8).decode("utf-8").strip())
    
    header['digMinimum'] = []
    for i in range(header['numSigs']):
        header['digMinimum'].append(thisFile.read(8).decode("utf-8").strip())
    header['digMaximum'] = []
    for i in range(header['numSigs']):
        header['digMaximum'].append(thisFile.read(8).decode("utf-8").strip())

    thisFile.read(header['numSigs']*(80))

    header['numSamps'] = []
    for i in range(header['numSigs']):
        header['numSamps'].append(int(thisFile.read(8).decode("utf-8").strip()))

    # in case number of data records is unknown (-1) from the header
    if(header['numRecs'] < 0):
        numBytes = file_size - header['head_length'] # number of bytes for data content
        R = sum(header['numSamps']) * 2 # length of record for all the samples
        header['numRecs'] = floor(numBytes/R) # number of data records

    return header

if __name__ == '__main__':
    # set up and parse options
    parser = argparse.ArgumentParser(description='Read an edf header and print contents to stdout',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('edfloc', help='Location of edf file to convert')
    args = parser.parse_args()

    edf_file = args.edfloc

    # getting file_size in bytes
    file_size = os.path.getsize(edf_file)

    # reads an edf file and splits the signals into a folder of binary files (one for each signal)
    with open(edf_file, 'rb') as thisFile: # open edf file as read-binary
        # parse header
        header = head_parser(thisFile, file_size)
        
        # print header bits
        print("File name :", header['filename'])
        start = datetime.datetime.combine(header['start_date'], header['start_time'])
        print("File start:", start.strftime("%B %d, %Y  %H:%M:%S"))
        duration = timedelta(seconds=header['recDur'] * header['numRecs'])
        print("File end:  ", (start + duration).strftime("%B %d, %Y  %H:%M:%S"))
        print("Number of channels:", header['numSigs'])
