#!/usr/bin/python
# coding=utf-8
from datetime import datetime
from subprocess import call, Popen, PIPE
import threading
from urlparse import urlparse,parse_qsl
import BaseHTTPServer
import Image
import ImageDraw
import ImageFont
import csv
import math
import os
import serial
import qrcode
import signal, os
import socket, fcntl, struct
import sys
import time
import monotonic
import traceback
#from gpiozero import Button
import sliplib
import roboctl
from optparse import OptionParser

import config
import pi2kf
import display

HOST_NAME = ''		# listen on this address
PORT_NUMBER = 8888	# listen on this port
quit = False
global secureThread
# Define pins for Pan/Tilt
pan = 0
tilt = 1
lastRcv = monotonic.monotonic()
pVal = pCenter = config.pCenter
tVal = tCenter = config.tCenter

bufsize = 1 	# line buffered
disp = 0

os.environ['PATH'] += ':/usr/local/bin'
if(os.path.dirname(__file__) != ''):
    os.chdir(os.path.dirname(__file__))

fuelgauge = pi2kf.FuelGauge(0x36)

blinkthread = pi2kf.BlinkThread()
blinkthread.daemon = True

serial_driver = sliplib.Driver()

p = Popen("espeak --stdout -v german-mbrola-5 -s 130 | aplay -q", shell=True, bufsize=bufsize, stdin=PIPE)
def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
        )[20:24])

def soundAnnounce():
    call("aplay -q /home/pi/pi2kf/bla.wav", shell=True)

def cleanup():
    global blinkthread
    p.communicate()
    httpd.server_close()
    print "Server Stops - %s:%s" % (HOST_NAME, PORT_NUMBER)
    if blinkthread.isAlive():
        blinkthread.quit()
        blinkthread.join()
    pi2kf.cleanup()
    #disp.clear()
    #disp.display()
    print "done"

def handler(signum, frame):
    global quit
    print('received signal {}, quit.'.format(signum))
    quit = True
    httpd.server_close()

# Set the signal handler and a 5-second alarm
signal.signal(signal.SIGTERM, handler)

def speak(words):
    print ("speak: " + words)
    p.stdin.write(words+"\n")

model = None
camera = config.get_camera()
label_to_num = {}
num_to_label = {}
maxlabel = 0
shutdown = '0'
beep=False
lastReceived=-1
lastPkg = "web"

def httpThreadFunc():
    global httpd, quit
    server_class = BaseHTTPServer.HTTPServer
    httpd = server_class((HOST_NAME, PORT_NUMBER), MyHandler)
    print "Server Starts - %s:%s" % (HOST_NAME, PORT_NUMBER)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("httpThreadFunc() KeyboardInterrupt")
    except Exception as e:
        if not quit:
            print(e.args)
            print("httpThreadFunc() Exception")
            traceback.print_exc()
    quitThread()

class MyHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_HEAD(s):
        s.send_response(200)
        s.send_header("Content-type", "text/html")
        s.send_header("Access-Control-Allow-Origin", "*")
        s.send_header("Origin", "http://pi2kf.bux.at")
        s.end_headers()
    def do_GET (s):
        #Save last time when package arrived
        """Respond to a GET request."""
        global tVal, pVal, fuelgauge, image, blinkthread, beep, lastRcv, lastPkg, quit
        lastPkg = "web"
        ti = time.time();
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
            if(cmd=='acknowledge'):
                if lastReceived == -1:
                    speak("Fernsteuerung verbunden!")
                lastReceived=currentTimeMillis()
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
                call("mpg123 -q snd/Robot_dying.mp3 &", shell=True)
            if(cmd=="speak"):
                speak(cmds['words'])
                #call("espeak --stdout -v german '"+cmds['words']+"' | aplay -q &", shell=True)
            if(cmd=="shutdown"):
                shutdown = '1'
                try:
                    quit = True
                    secureThread.stop()
                except:
                    pass
                speak("Herrunterfahren...")
                time.sleep(3)
                call("mpg123 -q /home/pi/pi2kf/Robot_dying.mp3", shell=True)
                call("/sbin/poweroff &", shell=True)
            if(cmd=="toggle-ledblink"):
                print("Processing LED Command...")
                if not blinkthread.isAlive():
                    print("Starting Thread...")
                    blinkthread.start()
                    blinkthread.setBrightness(255)
                    blinkthread.setBlinkSpeed(0.5)
                else:
                    print("Stopping Thread")
                    blinkthread.quit()
                    blinkthread.join()
                    blinkthread = pi2kf.BlinkThread()
            if(cmd=="toggle-beep"):
                if beep==True:
                    call("killall mpg123", shell=True)
                    beep=False
                else:
                    call("mpg123 --loop -1 --scale 3000 /home/pi/mot2bot/beep-beep.mp3 &", shell=True)
                    beep=True
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
            lastRcv = monotonic.monotonic()
            # HTTP send reply
            s.wfile.close()

def currentTimeMillis():
    #Returns the actual time in milliseconds
    return int(round(time.time() * 1000))

