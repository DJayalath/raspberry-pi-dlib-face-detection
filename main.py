##
# Copyright 2018, Ammar Ali Khan
# Licensed under MIT.
# Since: v1.0.0
##

from asyncio.format_helpers import _format_callback_source
import time
import cv2
import pantilthat
from src.common.package.config import application
from src.common.package.http import server as _server
from src.common.package.http.handler import Handler
from src.common.package.camera.capture import Capture as _capture
from src.common.package.frame.action import Action as _frame
from src.common.package.frame.draw import Draw as _draw
from src.dlib.package.dlib.dlib import Dlib

# Constant
_dlib = Dlib()
SLACK = 20
RES = 5
CENTER_W = 160
CENTER_H = 120
FACTOR = 0.15

def quiet():

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

        while True:
            # Read a frame from capture
            frame = capture.read()

            # Rotate as pantilthat is upside down
            frame = cv2.rotate(frame, cv2.ROTATE_180)

            # Down size frame to 50% (to increase performance on Raspberry Pi)
            frame = _frame.scale(frame=frame, scale=0.5)

            # Convert frame to gray (to increase performance on Raspberry Pi)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Dlib detection (set `up_sample=0` to increase performance on Raspberry Pi)
            dets = _dlib.frontal_face_detector(frame=gray, up_sample=0)

            # Up size frame to 50% (how the frame was before down sizing)
            frame = _frame.scale(frame=frame, scale=2)

            # Target first detection with pantilt camera tracking
            if len(dets) > 0:

                det = dets[0]

                # Note that frame is quarter the size

                center_vert = (det.bottom() + det.top()) / 2.0
                center_horz = (det.right() + det.left()) / 2.0

                # Compute delta (range will be 0 - 120 or 0 - 160)
                delta_v = center_vert - CENTER_H
                delta_h = center_horz - CENTER_W

                # Iterative halving auto-correction
                
                if abs(delta_v) > SLACK:
                    current_tilt = pantilthat.get_tilt()
                    new_delta = delta_v * FACTOR
                    new_tilt = current_tilt + new_delta
                    while new_tilt > 90 or new_tilt < -90:
                        new_delta = new_delta / 2.0
                        new_tilt = current_tilt + new_delta
                    pantilthat.tilt(new_tilt)

                if abs(delta_h) > SLACK:
                    current_pan = pantilthat.get_pan()
                    new_delta = -delta_h * FACTOR
                    new_pan = current_pan + new_delta
                    while new_pan > 90 or new_pan < -90:
                        new_delta = new_delta / 2.0
                        new_pan = current_pan + new_delta
                    pantilthat.pan(new_pan)

if __name__ == '__main__':
    quiet()
