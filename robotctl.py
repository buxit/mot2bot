import socket
import threading
import json
import math

def get_ip():
    return socket.gethostbyname(socket.gethostname())


class RobotCtlPacket:
    TYPE_JSON = 0
    TYPE_DATA = 1

    def __init__(self, packetType, json = None, data = None):
        self.type = packetType
        self.json = json
        self.data = data

class RobotControlHandling:
    def __init__(self, pi2kf, pkg_update_func):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((get_ip(), 1581))
        self.sock.listen(1)
        self.pi2kf = pi2kf
        self.pkg_sent = pkg_update_func
        self.thread = None
    
    def handler(self):
        pi2kf = self.pi2kf
        while True:
            print("start")
            conn, addr = self.sock.accept()
            print("COnnecte")
            lastLength = 0
            lastAngle = 0

            while True:
                try:
                    #Procedure to controll robot
                    data = bytearray(conn.recv(6))
                    angleCamera = int(data[0] << 8 | data[1])
                    distanceCamera = int(data[2])
                    angleMovement = int(data[3] << 8 | data[4])
                    distanceMovment = int(data[5])

                    angleNorm = angleMovement - 90
                    if angleNorm < 0:
                        angleNorm += 360

                    if angleNorm >= 360:
                        angleNorm -= 360

                    q = (angleNorm / 180.0 - 1)
                    l = 0
                    r = 0
                    length = 1.0 / 255.0 * distanceMovment
                    #print("leng={:5.2f}, deg={:5.2f}, q={:5.2f}, angle={:5.2f}, length={:5.2f}".format(length, 0, q, angleMovement, distanceMovment))
                    if q > 0.0 and q <= 0.5:
                        l = 1
                        r = 1 - (q * 4)
                    elif q > 0.5 and q <= 1.0:
                        l = -1
                        r = 1 - ((q * 4) - 2)
                    elif q >= -1.0 and q < -0.5:
                        r = -1
                        l = (q * 4) + 3
                    elif q >= -0.5 and q <= 0.0:
                        r = 1
                        l = (q * 4) + 1
                    l *= -1
                    r *= -1
                    r *= length
                    l *= length

                    self.pkg_sent()

                    if lastAngle != angleMovement or lastLength != distanceMovment:
                      pi2kf.go(r * 100, l* 100)
                      #print(str(r * 100) + " | " + str(l * 100) + " > " + str(angleMovement))
                      lastLength = distanceMovment
                      lastAngle = angleMovement
                        #TODO: Implement crawl mode

                except Exception as e:
                    print(e)
                    #stop robot in case of disconnect
                    pi2kf.go(0,0)
                    break
    
    def start(self):
        self.thread = threading.Thread(target=self.handler)
        self.thread.daemon = True
        self.thread.start()


class RobotCommunicationHandling(threading.Thread):
    def __init__(self, interfaces):
        threading.Thread.__init__(self)
        self.handler = RobotRequestHandler(self, interfaces)
        self.clients = []
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.daemon = True
    
    def run(self):
        self.sock.bind((get_ip(), 1582))
        self.sock.listen(15)
        while True:
            try: 
                conn, addr = self.sock.accept()
                client = RobotClientHandler(conn, addr, self)
                self.clients.append(client)
                client.start()
            except Exception as e:
                print("Err: " + str(e))

    def get_handler(self):
        return self.handler

class RobotRequestHandler:
    def __init__(self, handler, interfaces):
        self.handler = handler
        self.interfaces = interfaces
        self.handlers = {
            "gadget": self.handler_gadgets,
            "status": self.handler_status
        }
    
    
    def handlePacket(self, packet, client):
        client.sock.send(b'0x01' + "{\"type\": \"heiii\"}\n".decode("utf-8"))

    def handler_status(self, packet):
        pass
    
    def handler_gadgets(self, packet):
        pass

class RobotClientHandler(threading.Thread):
    def __init__(self, conn, addr, handler):
        threading.Thread.__init__(self)
        self.conn = conn
        self.addr = addr
        self.handler = handler
        self.daemon = True
    
    
    
    def send(self, packet):
        try:
            if packet.type == RobotCtlPacket.TYPE_JSON:
                self.conn.send(json.dumps(packet.json).decode("utf8"))
            elif packet.type == RobotCtlPacket.TYPE_DATA:
                self.conn.send(packet.data)
        except Exception as e:
            print("Failed to send packet: " + str(e))

    def run(self):
        buff = bytearray()
        while True:
            try:
                part = self.conn.recv(1)
                if not chr(part) == '\n':
                    buff.append(part)
                    continue
                packet = str(buff)
                header = packet[:1]
                data = packet[1:]
                if header == 1:
                    try:
                        print("Rec: " + str(data))
                        #handle JSON
                        jdata = json.loads(data)
                        pack = RobotCtlPacket(RobotCtlPacket.TYPE_JSON, json=jdata)
                        self.handler.get_handler().handlePacket(pack, self)
                    except Exception as e:
                        print("Packet handling failed: " + str(e))
                else:
                    #TODO: implementdata
                    pass
                buff = bytearray()
            except Exception as e:
                print(str(e))
                print(self.addr[0] + " has disconnected")
                buff = bytearray()
                #TODO: remove this client
                break

class RobotDiscovery:
    def __init__(self, name):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("", 1584))
        self.name = name
        self.thread = None
    
    def do_handling(self):
        while True:
                try:
                    print("run")
                    data, addr = self.sock.recvfrom(1024)
                    print("rec")
                    self.sock.sendto(self.name.decode("utf8"), (addr[0], 1583))
                except Exception as e:
                    print(str(e))
                    pass

    def start(self):
        self.thread = threading.Thread(target=self.do_handling)
        self.thread.daemon = True
        self.thread.start()

class RoboCtl:
    def __init__(self, pi2kf, pkg_update_func):
        self.discovery = RobotDiscovery("linux-pc")
        self.handler = RobotCommunicationHandling({})
        self.controller = RobotControlHandling(pi2kf, pkg_update_func)
    
    def start(self):
        self.discovery.start()
        self.handler.start()
        self.controller.start()

def void():
    pass
