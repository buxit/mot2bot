#!/usr/bin/python 
# coding=utf-8
from datetime import datetime
from subprocess import call, Popen, PIPE
from threading import Thread
from urlparse import urlparse,parse_qsl
import BaseHTTPServer
import Image
import ImageDraw
import ImageFont
import csv
import cv2
import face
import os
import qrcode
import signal, os
import socket, fcntl, struct
import sys
import time

import config
import pi2kf
import display

HOST_NAME = ''		# listen on this address
PORT_NUMBER = 8888	# listen on this port

# Define pins for Pan/Tilt
pan = 0
tilt = 1

pVal = pCenter = config.pCenter
tVal = tCenter = config.tCenter

bufsize = 1 	# line buffered
disp = 0

os.environ['PATH'] += ':/usr/local/bin'
if(os.path.dirname(__file__) != ''):
    os.chdir(os.path.dirname(__file__))

fuelgauge = pi2kf.FuelGauge(0x36)
bat_lastupdate = 0

p = Popen("espeak --stdout -v german-mbrola-5 -s 130 | aplay -q", shell=True, bufsize=bufsize, stdin=PIPE)

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
        )[20:24])

def cleanup():
    p.communicate()
    httpd.server_close()
    print "Server Stops - %s:%s" % (HOST_NAME, PORT_NUMBER)
    pi2kf.cleanup()
    #disp.clear()
    #disp.display()
    print "done"

def handler(signum, frame):
    print 'Signal handler called with signal', signum
    httpd.server_close()
    #cleanup()

# Set the signal handler and a 5-second alarm
signal.signal(signal.SIGTERM, handler)

def speak(words):
    print ("speak: " + words)
    p.stdin.write(words+"\n")

model = cv2.createEigenFaceRecognizer()
camera = config.get_camera()
label_to_num = {}
num_to_label = {}
maxlabel = 0
shutdown = '0'
beep=False

if __name__ == '__main__':
    maxlabel=0
    for key, val in csv.reader(open("labels.csv")):
        num_to_label[val] = key
        label_to_num[key] = val
        if val > maxlabel:
            maxlabel = val
    print label_to_num
    print num_to_label
    print 'Loading training data...'
    model.load(config.TRAINING_FILE)
    print 'loaded.'

class MyHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_HEAD(s):
        s.send_response(200)
        s.send_header("Content-type", "text/html")
        s.send_header("Access-Control-Allow-Origin", "*")
        s.send_header("Origin", "http://pi2kf.bux.at")
        s.end_headers()
    def do_GET (s):
        """Respond to a GET request."""
        global tVal, pVal, fuelgauge, image, bat_lastupdate

        ti = time.time();
        if ti > bat_lastupdate + 1.0:
            fuelgauge.update()
            draw.rectangle((65, 0, width-1, 24), outline=0, fill=0)
            draw.text((65,  0), 'BAT: {0:5.2f} %'.format(fuelgauge.percent),  font=font9, fill=display.DARK_RED)
            draw.text((65, 12), 'BAT: {0:5.2f} V'.format(fuelgauge.voltage),  font=font9, fill=display.DARK_RED)
            display.update(image)
            bat_lastupdate = time.time()

        s.send_response(200)
        origin = s.headers.get('Origin')
        if origin:
            s.send_header("Origin", origin)
        s.send_header("Content-type", "text/html")
        s.send_header("Access-Control-Allow-Origin", "*")
        s.end_headers()
        cmds = dict(parse_qsl(urlparse(s.path).query))
        #print cmds
        cmd = cmds['cmd']
        if(cmd=='status'):
            s.wfile.write('{'+'"bat_perc":{:5.2f}, "bat_volt":{:5.2f}'.format(fuelgauge.percent, fuelgauge.voltage)+'}')
        if(cmd=='drive'):
            left = float(cmds['l'])
            right = float(cmds['r'])
            pi2kf.go(left*100.0, right*100.0)
        if(cmd=='stop'):
            pi2kf.stop()
        if(cmd=='cam-center'):
            tVal = tCenter
            pVal = pCenter
            pi2kf.setServo(pan, pVal)
            pi2kf.setServo(tilt, tVal)
        if(cmd=='cam-turn'):
            tVal += float(cmds['t'])
            pVal += float(cmds['p'])
            pi2kf.setServo(pan, pVal)
            pi2kf.setServo(tilt, tVal)
            print pVal, tVal
        if(cmd=='cam-snapshot'):
            Popen(["/usr/bin/curl", 'localhost/cam/cmd_pipe.php?cmd=img'])
            call("aplay -q /home/pi/pi2kf/440Hz.wav &", shell=True)
        if(cmd=="sound-9"):
            call("mpg123 -q /home/pi/pi2kf/Robot_dying.mp3 &", shell=True)
        if(cmd=="speak"):
            speak(cmds['words'])
            #call("espeak --stdout -v german '"+cmds['words']+"' | aplay -q &", shell=True)
        if(cmd=="shutdown"):
            shutdown='1'
            call("espeak --stdout -v german 'Oh, oh! Ich werde abgeschalten!' | aplay -q", shell=True)
            call("mpg123 -q /home/pi/pi2kf/Robot_dying.mp3", shell=True)
            call("/sbin/poweroff &", shell=True)
        if(cmd=="toggle-beep"):
            if beep==True:
                call("killall mpg123", shell=True)
                beep=False
                global beep
            else:
                Popen("mpg123 --loop -1 --scale 15000 /home/pi/mot2bot/beep-beep.mp3", shell=True, bufsize=bufsize, stdin=PIPE)
                beep=True
                global beep
        if(cmd=="face-learn"):
            if not 'name' in cmds:
                speak('Ich brauche einen Namen zum lernen!');
            else:
                name = cmds['name'].title()
                ti = time.time();
                fimage = camera.read()
                print time.time()-ti, 'read()';
                ti = time.time();
                # Convert image to grayscale.
                fimage = cv2.cvtColor(fimage, cv2.COLOR_RGB2GRAY)
                print time.time()-ti, 'cvtColor()';
                ti = time.time();
                # Get coordinates of single face in captured image.
                result = face.detect_single(fimage)
                print time.time()-ti, 'detectSingle()';
                if result is not None:
                    x, y, w, h = result
                    ti = time.time();
                    # Crop and resize image to face.
                    crop = face.resize(face.crop(fimage, x, y, w, h))
                    print time.time()-ti, 'resize()';
                    ti = time.time();
                    fulldir = os.path.join(config.POSITIVE_DIR, name)
                    if not os.path.exists(fulldir):
                        os.makedirs(fulldir)
                    filename = os.path.join(fulldir, '{0:%Y-%m-%d_%H%M%S}.pgm'.format(datetime.now()))
                    cv2.imwrite(filename, crop)
                    speak('Gesicht von {0} gespeichert.'.format(name))
                else:
                    speak("Ich erkenne leider kein Gesicht.")
        if(cmd=="face-train"):
            face.train(model, num_to_label, label_to_num, speak)
            print label_to_num
            print num_to_label
        if(cmd=="musicOn"):
            call("mpg123 /home/pi/01-* &", shell=True)
        if(cmd=="musicOff"):
            call("killall mpg123", shell=True)
        if(cmd=="face"):
            print label_to_num
            print num_to_label
            ti = time.time();
            fimage = camera.read()
            print time.time()-ti, 'read()';
            ti = time.time();
            # Convert image to grayscale.
            fimage = cv2.cvtColor(fimage, cv2.COLOR_RGB2GRAY)
            print time.time()-ti, 'cvtColor()';
            ti = time.time();
            # Get coordinates of single face in captured image.
            result = face.detect_single(fimage)
            print time.time()-ti, 'detectSingle()';
            if result is not None:
                x, y, w, h = result
                ti = time.time();
                # Crop and resize image to face.
                crop = face.resize(face.crop(fimage, x, y, w, h))
                print time.time()-ti, 'resize()';
                ti = time.time();
                # Test face against model.
                label, confidence = model.predict(crop)
                print time.time()-ti, 'predict()';
                print '\nSehe Gesicht von {0} "{1}", Sicherheit={2} (niedriger ist besser).'.format(label,num_to_label[str(label)], confidence)
                if confidence < config.POSITIVE_THRESHOLD:
                    print 'Erkannt!'
                    speak("Hallo {0}! Ich habe dich erkannt!".format(num_to_label[str(label)]))
                else:
                    speak('Da ist ein Gesicht, aber ich weiss nicht wer es sein könnte.')
            else:
                speak("Ich erkenne leider kein Gesicht.")
        # HTTP send reply
        s.wfile.close()

