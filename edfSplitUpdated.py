#!/usr/bin/env python
# run "ln -s <this-script's-location> /usr/local/bin/edf_split" to make this script executable from anywhere
from __future__ import print_function

import argparse
from urllib.parse import urlparse
import os
import sys
import boto3
from boto3.s3.transfer import S3Transfer
import threading
import shutil
import tempfile
import json
import math
from math import floor
from datetime import date

class Progress(object):
    def __init__(self, filename):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._lock = threading.Lock()

    def __call__(self, bytes_amount):
        with self._lock:
            self._seen_so_far += bytes_amount
            relprogress = int((self._seen_so_far / self._size) * 50)
            sys.stdout.write("\r[" + "=" * relprogress + " " * (50 - relprogress) + "]" + str(relprogress*2) + "%")


def local_and_s3_writer(edf, header, local, s3):
    # write locally
    localpaths = local_writer(edf, header, local, s3)
    # connect to s3
    try:
        transfer = S3Transfer(boto3.client('s3', 'us-east-1'))
        print ('Connected to S3')
    except:
        print ('Unable to connect to S3!  Make sure AWS credentials are stored as environment variables.')
        return


    # connect to specific s3 bucket after checking path validity
    parsed_s3 = urlparse(s3)
    if parsed_s3.scheme != 's3':
        print ("Must provide valid S3 URI! (starts with 's3://')")
        return

    print ("Uploading %i files:" % len(localpaths))
    i = 1
    for path in localpaths:
        if parsed_s3.path != '/': # if path beyond bucket is specified
            fname = os.path.join(parsed_s3.path[1:], path.split('/')[-2], path.split('/')[-1]) # take s3 directory, local folder, and filename
        else:
            fname = os.path.join(path.split('/')[-2], path.split('/')[-1]) # take local folder, and filename
            print("testing FILE!!!!!!!   ", fname)
        print ("File %i:" % i)
        transfer.upload_file(path, parsed_s3.netloc, fname, callback=Progress(path))

        sys.stdout.write('\n')
        i += 1
    print ("Upload complete!")
    return

def local_writer(edf, header, local, s3):
    # create directory for byte files
    store_path = os.path.join(local, os.path.basename(header['filename']).split('.')[0], '')
    if not os.path.exists(store_path):
        os.makedirs(store_path)

    edf.seek(header['head_length'])  # find beginning of data

    # make list that marks the indeces of where to cut a data record buffer per signal
    sigBounds = list(header['numSamps'])
    for i in range(header['numSigs']):  # mark index where each signal starts and ends within each record
        if i == 0:
            sigBounds[i] = tuple((0, sigBounds[i]*2))
        else:
            sigBounds[i] = tuple((sigBounds[i-1][1], sigBounds[i-1][1]+sigBounds[i]*2))

    print ("Writing data locally...")
    maxprogress = float((header['numRecs'])*(header['numSigs']))
    # write data from edf to the file
    chunk_rec = 0  # number of record within chunk
    chunk_num = 0  # current chunk number
    all_files = []
    files = []
    recsRemaining = header['numRecs']
    for i in range(header['numRecs']):  # iterate over records
        if chunk_rec == header['recsPerChunk']:
            chunk_rec = 0
            chunk_num += 1
            recsRemaining = recsRemaining - header['recsPerChunk']
        if chunk_rec == 0:  # start new files if new chunk
            for f in files:
                f.close()
            all_files += files
            files = []
            for j in range(header['numSigs']):
                files.append(open(store_path+header['sigLabels'][j] +
                                  '_chunk-' + str(chunk_num) +
                                  '.chn', 'wb'))  # create file for each signal
                file_head = dict(header)  # copy header info
                # modify header info for this channel
                file_head.pop('head_length')
                file_head.pop('numRecs')
                file_head.pop('recDur')
                file_head.pop('numSigs')
                file_head.pop('sigLabels')
                file_head.pop('numSamps')
                file_head['read_instruct'] = ("To load this file properly, " +
                                              "use json.loads(f.readline()) " +
                                              "to get the header, then use " +
                                              "np.fromstring(f.read(),'<i2')" +
                                              " to get the values." +
                                              "Note: if chunk is from end of" +
                                              " file, it may not be the full" +
                                              " chunk size.")
                hr, mnt, sec = header['start_time']
                mnt += header['maxChunkTime'] * chunk_num
                hr += (mnt / 60)
                mnt = (mnt % 60)

                sec += 60*(mnt%1)
                mnt += sec//60
                sec = sec%60
                file_head['start_date'] = header['start_date']
                file_head['start_time'] = (floor(hr), floor(mnt), sec)
                file_head['sigLabel'] = header['sigLabels'][j]
                file_head['sampsPerRecord'] = header['numSamps'][j]
                file_head['phyDimension'] = header['phyDimension'][j]
                file_head['phyMinimum'] = header['phyMinimum'][j]
                file_head['phyMaximum'] = header['phyMaximum'][j]
                file_head['digMinimum'] = header['digMinimum'][j]
                file_head['digMaximum'] = header['digMaximum'][j]
                file_head['chunk'] = chunk_num
                file_head['recDur'] = header['recDur']
                file_head['numRecs'] = header['numRecs']
                file_head['recsRemaining'] = recsRemaining
                if(recsRemaining < header['recsPerChunk']):
                	file_head['chunkDuration'] = (recsRemaining*header['recDur'])
                else:
                	file_head['chunkDuration'] = (header['recsPerChunk']*header['recDur'])
                files[j].write(json.dumps(file_head).encode('utf-8'))
                files[j].write('\n'.encode('utf-8'))

        record = edf.read(sum(header['numSamps'])*2)  # read an entire record
        for j in range(header['numSigs']):  # iterate over signals within records
            # grab and write signal data from record
            files[j].write(record[sigBounds[j][0]:sigBounds[j][1]])
        chunk_rec += 1

        # progress bar
        currprogress = float((i+1)*header['numSigs'])
        relprogress = int(50*currprogress/maxprogress)
        sys.stdout.write("\r[" + "=" * relprogress + " " * (50 - relprogress) + "]" +  str(relprogress*2) + "%")

    for f in files:
        f.close() # close files
    all_files += files # add incomplete chunks

    print ("\nLocal write complete!")

    # create list for all file paths
    filepaths = [f.name for f in all_files]
    # for i in range(header['numSigs']):
    #     filepaths.append(store_path+header['sigLabels'][i]+'.bin')
    return filepaths

