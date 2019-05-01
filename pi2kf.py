#!/usr/bin/python
#
# Python Module to externalise all pi2kf specific hardware
#
# Created by Gareth Davies and Zachary Igielman, May 2014
# Updated June 2014 to include pi2kf-Lite within same framework
# Copyright 4tronix
#
# This code is in the public domain and may be freely copied and used
# No warranty is provided or implied
#
#======================================================================

from Adafruit_I2C import Adafruit_I2C
from Adafruit_MotorHAT import Adafruit_MotorHAT, Adafruit_DCMotor

import time
import atexit

mh = Adafruit_MotorHAT(addr=0x60)

# auto-disable motors on shutdown!
def turnOffMotors():
	mh.getMotor(1).run(Adafruit_MotorHAT.RELEASE)
	mh.getMotor(2).run(Adafruit_MotorHAT.RELEASE)
	mh.getMotor(3).run(Adafruit_MotorHAT.RELEASE)
	mh.getMotor(4).run(Adafruit_MotorHAT.RELEASE)

atexit.register(turnOffMotors)

mL = mh.getMotor(1)
mR = mh.getMotor(2)

#======================================================================
# General Functions
# (Both versions)
#
# init(). Initialises GPIO pins, switches motors and LEDs Off, etc
# cleanup(). Sets all motors and LEDs off and sets GPIO to standard values
# version(). Returns 1 for Full pi2kf, and 2 for pi2kf-Lite. Invalid until after init() has been called
#======================================================================

#======================================================================
# Motor Functions
# (Both Versions)
#
# stop(): Stops both motors
# go(leftSpeed, rightSpeed): controls motors in both directions independently using different positive/negative speeds. -100<= leftSpeed,rightSpeed <= 100
#======================================================================

#======================================================================
# UltraSonic Functions
# (Both Versions)
#
# getDistance(). Returns the distance in cm to the nearest reflecting object. 0 == no object
#======================================================================

#======================================================================
# Servo Functions
# 
# setServo(Servo, degrees). Sets the servo to position in degrees -90 to +90
#======================================================================

#======================================================================
# Switch Functions
# 
# getSwitch(). Returns the value of the tact switch: True==pressed
#======================================================================


# Import all necessary libraries
#import RPi.GPIO as GPIO
import sys, threading, time, os
from Adafruit_PWM_Servo_Driver import PWM

# Define Type of pi2kf
PI2KF = 1
TAVBOT = 2

# Define Sonar Pin (same pin for both Ping and Echo
sonar = 8

# Define pins for switch (different on each version)
switch = 16
Lswitch = 23

def setLed(on, brightness=255):
    if on:
        mh.getMotor(3).setSpeed(brightness)
        mh.getMotor(3).run(Adafruit_MotorHAT.FORWARD)
    else:
        mh.getMotor(3).run(Adafruit_MotorHAT.RELEASE)
#======================================================================
# General Functions
#
# init(). Initialises GPIO pins, switches motors and LEDs Off, etc
def init():
    global p, q, a, b, pwm, pcfADC, PGType
    PGType = PI2KF
    # Initialise the PCA9685 PWM device using the default address
    try:
        pwm = PWM(0x60, debug = False)
        pwm.setPWMFreq(60)
    except:
        print "can't set PWM frequency!"

    mh.getMotor(1).run(Adafruit_MotorHAT.RELEASE)
    mh.getMotor(2).run(Adafruit_MotorHAT.RELEASE)
    mh.getMotor(3).run(Adafruit_MotorHAT.RELEASE)
    mh.getMotor(4).run(Adafruit_MotorHAT.RELEASE)

# cleanup(). Sets all motors and LEDs off and sets GPIO to standard values
def cleanup():
    stop()
    time.sleep(1)
    #GPIO.cleanup()

# version(). Returns 1 pi2kf, 2 for tavbot
def version():
    return PGType

# End of General Functions
#======================================================================


#======================================================================
# Motor Functions
# (both versions)
#
# stop(): Stops both motors
def stop():
    mL.run(Adafruit_MotorHAT.RELEASE)
    mR.run(Adafruit_MotorHAT.RELEASE)

