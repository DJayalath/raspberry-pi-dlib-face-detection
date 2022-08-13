# import necessary packages
from multiprocessing import Manager
from multiprocessing import Process
# from imutils.video import VideoStream
from src.common.package.config import application
from src.common.package.camera.capture import Capture as _capture
from src.common.package.frame.action import Action as _frame
from src.dlib.package.dlib.dlib import Dlib
_dlib = Dlib()
from pid import PID
import pantilthat as pth
import argparse
import signal
import time
import sys
import cv2
# define the range for the motors
servoRange = (-90, 90)

# function to handle keyboard interrupt
def signal_handler(sig, frame):
	# print a status message
	print("[INFO] You pressed `ctrl + c`! Exiting...")
	# disable the servos
	pth.servo_enable(1, False)
	pth.servo_enable(2, False)
	# exit
	sys.exit()

def obj_center(objX, objY):
	# signal trap to handle keyboard interrupt
	signal.signal(signal.SIGINT, signal_handler)
	# start the video stream and wait for the camera to warm up
	# Initialise capture
	capture = _capture(src=application.CAPTURING_DEVICE,
						use_pi_camera=application.USE_PI_CAMERA,
						resolution=application.RESOLUTION,
						frame_rate=application.FRAME_RATE)

	if application.USE_PI_CAMERA:
		print('[INFO] Warming up pi camera...')
	else:
		print('[INFO] Warming up camera...')

	time.sleep(2.0)

	print('[INFO] Start capturing...')
	# initialize the object center finder
	# obj = ObjCenter(args["cascade"])
	# loop indefinitely
	while True:
		# grab the frame from the threaded video stream and flip it
		# vertically (since our camera was upside down)
		frame = capture.read()
		frame = cv2.rotate(frame, cv2.ROTATE_180)

		# Down size frame to 50% (to increase performance on Raspberry Pi)
		frame = _frame.scale(frame=frame, scale=0.5)

		# Convert frame to gray (to increase performance on Raspberry Pi)
		gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

		# Dlib detection (set `up_sample=0` to increase performance on Raspberry Pi)
		dets = _dlib.frontal_face_detector(frame=gray, up_sample=0)

		# Up size frame to 50% (how the frame was before down sizing)
		frame = _frame.scale(frame=frame, scale=2)

		if len(dets) > 0:
			det = dets[0]
			print(det.left())
			objX.value = (det.left() * 2.0 + det.right() * 2.0) / 2.0
			objY.value = (det.top() * 2.0 + det.bottom() * 2.0) / 2.0
		else:
			objX.value = 320
			objY.value = 240

		# # extract the bounding box and draw it
		# if len(dets) > 0:
		# 	(x, y, w, h) = rect
		# 	cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0),
		# 		2)
		# # display the frame to the screen
		# cv2.imshow("Pan-Tilt Face Tracking", frame)
		# cv2.waitKey(1)

def pid_process(output, p, i, d, objCoord, centerCoord):
	# signal trap to handle keyboard interrupt
	signal.signal(signal.SIGINT, signal_handler)
	# create a PID and initialize it
	p = PID(p.value, i.value, d.value)
	p.initialize()
	# loop indefinitely
	while True:
		# calculate the error
		error = centerCoord.value - objCoord.value
		# update the value
		output.value = p.update(error)

def in_range(val, start, end):
	# determine the input value is in the supplied range
	return (val >= start and val <= end)
def set_servos(pan, tlt):
	# signal trap to handle keyboard interrupt
	signal.signal(signal.SIGINT, signal_handler)
	# loop indefinitely
	while True:
		# the pan and tilt angles are reversed
		panAngle = -1 * pan.value
		tiltAngle = -1 * tlt.value
		# if the pan angle is within the range, pan
		if in_range(panAngle, servoRange[0], servoRange[1]):
			pth.pan(panAngle)
		# if the tilt angle is within the range, tilt
		if in_range(tiltAngle, servoRange[0], servoRange[1]):
			pth.tilt(tiltAngle)

# check to see if this is the main body of execution
if __name__ == "__main__":
	# construct the argument parser and parse the arguments
	# ap = argparse.ArgumentParser()
	# ap.add_argument("-c", "--cascade", type=str, required=True,
	# 	help="path to input Haar cascade for face detection")
	# args = vars(ap.parse_args())

	# start a manager for managing process-safe variables
	with Manager() as manager:
		# enable the servos
		pth.servo_enable(1, True)
		pth.servo_enable(2, True)
		# set integer values for the object center (x, y)-coordinates
		centerX = manager.Value("i", 320)
		centerY = manager.Value("i", 240)
		# set integer values for the object's (x, y)-coordinates
		objX = manager.Value("i", 0)
		objY = manager.Value("i", 0)
		# pan and tilt values will be managed by independed PIDs
		pan = manager.Value("i", 0)
		tlt = manager.Value("i", 0)

		# set PID values for panning
		panP = manager.Value("f", 0.09)
		panI = manager.Value("f", 0.08)
		panD = manager.Value("f", 0.002)
		# set PID values for tilting
		tiltP = manager.Value("f", 0.05)
		tiltI = manager.Value("f", 0.0001)
		tiltD = manager.Value("f", 0.05)

		# we have 4 independent processes
		# 1. objectCenter  - finds/localizes the object
		# 2. panning       - PID control loop determines panning angle
		# 3. tilting       - PID control loop determines tilting angle
		# 4. setServos     - drives the servos to proper angles based
		#                    on PID feedback to keep object in center
		processObjectCenter = Process(target=obj_center,
			args=(objX, objY))
		processPanning = Process(target=pid_process,
			args=(pan, panP, panI, panD, objX, centerX))
		processTilting = Process(target=pid_process,
			args=(tlt, tiltP, tiltI, tiltD, objY, centerY))
		processSetServos = Process(target=set_servos, args=(pan, tlt))
		# start all 4 processes
		processObjectCenter.start()
		# processPanning.start()
		processTilting.start()
		processSetServos.start()
		# join all 4 processes
		processObjectCenter.join()
		# processPanning.join()
		processTilting.join()
		processSetServos.join()
		# disable the servos
		pth.servo_enable(1, False)
		pth.servo_enable(2, False)