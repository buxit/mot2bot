"""Raspberry Pi Face Recognition Treasure Box
Face Detection Helper Functions
Copyright 2013 Tony DiCola

Functions to help with the detection and cropping of faces.
"""
import cv2
import fnmatch
import os
import re
import numpy as np
import csv

import config

haar_faces = None
MEAN_FILE = 'mean.png'

def init():
    global haar_faces
    print "cv2.CascadeClassifier(config.HAAR_FACES)"
    haar_faces = cv2.CascadeClassifier(config.HAAR_FACES)
    print haar_faces


def detect_single(image):
    global haar_faces
    """Return bounds (x, y, width, height) of detected face in grayscale image.
       If no face or more than one face are detected, None is returned.
    """
    faces = haar_faces.detectMultiScale(image,
                            scaleFactor=config.HAAR_SCALE_FACTOR,
                            minNeighbors=config.HAAR_MIN_NEIGHBORS,
                            minSize=config.HAAR_MIN_SIZE,
                            flags=0) #flags=cv2.CASCADE_SCALE_IMAGE)
    if len(faces) != 1:
            if len(faces) > 1:
                    print len(faces)," faces."
            return None
    return faces[0]

def crop(image, x, y, w, h):
    """Crop box defined by x, y (upper left corner) and w, h (width and height)
    to an image with the same aspect ratio as the face training data.  Might
    return a smaller crop if the box is near the edge of the image.
    """
    crop_height = int((config.FACE_HEIGHT / float(config.FACE_WIDTH)) * w)
    midy = y + h/2
    y1 = max(0, midy-crop_height/2)
    y2 = min(image.shape[0]-1, midy+crop_height/2)
    return image[y1:y2, x:x+w]

def resize(image):
	"""Resize a face image to the proper size for training and detection.
	"""
	return cv2.resize(image, (config.FACE_WIDTH, config.FACE_HEIGHT), interpolation=cv2.INTER_LANCZOS4)

def walk_files(directory, match='*'):
	"""Generator function to iterate through all files in a directory recursively
	which match the given filename match parameter.
	"""
	for root, dirs, files in os.walk(directory):
		for filename in fnmatch.filter(files, match):
			yield os.path.join(root, filename)

def prepare_image(filename):
	"""Read an image as grayscale and resize it to the appropriate size for
	training the face recognition model.
	"""
	return resize(cv2.imread(filename, cv2.IMREAD_GRAYSCALE))

def normalize(X, low, high, dtype=None):
	"""Normalizes a given array in X to a value between low and high.
	Adapted from python OpenCV face recognition example at:
	  https://github.com/Itseez/opencv/blob/2.4/samples/python2/facerec_demo.py
	"""
	X = np.asarray(X)
	minX, maxX = np.min(X), np.max(X)
	# normalize to [0...1].
	X = X - float(minX)
	X = X / float((maxX - minX))
	# scale to [low...high].
	X = X * (high-low)
	X = X + low
	if dtype is None:
		return np.asarray(X)
	return np.asarray(X, dtype=dtype)

def train(model, num_to_label, label_to_num, speak):
	print "Reading training images..."
	speak("Analysiere Gesichter ...");
	faces = []
	labels = []
	labels_count = 0
	pos_count = 0
	neg_count = 0
	label_to_num.clear()
	num_to_label.clear()
	# Read all positive images
	for filename in walk_files(config.POSITIVE_DIR, '*.pgm'):
		m = re.split('/', filename)
		label = m[len(m)-2]
		if not label in label_to_num:
			labels_count += 1
			label_to_num[label] = labels_count
			num_to_label[str(labels_count)] = label
		print filename, 'l=', label, labels_count
		faces.append(prepare_image(filename))
		labels.append(labels_count)
		pos_count += 1
	with open('labels.csv', 'wb') as csvfile:
		csvwriter = csv.writer(csvfile)
		for key, val in label_to_num.items():
			csvwriter.writerow([key, val])

	#for filename in walk_files(config.NEGATIVE_DIR, '*.pgm'):
	#	print filename
	#	faces.append(prepare_image(filename))
	#	labels.append(0)
	#	neg_count += 1
	print 'Read', pos_count, 'positive images and', neg_count, 'negative images.'
	print label_to_num
	print num_to_label

	# Train model
	print 'createEigenFaceRecognizer() ...'
	# model = cv2.createEigenFaceRecognizer()
	print 'Training model...'
	model.train(np.asarray(faces), np.asarray(labels))
	speak("{0} Gesichter analysiert. Speichere Daten.".format(pos_count+neg_count));
	print 'Saving model...'

	# Save model results
	model.save(config.TRAINING_FILE)
	print 'Training data saved to', config.TRAINING_FILE
	# Save mean and eignface images which summarize the face recognition model.
	mean = model.getMat("mean").reshape(faces[0].shape)
	cv2.imwrite(MEAN_FILE, normalize(mean, 0, 255, dtype=np.uint8))
	speak("Fertig.")
	# eigenvectors = model.getMat("eigenvectors")
	# pos_eigenvector = eigenvectors[:,0].reshape(faces[0].shape)
	# cv2.imwrite(POSITIVE_EIGENFACE_FILE, normalize(pos_eigenvector, 0, 255, dtype=np.uint8))
	# neg_eigenvector = eigenvectors[:,1].reshape(faces[0].shape)
	# cv2.imwrite(NEGATIVE_EIGENFACE_FILE, normalize(neg_eigenvector, 0, 255, dtype=np.uint8))
