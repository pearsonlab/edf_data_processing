from __future__ import print_function

import argparse
import shutil
import glob


# move the required .chn files to another folder in order to write them as a EDF file

def main(dest_folder_loc, chunk_file_loc, chunk_num):
    chunk_files = str(chunk_file_loc)+'/*chunk-'+str(chunk_num)+'.chn'
    folder = glob.glob(chunk_files)

    for i in range(len(folder)):
        shutil.move(folder[i], dest_folder_loc)
        if(i == len(folder)-1):
            print("All the files moved to destination folder")


if __name__ == '__main__':
	# parser setup to get edf file location
    parser = argparse.ArgumentParser(description='move chunk files to another folder for edf creation. Must specify the destination folder location',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('destloc', help='Location of the destination folder to move the chunk file to')
    parser.add_argument('--chunkloc', help = 'Location of the chunk file')
    parser.add_argument('--chunknum', help = 'Chunk number')
    args = parser.parse_args()

    dest_folder_loc = args.destloc
    chunk_file_loc = args.chunkloc
    chunk_num = args.chunknum

    if not dest_folder_loc and not chunk_file_loc and not chunk_num:
        sys.exit('Must specify the destination folder location, chunk files location and chunk number')
    else:
        main(dest_folder_loc, chunk_file_loc, chunk_num)