def startRemote():
    global tVal, pVal, lastRcv, lastPkg, beep, blinkthread, light_on
    connected = False
    while True:
        try:
            print("Starting remote support...")
            ser = serial.Serial('/dev/ttyUSB-jeelink', 115200, timeout=0.5)
            lastX = 0
            lastY = 0
            lastMode = 0
            lastRcv = monotonic.monotonic()
            inp = ''
            while inp != 'm2b ready.':
                inp = ser.readline().strip()
                print("wait for ready: '{}'".format(inp))

            snd_files = sorted(os.listdir('snd/'))
            print(snd_files)
            snd = 0
            connected = True
            for snd_file in snd_files:
                snd += 1
                snd_file = snd_file.replace('.mp3', '')
                message = b'm2bsnd\0'
                message += struct.pack('bb', snd, min(len(snd_file),15)+1)
                message += snd_file[:15] + '\0'
                ser.write(serial_driver.send(message))
                ser.flush()
                inp = ser.readline().rstrip()
                print(inp)

            while connected:
                try:
                    vals = []
                    s_line = ser.readline().strip()
                    message = b'status\0'
                    message += struct.pack('ff', fuelgauge.percent, fuelgauge.voltage)
                    #print(serial_driver.send(message))
                    ser.write(serial_driver.send(message))
                    if s_line != '':
                        print(s_line)
                    #outp = ser.write('{:5.2f} {:5.2f}\n'.format(fuelgauge.percent, fuelgauge.voltage)) #  battery
                    #print("Last: " + str(lastRcv) + ", from: " + lastPkg)
                    inp = s_line.split(" ")
                    if len(inp) >= 5:
                        lastRcv = monotonic.monotonic()
                    if lastRcv + 0.5 < monotonic.monotonic() and lastPkg == "remote":
                        pi2kf.go(0, 0)
                        print(str(lastRcv + 0.5) + "<" + str(monotonic.monotonic()))
                        continue
                    elif lastRcv + 1 < monotonic.monotonic() and lastPkg == "web":
                        pi2kf.go(0, 0)
                        continue
                    if len(inp) < 5:
                        continue
                    x = int(inp[0])
                    y = int(inp[1])
                    x /= 511.0
                    y /= 511.0
                    leng = math.sqrt(x*x + y*y)
                    w = math.atan2(x, -y)
                    deg = w * 180/math.pi
                    q = w / math.pi
                    l = 0
                    r = 0
                    #print("x={:5.2f}, y={:5.2f} leng={:5.2f}, deg={:5.2f}, q={:5.2f}".format(x, y, leng, deg, q))
                    if q > 0.0 and q <= 0.5:
                        l = 1
                        r = 1 - (q * 4)
                    elif q > 0.5 and q <= 1.0:
                        l=-1
                        r = 1 - ((q*4) - 2)
                    elif q >= -1.0 and q < -0.5:
                        r = -1
                        l = (q*4)+3
                    elif q >= -0.5 and q <= 0.0:
                        r = 1
                        l = (q * 4) + 1
                    r *= leng
                    l *= leng
                    if lastX != x or lastY != y:
                        if int(inp[4]) & 1:
                          pi2kf.go(r * 100, l* 100)
                          lastX = x
                          lastY = y
                    if lastMode != int(inp[4]):
                        pi2kf.go(0,0)
                    if int(inp[4]) & 2:
                       go2 = int(inp[1]) / 511.0 * 100 * -1
                       go1 = int(inp[3]) / 511.0 * 100 * -1
                       pi2kf.go(go1, go2)

                    #cam
                    if not int(inp[4]) & 2:
                        x1 = int(inp[2])
                        y1 = int(inp[3])
                        if (abs(x1) > 10 or abs(y1) > 10):
                            x1 /= -150.0
                            y1 /= -150.0
                            tVal += y1
                            pVal += x1
                            if pVal > 70:
                                pVal = 70
                            if pVal < -70:
                                pVal = -70
                            if tVal > 90:
                                tVal = 90
                            if tVal < -90:
                                tVal = -90
                            print("tVal={} pVal={}".format(tVal, pVal))
                            pi2kf.setServo(pan, pVal)
                            pi2kf.setServo(tilt, tVal)
                        #print("{} bla".format(inp[4]))
                    if int(inp[4]) & 0x08:
                        tVal = tCenter
                        pVal = pCenter
                        pi2kf.setServo(pan, pVal)
                        pi2kf.setServo(tilt, tVal)
                    if int(inp[4]) & 0x200 and lastMode & 0x200 == 0:
                        Popen(["/usr/bin/curl", 'localhost/cam/cmd_pipe.php?cmd=img'])
                        call("aplay -q /home/pi/pi2kf/440Hz.wav &", shell=True)
                    lastMode = int(inp[4])
                    lastRcv = monotonic.monotonic()
                    lastPkg = "remote"
                    if int(inp[4]) & 0x10:
                        if not beep:
                            beep = True
                            call("mpg123 --loop -1 --scale 3000 snd/beep-beep.mp3 &", shell=True)
                    if int(inp[4]) & 0x20:
                        if beep:
                            beep = False
                            call("killall mpg123", shell=True)

                    if int(inp[4]) & 0x40:
                        if not light_on:
                            pi2kf.setLed(True)
                        light_on = True
                    else:
                        if light_on:
                            pi2kf.setLed(False)
                        light_on = False
                        #if not blinkthread.isAlive():
                        #    print("Starting Thread...")
                        #    blinkthread.start()
                        #    blinkthread.setBrightness(255)
                        #    blinkthread.setBlinkSpeed(0.5)
                    if int(inp[4]) & 0x80:
                        if light_on:
                            pi2kf.setLed(False)
                        light_on = False
                        #if blinkthread.isAlive():
                        #    print("Stopping Thread")
                        #    blinkthread.quit()
                        #    blinkthread.join()
                        #    blinkthread = pi2kf.BlinkThread()
                    if int(inp[4]) & 0x100:
                        speak("Herrunterfahren...")
                        time.sleep(3)
                        call("mpg123 -q snd/Robot_dying.mp3", shell=True)
                        call("/sbin/poweroff &", shell=True)
                except Exception, e:
                    connected = False
                    pi2kf.go(0,0)
                    traceback.print_exc()
                    print("Overriding...")
                    print(str(e))
                    continue
        except:
            connected = False
            pi2kf.go(0,0)
            traceback.print_exc()
            speak("Fernschteuerung nicht Verbunden.")
            print("Remote Error!")
            time.sleep(5);

