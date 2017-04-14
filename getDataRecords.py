import math
import os
import argparse

# script to check the number of data records in an EDF file

def main(file):

	# number of bytes in whole file
	numBytes = os.path.getsize(file)

	with open(file, 'r+b') as thisFile:	
		# number of bytes in header
		thisFile.read(184)
		headerBytes = int(thisFile.read(8).decode("utf-8").strip())
		thisFile.read(44)
		numRec = int(thisFile.read(8).decode("utf-8").strip())
		thisFile.read(8)
		# recDur = float(thisFile.read(8).decode("utf-8").strip())
		numSigs = int(thisFile.read(4).decode("utf-8").strip())

		thisFile.read(numSigs*(16+80+8+8+8+8+8+80))

		numSamps = []
		for i in range(numSigs):
			numSamps.append(int(thisFile.read(8).decode("utf-8").strip()))

	# required bytes for calculation
	remBytes = numBytes - headerBytes

	# If the number of data record is not known
	# if(numRec < 0):
	R = sum(numSamps) * 2 # length of record for all the samples
	numRecs = math.floor(remBytes/R) # number of records

	print("data records from the file: ", numRec)
	print("The number of data records is: ", numRecs)

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='get the number of data records for edf file', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	
	parser.add_argument('edfFileLocation', help='File name and location for final edf file , eg:(directory/filename.edf)')
	
	args = parser.parse_args()
	edf_file = args.edfFileLocation

	# checking if all the arguments are given
	if not edf_file:
		sys.exit('Must provide input edf file location.')
	else:
		main(edf_file)
