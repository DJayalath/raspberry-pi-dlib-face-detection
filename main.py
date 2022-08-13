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
                



##
# StreamHandler class - inherit Handler
# This class provide handler for HTTP streaming
# Note: this class should override Handler.stream
##
class StreamHandler(Handler):

    ##
    # Override method Handler.stream()
    ##
    def stream(self):
        Handler.stream(self)
        print('[INFO] Overriding stream method...')

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
                h, w = frame.shape[:2]

                # Note that frame is quarter the size

                center_vert = (det.bottom() + det.top()) / 2.0
                center_horz = (det.right() + det.left()) / 2.0

                if center_vert < h / 4.0 - SLACK:
                    if pantilthat.get_tilt() - RES >= -90:
                        pantilthat.tilt(pantilthat.get_tilt() - RES)
                elif center_vert > h / 4.0 + SLACK:
                    if pantilthat.get_tilt() + RES <= 90:
                        pantilthat.tilt(pantilthat.get_tilt() + RES)

                if center_horz < w / 4.0 - SLACK:
                    if pantilthat.get_pan() + RES <= 90:
                        pantilthat.pan(pantilthat.get_pan() + RES)
                elif center_horz > w / 4.0 + SLACK:
                    if pantilthat.get_pan() - RES >= -90:
                        pantilthat.pan(pantilthat.get_pan() - RES)


            # If Dlib returns any detection
            for det in dets:

                # Up size coordinate to 50% (according to the frame size before down sizing)
                coordinates = {'left': det.left() * 2,
                               'top': det.top() * 2,
                               'right': det.right() * 2,
                               'bottom': det.bottom() * 2}

                # Draw box around detection with text on the frame
                frame = _draw.rectangle(frame=frame,
                                        coordinates=coordinates,
                                        text='Detected')

            # Write date time on the frame
            frame = _draw.text(frame=frame,
                               coordinates={'left': application.WIDTH - 150, 'top': application.HEIGHT - 20},
                               text=time.strftime('%d/%m/%Y %H:%M:%S', time.localtime()),
                               font_color=(0, 0, 255))

            # Convert frame into buffer for streaming
            retval, buffer = cv2.imencode('.jpg', frame)

            # Write buffer to HTML Handler
            self.wfile.write(b'--FRAME\r\n')
            self.send_header('Content-Type', 'image/jpeg')
            self.send_header('Content-Length', len(buffer))
            self.end_headers()
            self.wfile.write(buffer)
            self.wfile.write(b'\r\n')


##
# Method main()
##
def main():
    try:
        address = ('', application.HTTP_PORT)
        server = _server.Server(address, StreamHandler)
        print('[INFO] HTTP server started successfully at %s' % str(server.server_address))
        print('[INFO] Waiting for client to connect to port %s' % str(application.HTTP_PORT))
        server.serve_forever()
    except Exception as e:
        server.socket.close()
        print('[INFO] HTTP server closed successfully.')
        print('[ERROR] Exception: %s' % str(e))


if __name__ == '__main__':
    # main()
    quiet()