def quitThread():
    global quit
    quit = True
    #remoteThread.stop()

def shutdownButton():
    button_2 = Button(23, pull_up=True)
    button_2.wait_for_press()
    speak("Herrunterfahren...")
    time.sleep(3)
    quitThread()
    call("mpg123 -q snd/Robot_dying.mp3", shell=True)
    call("/sbin/poweroff &", shell=True)

if __name__ == '__main__':
    usage = "usage: %prog [options]"
    parser = OptionParser(usage)
    parser.add_option("-f", "--fast", action="store_true", dest="fast")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose")
    (options, args) = parser.parse_args()

    if not options.fast:
        import cv2
        import face
        maxlabel=0
        face.init()
        model = cv2.createEigenFaceRecognizer()
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

    pi2kf.init()
    #call("aplay -q /home/pi/pi2kf/bla.wav", shell=True)
    if not options.fast:
        speak("System gestartet!,")
        speak("Warten auf Netzwerk!")
    httpThread = threading.Thread(target=httpThreadFunc)
    httpThread.daemon = True
    httpThread.start()

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
    light_on = False

    ip_addr = ''
    req=0

    #buttonThread = threading.Thread(target=shutdownButton)
    #buttonThread.daemon = True
    #buttonThread.start()

    remoteThread = threading.Thread(target=startRemote)
    remoteThread.daemon = True
    remoteThread.start()

    while ip_addr == '':
        req=req + 1
        if req > 300:
            draw.text((0, -5), 'Verbindung',  font=font22, fill=255)
            draw.text((0, 25), 'Fehlgeschlagen',  font=font22, fill=255)
            speak("Verbindung mit Netzwerk Fehlgeschlagen! System wird herruntergefahren...")
            call("/sbin/poweroff &", shell=True)
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
        if ip_addr == '':
            time.sleep(1)

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
        draw.text((65, 40), config.MOT2BOT_NAME+' bereit.',  font=font9, fill=display.DARK_GREEN)
        draw.text((0, 78), ip_addr, font=font9, fill=display.ORANGE)
    else:
        draw.rectangle((65, 0, width-1, 24), outline=0, fill=0)
        draw.text((65,  0), 'BAT: {:5.2f} %'.format(fuelgauge.percent),  font=font9, fill=display.DARK_GREEN)
        draw.text((65, 12), 'BAT: {:5.2f} V'.format(fuelgauge.voltage),  font=font9, fill=display.DARK_GREEN)

    image2 = img.convert('RGB').point(lambda p: p * 0.3)
    image.paste(image2, (-1, -1))
    if not options.fast:
        call("aplay -q /home/pi/pi2kf/bla.wav", shell=True)
        speak(config.MOT2BOT_NAME+" bereit.")
        speak("Meine EiPi-Adresse lautet: " + (ip_addr.replace("", " ")).replace(".", "punkt"))
    display.update(image)

    last_bat = 0.0
    try:
        while not quit:
            if time.time() > last_bat + 1.0:
                fuelgauge.update()
                draw.rectangle((65, 50, width-1, 70), outline=None, fill=0)
                draw.text((65, 50), 'BAT: {:5.2f} %'.format(fuelgauge.percent),  font=font9, fill=display.DARK_GREEN)
                draw.text((65, 60), 'BAT: {:5.2f} V'.format(fuelgauge.voltage),  font=font9, fill=display.DARK_GREEN)
                display.update(image)
                last_bat = time.time()
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("main KeyboardInterrupt")
        quitThread()
    except Exception:
        print("main Exception")
        traceback.print_exc()
        quitThread()

    httpd.server_close()
    cleanup()
