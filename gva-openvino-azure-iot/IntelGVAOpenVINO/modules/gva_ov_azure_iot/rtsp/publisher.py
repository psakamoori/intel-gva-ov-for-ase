#import paho.mqtt.client as mqtt
import time
import json
from collections import deque as deque
import os, shutil, json

class Publisher:

    def create_frame_directory(self):
        try:
           shutil.rmtree("/tmp/stream_{}".format(self.index))
        except Exception as e:
            pass

        os.makedirs("/tmp/stream_{}".format(self.index))


    def __init__(self, source=None, 
                       index=None, 
                       output_frames=False, 
                       print_detections = True, 
                       max_output_frames=5000):
        self.source = "../" + source
        self.max_output_frames = max_output_frames
        self.initialized = False
        self.index = index
        self.frame_number = 0
        if (output_frames):
            self.create_frame_directory()
        self.print_detections = print_detections
        self.output_frames = output_frames

    def write_caps(self, frame):
        path = "/tmp/stream_{}.caps".format(self.index)
        try:
            os.remove(path)
        except Exception as e:
            pass

        with frame.data() as data:
            with open(path,"w") as file:
                value = {'caps':str(frame.caps),
                         'size':len(data.tobytes())}

                file.write(json.dumps(value))
                file.flush()

    def process_frame(self,frame):

        if (self.print_detections):
            header = "Source: {} Frame: {}".format(self.source,
                                                self.frame_number)
            seperator = '='*len(header)
            print()
            print(seperator)
            print(header)
            print(seperator)  
            for message in frame.messages():
              print(json.dumps(json.loads(message.get_message()),
                    indent=2,sort_keys=True),flush=True)
            print()

        if (self.output_frames):

            if (not self.initialized):
                self.write_caps(frame)
                self.initialized = True 

            with frame.data() as data:
                path = "/tmp/stream_{}/{}".format(self.index,self.frame_number%self.max_output_frames)
                with open(path,"wb",0) as output:
                    output.write(data.tobytes())
        
        self.frame_number+=1
           
        return True
   