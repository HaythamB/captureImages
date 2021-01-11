#!/usr/bin/env python3
# load DuetWebAPI
import cv2
import random
import time
import os
import tarfile
import tempfile
import argparse

try:
    import DuetWebAPI as DWA
except ImportError:
    print("Python Library Module 'DuetWebAPI.py' is required. ")
    print("Obtain from https://github.com/DanalEstes/DuetWebAPI ")
    print("Place in same directory as script, or in Python libpath.")
    exit(-666)
# Check if running in a graphics console
if (os.environ.get('SSH_CLIENT')):
    print("This script MUST run on the graphics console, not an SSH session.")
    exit(-888)
    
def controlPoint(printerIn,controlPointIn):
    printerIn.gCode("G90 G1 X"+str(controlPointIn[0])+" Y"+str(controlPointIn[1]))
    return

# parse command line arguments
parser = argparse.ArgumentParser(description='Program to capture images of endstop moving 0.025 or 0.05mm per frame. Output  is saved to working directory in captures.tar.gz', allow_abbrev=False)

parser.add_argument('-duet',
                        type=str,
                        nargs=1,
                        default=['localhost'],
                        help='Name or IP address of Duet printer. You can use -duet=localhost if you are on the embedded Pi on a Duet3.')

parser.add_argument('-camera',
                        type=int,
                        nargs=1,
                        default=[0],
                        help='Index of /dev/videoN device to be used.  Default 0. ')
requiredNamed = parser.add_argument_group('required named arguments')
requiredNamed.add_argument('-cp',
                        type=float,
                        nargs=2,
                        required = True,
                        help="x y that will put 'controlled point' on carriage over camera.")

parser.add_argument('-repeat',
                        type=int,
                        nargs=1,
                        default=[10],
                        help="Set number of captures per offset (default is 10)")

args=vars(parser.parse_args())

duet                    = args['duet'][0]
camera                  = args['camera'][0]
controlPointLocation    = args['cp']
numImages               = args['repeat'][0]

# setup printer communication
printer = DWA.DuetWebAPI('http://'+duet)
if (not printer.printerType()):
    print('Device at '+duet+' either did not respond or is not a Duet V2 or V3 printer.')
    print('')
    exit(-222)
print('Unloading tools.')
printer.gCode("T-1")
while printer.getStatus() not in 'idle': time.sleep(0.5)
print('Moving to control point and running with 1st offset of 0.025mm')
controlPoint(printer, controlPointLocation)
while printer.getStatus() not in 'idle': time.sleep(0.5)

# setup capture device
try:
    print('Settting up webcam for capture..')
    cap = cv2.VideoCapture(camera)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS,25)
    cap.set(cv2.CAP_PROP_BUFFERSIZE,1)
except Exception as v1:
    print( 'Failed to open webcam stream' )
    print( str(v1) )
    exit(-1)
    
# create subdirectory to store capture files
try:
    print( 'Settting up temporary directory for captures..' )
    tempFolder = tempfile.TemporaryDirectory()
    path = tempFolder.name
except OSError:
    print('Failed to create capture directory \"'+path+'\".')
    cap.release()
    exit(-2)
    
direction = [1,1]

offsetAmount = 0.025
for i in range(1,numImages+1):
    offsetX = offsetAmount * random.choice(direction)
    offsetY = offsetAmount * random.choice(direction)
    print("\rMove #"+str(i)+": G91 G1 X" + str(offsetX) + " Y" + str(offsetY) + "  F12000 G90 ", end='', flush=True)
    printer.gCode("G91 G1 X" + str(offsetX) + " Y" + str(offsetY) + "  F12000 G90 ")
    printer.gCode("M400")
    for count in range (1,5):
        # capture some frames to discard to allow movement of printer
        (grabbed, frame) = cap.read()
    (grabbed, frame) = cap.read()
    filename = path+"/capture_"+str(offsetAmount)+"_{:03d}.jpg".format(i)
    cv2.imwrite(filename, frame)

print('')
print('Returning to control point and running with 2nd offset of 0.05mm')
controlPoint(printer,controlPointLocation)
offsetAmount = 0.05    
for i in range(1,numImages+1):
    offsetX = offsetAmount * random.choice(direction)
    offsetY = offsetAmount * random.choice(direction)
    print("\rMove #"+str(i)+": G91 G1 X" + str(offsetX) + " Y" + str(offsetY) + "  F12000 G90 ", end='', flush=True)
    printer.gCode("G91 G1 X" + str(offsetX) + " Y" + str(offsetY) + "  F12000 G90 ")
    printer.gCode("M400")
    for count in range (1,5):
        # capture some frames to discard to allow movement of printer
        (grabbed, frame) = cap.read()
    (grabbed, frame) = cap.read()
    filename = path+"/capture_"+str(offsetAmount)+"_{:03d}.jpg".format(i)
    cv2.imwrite(filename, frame)
print('')
print('Returning to control point.')
controlPoint(printer,controlPointLocation)

try:
    print( 'Compressing images into archive.')
    with tarfile.open('./capture_offsets.tar.gz','w') as archive:
        for i in os.listdir(path):
            archive.add(path+'/'+i, arcname='captures/'+i)
except Exception as c1:
    print( 'Cannot create tarfile.' )
    print( str(c1) )
    cap.release()
    exit(-3)
    
print( '\nCapture done. Compressed archive of captures has been created\n and temp folder and files have been deleted.')
print('')
print( 'Thanks for helping out!' )
cap.release()
exit()