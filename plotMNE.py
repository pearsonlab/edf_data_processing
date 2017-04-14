from __future__ import print_function

import argparse
import mne

# script to plot and visually test the edf file
# input the file name with start and end time.
# default start time is 0 sec and end time is 1800 sec

def main(input_fname, start_time, end_time):

    raw = mne.io.read_raw_edf(input_fname, montage=None, eog=None, misc=None, stim_channel=None, annot=None, annotmap=None, preload=False, verbose=None).crop(start_time,end_time).load_data()
    channels = ['Event', 'EKGR', 'EKGL']
    raw.drop_channels(channels)

    # pick the channels you want to plot
    # channels = []
    # raw.pick_channels(channels)

    print("plotting...")
    raw.plot(n_channels=4, order='type', scalings='auto', color='g', show_options=True, duration=15.0, show=True, block=True)

if __name__ == '__main__':
    
    # parser setup to get edf file location
    parser = argparse.ArgumentParser(description='Plot edf file. Must specify edf file location',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('edfloc', help='Location of edf file to print')
    parser.add_argument('--start_time', help='Start time (in seconds) for the duration you want to plot.', default=0)
    parser.add_argument('--end_time', help='End time (in seconds) for the duration you want to plot.', default=1800)

    args = parser.parse_args()

    edf_file = args.edfloc
    start = int(args.start_time)
    end = int(args.end_time)


    if not edf_file:
        sys.exit('Must provide an edf file location location')
    else:
        print("Plotting data between "+ str(start) +" secs and "+str(end)+" secs ...")
        print()
        main(edf_file, start, end)
