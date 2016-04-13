MODEL_PI2KF = 1
MODEL_TAVBOT = 2

pCenter=0
tCenter=0

model = MODEL_TAVBOT

if model == MODEL_PI2KF:
    pCenter = -4
    tCenter = 2
    MOT2BOT_NAME = 'PI2KF'
else:
    MOT2BOT_NAME = 'Tavbot'
    pCenter = 11
    tCenter = -61

# Raspberry Pi Face Recognition Treasure Box Configuration
# Copyright 2013 Tony DiCola 

# Threshold for the confidence of a recognized face before it's considered a
# positive match.  Confidence values below this threshold will be considered
# a positive match because the lower the confidence value, or distance, the
# more confident the algorithm is that the face was correctly detected.
# Start with a value of 3000, but you might need to tweak this value down if 
# you're getting too many false positives (incorrectly recognized faces), or up
# if too many false negatives (undetected faces).
POSITIVE_THRESHOLD = 3300.0

# File to save and load face recognizer model.
TRAINING_FILE = 'training.xml'

# Directories which contain the positive and negative training image data.
POSITIVE_DIR = './training/positive'
NEGATIVE_DIR = './training/negative'

# Size (in pixels) to resize images for training and prediction.
# Don't change this unless you also change the size of the training images.
FACE_WIDTH  = 92
FACE_HEIGHT = 112

# Face detection cascade classifier configuration.
# You don't need to modify this unless you know what you're doing.
# See: http://docs.opencv.org/modules/objdetect/doc/cascade_classification.html
HAAR_FACES         = 'haarcascade_frontalface_alt.xml'
HAAR_SCALE_FACTOR  = 1.3
HAAR_MIN_NEIGHBORS = 3
HAAR_MIN_SIZE      = (50, 50)

# Filename to use when saving the most recently captured image for debugging.
DEBUG_IMAGE = 'capture.pgm'

def get_camera():	
	# Camera to use for capturing images.
	# Use this code for capturing from the Pi camera:
	import picam
	return picam.OpenCVCapture()
	# Use this code for capturing from a webcam:
	# import webcam
	# return webcam.OpenCVCapture(device_id=0)
