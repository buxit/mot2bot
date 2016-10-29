import Image
import sys
import pygame
import config

MODE_SPI = 1
MODE_FB = 0

width = 0
height = 0

BLACK      = (  0,   0,   0)
WHITE      = (255, 255, 255)
RED        = (255,   0,   0)
GREEN      = (  0, 255,   0)
BLUE       = (  0,   0, 255)
DARK_GREEN = (  0, 204,   0)
ORANGE     = (255, 153,  51)


def init():
    global surf, disp, mode, image, width, height
    global BLACK, WHITE, RED, GREEN, BLUE, DARK_GREEN, ORANGE

    mode = (MODE_SPI if config.model == config.MODEL_PI2KF else MODE_FB)

    if(mode == MODE_SPI):
        import Adafruit_GPIO.SPI as SPI
        import Adafruit_SSD1306
        RST = 23
        DC = 22
        SPI_PORT = 0
        SPI_DEVICE = 0
        disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST, dc=DC, spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE, max_speed_hz=8000000))
        disp.begin()
        disp.clear()
        disp.display()
        BLACK = 0
        WHITE = RED = GREEN = BLUE = DARK_GREEN = ORANGE = 255
        image = Image.new('1', (disp.width, disp.height))
        width = disp.width
        height = disp.width
    else:
        surf = pygame.display.set_mode((128, 128), 0, 16)
        width = 128
        height = 96
        image = Image.new('RGB', (width, height))

    return image


def update(image):
    global surf, disp, mode

    if(mode == MODE_SPI):
        disp.image(image)
        disp.display()
    else:
        print "update image"
        idata = image.tostring()
        pgimage = pygame.image.fromstring(idata, image.size, image.mode)
        surf.blit(pgimage, (0,32))
        pygame.display.update()
