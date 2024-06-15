#!/usr/bin/env python3
# 30 Mar 2024 working
# 10 May 2024 Added ip check, ROS status check
# 26 May 2024 added 'mapimgae" request
# 4 Jun 2024 added ROS ready check, get_ros_status
# 5 Jun 2024 combined GET request "info","health","battery" into 1, change mapdata to json 
# modfied for python3
# from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer #  python 2
# server1.py  change request header to /html, respond with a html page
#    problem shown as download, must open download to show webpage
#    change the header Content-type from 'application/html' to 'text/html' working
#   Open a web browser, type http://localhost:8009/index.html
#   try http://localhost:8009/service/?file=xyz.pdf
# 1 Apr 24: add request query str
import rospy
from http.server import BaseHTTPRequestHandler, HTTPServer #python3 use http.server
import socketserver      # python2 SocketServer  python3: socketserver
import json
import cgi
import struct
from time import sleep
import subprocess
from PIL import Image
import numpy as np

# from urlparse import urlparse

class Server(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
    def _set_headers_html(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
    def do_HEAD(self):
        self._set_headers()

    def bytes4ToFloat(self,byte_arry):
        val = struct.unpack("<f",byte_arry) # > MSB first than LSB, < LSB 1st then MSB
        return val[0]

    def bytes2longint(self,byte_arry):
        val = struct.unpack("<I",byte_arry) # > MSB first than LSB, < LSB 1st then MSB
        #return [ord(val[0]),ord(val[1]),ord(val[2]),ord(val[3])]
        return val[0]
        
    # GET sends back a Hello world message
    def do_GET(self):
        print(self.path, "type= ", type(self.path))
        # reqstr=self.path.split('?')
        reqstr=self.path
        robot_svr_dir='/home/wheeltec/robotmanager/' #****
        print(reqstr)
        if reqstr.rfind("info")>=0:     # Reques info
            self.send_response(200)
            self.send_header('Content-type','application/json')
            self.end_headers()
            robot_ip=readIP()
            robot_nm=get_hostname()
            ros_status=get_ros_status()
            status="ready"
            if robot_ip[0:4]=="Error" or robot_nm[0:4]=="Error":
                status="Error"
            # Open the voltage data file, saved by controller cpp
            with open(robot_svr_dir+'voltage.dat', 'rb') as file:
                float_arry=file.read()
            power_voltage=self.bytes4ToFloat(float_arry)
            # power_voltage='{:.2f}'.format(power_voltage)
            power_percent=power_voltage/12.5*100
            power_percentStg='{:.2f}'.format(power_percent)
            power_percent=float(power_percentStg)
            #
            info_dict = {
            "Robot name": robot_nm,
            "ip": robot_ip,
            "version": "18.04 Melodic",
            "mac":  "",
            "Network status": status,
            "ROS status": ros_status,
            "batteryPercentage": power_percent,
            "dockingStatus": "",
            "isCharging": False,    # future use
            "isDCConnected": "no",  # future use
            "powerStage": "",
            "sleepMode": "",            
            }
            jstr=json.dumps(info_dict) 
            self.wfile.write(bytes(jstr,"utf-8")) 


        if reqstr.rfind("map/data")>=0:    # request MAP data, only respond with para, not image
            ros_map=get_map_status()
            if ros_map=="Error":
                self.send_response(400)
                info_dict = {
                "Error": "no map topic,please launch mapping or navigation",   
                }
            else:    
                self.send_response(200)
                map_list=[]
                # Open the file
                with open(robot_svr_dir+'map_data', 'rb') as file: 
                    map_list=file.read() # Read the file 
                left_x=self.bytes4ToFloat(map_list[0:4])
                print("Left_x = ", left_x)
                lower_y=self.bytes4ToFloat(map_list[4:8])
                print("lower_y = ", lower_y)
                width=self.bytes2longint(map_list[8:12])
                print("width = ", width)
                height=self.bytes2longint(map_list[12:16])
                print("height = ", height)
                resolution=self.bytes4ToFloat(map_list[16:20])
                print("resolution = ", resolution)
                info_dict = {
                "left_x": left_x,
                "lower_y": lower_y,
                "width": width,
                "height": height,
                "resolution": resolution,     
                }
            self.send_header('Content-type','application/json')
            #self.send_header('Content-type','application/octet-stream')
            #self.send_header('Content-Disposition', 'attachment; filename="map_data"')
            self.end_headers()
            '''
            # old code, send binary map data file
            with open(robot_svr_dir+'map_data', 'rb') as file: 
            self.wfile.write(file.read()) # Read the file and send the contents 
            '''
            jstr=json.dumps(info_dict) 
            self.wfile.write(bytes(jstr,"utf-8")) 
            
        if reqstr.rfind("map/image")>=0:
            self.send_response(200)
            self.send_header('Content-type','application/octet-stream')
            self.send_header('Content-Disposition', 'attachment; filename="img_map.png"')
            self.end_headers()
            # Open the file
            img=Image.open(robot_svr_dir+'img_map.png')
            #with open(parent_dir+'img_map.png', 'rb') as file: 
                #self.wfile.write(file.read()) # Read the file and send the contents 
            np_pix=np.array(img)
            self.wfile.write(np_pix)   # works with np array

        if reqstr.rfind("battery")>=0:  # request Battery status
            self.send_response(200)
            self.send_header('Content-type','application/json')
            self.end_headers()
            # Open the file
            with open(robot_svr_dir+'voltage.dat', 'rb') as file:
                float_arry=file.read()
            power_voltage=self.bytes4ToFloat(float_arry)
            # power_voltage='{:.2f}'.format(power_voltage)
            power_percent=power_voltage/12.5*100
            power_percentStg='{:.2f}'.format(power_percent)
            power_percent=float(power_percentStg)
            battery_dict = {
            "batteryPercentage": power_percent,
            "dockingStatus": "",
            "isCharging": False,
            "isDCConnected": "no",
            "powerStage": "",
            "sleepMode": "",
            }
            jstr=json.dumps(battery_dict) 
            self.wfile.write(bytes(jstr,"utf-8"))
            
        if reqstr.rfind("pose")>=0:     # Reques robot pose, only respond with fix origin now.
            self.send_response(200)
            self.send_header('Content-type','application/json')
            self.end_headers()
            # Open the file
            with open(robot_svr_dir+'pose_data', 'rb') as file:
                float_arry=file.read()
            x=self.bytes4ToFloat(float_arry[0:4])
            y=self.bytes4ToFloat(float_arry[4:8])
            yaw=self.bytes4ToFloat(float_arry[8:12])
            pose_dict = {
            "x": x,
            "y": y,
            "yaw": yaw,
            }
            jstr=json.dumps(pose_dict) 
            self.wfile.write(bytes(jstr,"utf-8")) 

        if len(reqstr)>1:
            pos=reqstr[1].rfind("=")  # This request is not used
            print("position of =  ",pos)
        #query = urlparse(self.path).query
        #print(query)
        if self.path.endswith(".html"):
            #self.path has /index.htm   >
            self.send_response(200)
            self.send_header('Content-type','text/html')
            self.end_headers()
            # msg_page="<html>   <body>    <p>Trial page:</p><p> This is the body </p>   </body> </html>"  # 
            msg_page="<html>  <body>  <form action = 'http://localhost:8009/login' method = 'post'> \
<p>Enter Name:</p>  \
<p><input type = 'text' name = 'nm'></p> \
<p><input type = 'submit' value = 'submit' /></p>      \
</form>   </body> </html>" # working as download

            self.wfile.write(bytes(msg_page,"utf-8"))
            #
        if self.path.endswith(".json"):  # This request is not used
            self.send_response(200)
            self.send_header('Content-type','application/json')
            self.end_headers()
            # for Pyhton2:self.wfile.write(json.dumps({'hello': 'world', 'received': 'ok'}))
            # for Python3, must convert JSON string to bytes for wfile.write
            user_dict={"hello": "world", "received": "ok"}
            jstr=json.dumps(user_dict) 
            #self.wfile.write(bytes(jstr+chr(12)+chr(13),"utf-8")) # add CR & LF chr
            self.wfile.write(bytes(jstr+'\n',"utf-8")) # add CR & LF chr
                
    # POST echoes the message adding a JSON field
    def do_POST(self):
        # for python2:ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
        # for Python3:
        ctype, pdict = cgi.parse_header(self.headers.get('content-type'))  
        # refuse to receive non-json content
        if ctype != 'application/json':
            print("Not a json post: ",ctype)
            self.send_response(400)
            self.end_headers()
            return
            
        # read the message and convert it into a python dictionary
        length = int(self.headers.get('content-length'))
        message = json.loads(self.rfile.read(length))
        print(message)
        print("type message ", type(message))
        # add a property to the object, just to mess with data
        message['received'] = 'ok'
        if message["action"]=="login":
            print("login in received")
            msg_page="<body><p>This is a test.<p></body>"
            self.wfile.write(bytes(msg_page,"utf-8"))
        else:
            # send the message back
            self._set_headers()
            jstr=json.dumps(message)
            self.wfile.write(bytes(jstr,"utf-8")) # for python3, needs to convert to bytes

def readIP():
    output=subprocess.run("hostname -I".split(),stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    iplist=output.stdout.decode('UTF-8')
    err1=output.stderr.decode('UTF-8')
    if (err1!=""):
        print("Error: ",err1)
        addrstr="Error:"+err1
    else:
        listline=iplist.split()
        # print("Length of listline = ",len(listline))
        if len(listline)==0:
            addrstr=iplist
        else:
            addrstr=listline[0]
        print("Hostname IP= ", addrstr)
    return addrstr

def get_hostname():
    output=subprocess.run("hostname".split(),stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    nmlist=output.stdout.decode('UTF-8')
    err1=output.stderr.decode('UTF-8')
    if (err1!=""):
        print("Error: ",err1)
        robotname="Error:"+err1
    else:
        robotname=nmlist[:len(nmlist)-1]   # remove the char '\n'
        print("Hostname IP= ", robotname)
    return robotname

def get_ros_status():
    output=subprocess.run("rosnode list".split(),stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    nmlist=output.stdout.decode('UTF-8')
    err1=output.stderr.decode('UTF-8')
    if (err1!=""):
        print("Error: ",err1)
        ros="Error:"+err1
    else:
        ros="ready"   # ros is running
        print("rosnodes= ", nmlist)
    return ros

def get_map_status():
    output=subprocess.run("rostopic info /map".split(),stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    nmlist=output.stdout.decode('UTF-8')
    err1=output.stderr.decode('UTF-8')
    if (err1!=""):
        print("Error: ",err1)
        ros="Error"
    else:
        ros="ready"   # topic /map is available
        print("rostopic info= ", nmlist)
    return ros

def get_odom_status():
    output=subprocess.run("rostopic info /odom".split(),stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    nmlist=output.stdout.decode('UTF-8')
    err1=output.stderr.decode('UTF-8')
    if (err1!=""):
        print("Error: ",err1)
        ros="Error"
    else:
        ros="ready"   # topic /odom is available
        print("rostopic info= ", nmlist)
    return ros
        
def run(server_class=HTTPServer, handler_class=Server, port=1448):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    
    print('Starting httpd on port %d...' % port)
    httpd.serve_forever()
    
if __name__ == "__main__":
    from sys import argv
    
    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()
        