# go(leftSpeed, rightSpeed): controls motors in both directions independently using different positive/negative speeds. -100<= leftSpeed,rightSpeed <= 100
def go(leftSpeed, rightSpeed):
    global pwm
    l = min(abs(leftSpeed), abs(rightSpeed))
    freq = 1940 * ((l/100.0) ** 3)  + 60
    pwm.setPWMFreq(freq)
    mL.setSpeed(int(abs(leftSpeed*2.53)))
    mR.setSpeed(int(abs(rightSpeed*2.53)))
    #print("FREQ: {:5.2f}".format(freq))
    #print(int(abs(leftSpeed*2.53)))
    #print(int(abs(rightSpeed*2.53)))
    mL.run(Adafruit_MotorHAT.FORWARD if leftSpeed > 0 else Adafruit_MotorHAT.BACKWARD)
    mR.run(Adafruit_MotorHAT.FORWARD if rightSpeed > 0 else Adafruit_MotorHAT.BACKWARD)
    if leftSpeed == 0:
        mL.run(Adafruit_MotorHAT.RELEASE)
    if rightSpeed == 0:
        mR.run(Adafruit_MotorHAT.RELEASE)

# End of Motor Functions
#======================================================================


#======================================================================
# UltraSonic Functions
#
# getDistance(). Returns the distance in cm to the nearest reflecting object. 0 == no object
# (Both versions)
#
def getDistance():
    GPIO.setup(sonar, GPIO.OUT)
    # Send 10us pulse to trigger
    GPIO.output(sonar, True)
    time.sleep(0.00001)
    GPIO.output(sonar, False)
    start = time.time()
    count=time.time()
    GPIO.setup(sonar,GPIO.IN)
    while GPIO.input(sonar)==0 and time.time()-count<0.1:
        start = time.time()
    count=time.time()
    stop=count
    while GPIO.input(sonar)==1 and time.time()-count<0.1:
        stop = time.time()
    # Calculate pulse length
    elapsed = stop-start
    # Distance pulse travelled in that time is time
    # multiplied by the speed of sound 34000(cm/s) divided by 2
    distance = elapsed * 17000
    return distance

# End of UltraSonic Functions    
#======================================================================

#======================================================================
# Switch Functions
# 
# getSwitch(). Returns the value of the tact switch: True==pressed
def getSwitch():
    if PGType == 1:
        val = GPIO.input(switch)
    else:
        val = GPIO.input(Lswitch)
    return (val == 0)
#
# End of switch functions
#======================================================================

#======================================================================
# Servo Functions
# needs servoblaster started by init:
# https://github.com/richardghirst/PiBits/tree/master/ServoBlaster/user
# servod --pcm --idle-timeout=400 --p1pins="11,12"

def setServo(pin, degrees):
    #pinString = "echo " + str(pin) + "=" + str(((degrees+90)*0.001)) + " > /dev/pi-blaster"
    pinString = str(pin) + "=" + str(50+ ((90 - degrees) * 200 / 180))
    #print (pinString)
    with open('/dev/servoblaster', 'w') as servoblaster:
        servoblaster.write(pinString + "\n")

class FuelGauge:
    def __init__(self, address):
        self.i2c = Adafruit_I2C(address)
        self.i2c.write16(0x06, 0x0040)
        self.percent = 0.0
        self.voltage = 0.0

    def update(self):
        fg_ad = self.i2c.readU16(0x2)
        fg_ad = fg_ad >> 4
        fg_ad = self.i2c.reverseByteOrder(fg_ad)
        if fg_ad:
            self.voltage = fg_ad*0.00125;

        fg_pc1 = self.i2c.readU8(0x4)
        fg_pc2 = self.i2c.readU8(0x5)
        self.percent = fg_pc1 + fg_pc2/256.0;

class BlinkThread(threading.Thread):
    def __init__(self):
        super(BlinkThread, self).__init__()
        self.b=127
        self.speed=0.5
        self.blink=True
    def run(self):
        while self.blink:
            setLed(True, self.b)
            time.sleep(self.speed)
            setLed(False)
            time.sleep(self.speed)
    def setBrightness(self,br):
        self.b = br
    def setBlinkSpeed(self,sp):
        self.speed = sp
    def quit(self):
        self.blink=False