if __name__ == '__main__':
    server_class = BaseHTTPServer.HTTPServer
    httpd = server_class((HOST_NAME, PORT_NUMBER), MyHandler)
    print "Server Starts - %s:%s" % (HOST_NAME, PORT_NUMBER)
    pi2kf.init()
    #call("aplay -q /home/pi/pi2kf/bla.wav", shell=True)
    speak("System gestartet!,")
    speak("Warten auf Netzwerk!")

    image = display.init()

    width = display.width
    height = display.width

    # Get drawing object to draw on image.
    draw = ImageDraw.Draw(image)

    # Draw a black filled box to clear the image.
    draw.rectangle((0,0,width,height), outline=0, fill=0)

    #padding = 0
    font22 = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 22)
    font9  = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 9)
    font25 = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 25)
    #Draw Mot2Bot
    draw.text((10,20), 'mot2bot', font=font25, fill=255)
    display.update(image)

    #draw.text((0, -5), 'Warten auf',  font=font22, fill=255)
    #draw.text((0, 25), 'Netzwerk ...', font=font22, fill=255)
    #draw.text((0,55), str(300), font=font9, fill=255)



    # Display image.
    #disp.image(image)
    #idata = image.tostring()
    #pgimage = pygame.image.fromstring(idata, image.size, image.mode)
    #surf.blit(pgimage, (0,32))
    display.update(image)
    #disp.display()

    #Center Camera:
    tVal = tCenter
    pVal = pCenter
    pi2kf.setServo(pan, pVal)
    pi2kf.setServo(tilt, tVal)
    def secure(y):
        while shutdown == '0':
            x = os.system("ping -c 1 " + y)
            if x != 0:
                pi2kf.stop()
            time.sleep(1) 

    ip_addr = ''
    req=0
    while ip_addr == '':
        req=req + 1
        if req > 300:
            draw.text((0, -5), 'Verbindung',  font=font22, fill=255)
            draw.text((0, 25), 'Fehlgeschlagen',  font=font22, fill=255)
            speak("Verbindung mit Netzwerk Fehlgeschlagen! System wird herruntergefahren...")
            call("bin/poweroff &", shell=True)
            display.update(image)

            time.sleep(15);
        else:
            #draw.text((0, 25), 'Netzwerk', font=font, fill=255)
            #draw.text((0, 50), 'Warten...', font=font, fill=255)
            rem = 300 - req
            draw.rectangle((0,55,width,height), outline=0, fill=0)
            draw.text((0,55), str(rem), font=font9, fill=255)
            display.update(image)
        try:
            ip_addr = get_ip_address('wlan0')
        except IOError:
            try:
                ip_addr = get_ip_address('eth0')
            except IOError:
                ip_addr = ('')
        time.sleep(1)
    t = Thread(target=secure, args=(ip_addr,))
    #t.start()
    draw.rectangle((0,0,width,height), outline=0, fill=0)
    qr = qrcode.QRCode(
            version=3,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=2,
            border=2,
    )
    #qr.add_data('http://pi2kf/')
    qr.add_data('http://'+ip_addr+'/')
    qr.make(fit=True)

    img = qr.make_image()

    fuelgauge.update()
    if config.model == config.MODEL_TAVBOT:
        # Draw a smiley
        top = 0
        shape_width = 36
        draw.ellipse((90, top , 90+shape_width, 0+shape_width), outline=255, fill=0)
        draw.ellipse((100, top+12 , 100+6, 12+6), outline=255, fill=0)
        draw.ellipse((110, top+12 , 110+6, 12+6), outline=255, fill=0)
        draw.arc((100, 12, 116, 12+16), start=30, end=150, fill=255)
        draw.text((65, 44), config.MOT2BOT_NAME+' bereit.',  font=font9, fill=display.DARK_RED)
        draw.text((65, 53), 'BAT: {0:3.2}% ({1:1.2} V)'.format(fuelgauge.percent, fuelgauge.voltage),  font=font9, fill=display.DARK_RED)
        draw.text((10, 75), ip_addr, font=font9, fill=display.ORANGE)
    else:
        draw.rectangle((65, 0, width-1, 24), outline=0, fill=0)
        draw.text((65,  0), 'BAT: {0:5.2f} %'.format(fuelgauge.percent),  font=font9, fill=display.DARK_RED)
        draw.text((65, 12), 'BAT: {0:5.2f} V'.format(fuelgauge.voltage),  font=font9, fill=display.DARK_RED)

    image.paste(img, (-1, -1));
    call("aplay -q /home/pi/pi2kf/bla.wav", shell=True)
    speak(config.MOT2BOT_NAME+" bereit.")
    speak("Meine EiPi-Adresse lautet: " + (ip_addr.replace("", " ")).replace(".", "punkt"))
    image2 = image.point(lambda p: p * 0.5)
    display.update(image2)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        speak("Software manuell gestoppt!")
        pass
    except Exception:
        pass
    cleanup()