def s3_writer(edf, header, local, s3):
    try:
        tmp_dir = tempfile.mkdtemp()
        local_and_s3_writer(edf, header, tmp_dir, s3)
    finally:
        shutil.rmtree(tmp_dir)

def head_parser(thisFile, chunk_size, file_size, patientID, day):
    header = {}
    header['filename'] = thisFile.name.split('/')[-1]
    # extract info from header
    thisFile.read(168)
    file_given_date = tuple(int(i) for i in thisFile.read(8).decode("utf-8").strip().split('.')) # makes tuple for day, month, year 
    file_start_date = file_given_date[::-1] # getting the date in year, month, day format
    file_date = date(file_start_date[0], file_start_date[1], file_start_date[2]) # getting the date in python date format
    
    surgery_date = date(file_start_date[0], file_start_date[1], day)
    day_index = (file_date-surgery_date).days # getting the day index for the date to be stored in datebase
    
    header['start_date'] = (patientID, 1, day_index)
    header['start_time'] = tuple(int(i) for i in thisFile.read(8).decode("utf-8").strip().split('.'))  # makes tup of hour, minute, second
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

    header['recsPerChunk'] = floor(chunk_size / (header['recDur'] / 60)) #whole number of records per chunk
    header['maxChunkTime'] = (header['recsPerChunk']*header['recDur'])/60
    return header

if __name__ == '__main__':
    # set up and parse options
    parser = argparse.ArgumentParser(description='Split edf into files for each channel with proprietary headers. ' +
                                                  'Must specify location for at least one of --local and --s3 flags ' +
                                                  'If only s3 loc is specified, files are written to a temporary ' +
                                                  'directory, which is deleted after the s3 upload is complete.',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('edfloc', help='Location of edf file to convert')
    parser.add_argument('--local', help='Location to store folder of binary files (One for each chunk per signal) on the local machine.')
    parser.add_argument('--s3', help='URI formatted location to store binary folder on S3.  Only works if you have AWS ' +
                                    'credentials stored as environment variables.')
    parser.add_argument('--subject', help='patient ID in terms of year. eg: 2002')
    parser.add_argument('--day', help='day of the surgery. eg: 12')
    parser.add_argument('--chunk', help='Chunk size (in number of records) to break recordings by', default=60)
    args = parser.parse_args()

    edf_file = args.edfloc
    local_loc = args.local
    s3_loc = args.s3
    patientID = int(args.subject)
    day = int(args.day)
    chunk_size = int(args.chunk) #to number of records

    # set up file writer
    if not s3_loc and not local_loc and not patientID and not day:
        sys.exit('Must provide an output location (either local (--local), S3 (--s3), or both) as well as patientID and day.')
    elif s3_loc and local_loc:
        writer = local_and_s3_writer
    elif s3_loc:  # only local directory provided
        writer = s3_writer
    else:
        writer = local_writer

    # getting file_size in bytes
    file_size = os.path.getsize(edf_file)

    # reads an edf file and splits the signals into a folder of binary files (one for each signal)
    with open(edf_file, 'rb') as thisFile: # open edf file as read-binary
        # parse header
        header = head_parser(thisFile, chunk_size, file_size, patientID, day)

        # write to binary files
        writer(thisFile, header, local_loc, s3_loc)
