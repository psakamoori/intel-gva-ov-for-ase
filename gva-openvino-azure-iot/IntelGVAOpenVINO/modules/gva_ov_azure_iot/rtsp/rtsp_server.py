#!/usr/bin/env python
# -*- coding:utf-8 vi:ts=4:noexpandtab
# Simple RTSP server. Run as-is or with a command-line to replace the default pipeline
import json
import gi
import os
import time
import socket
gi.require_version('GstRtspServer', '1.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GstRtspServer, GObject, GstRtsp, GLib

def timeout(server):
    pool = server.get_session_pool()
    pool.cleanup()
    return True

class Source:

    def get_framerate(self):
        split_caps = self.caps["caps"].split(',')
        for cap in split_caps:
            if 'framerate' in cap:
                prefix,value = cap.split("(fraction)")
                numerator,denominator = value.split('/')
                return float(numerator)/float(denominator)
        return None

    def __init__(self,index,caps,options,reserve=2):
        self.index = index
        self.number_frames = 0
        self.caps = caps
        self.framerate = self.get_framerate()
        self.duration = 1 / self.framerate * Gst.SECOND
        self.path = "/tmp/stream_{}".format(index)
        self.reserve = reserve
        self.options = options

    def enough_data(self,src):
        pass

    def on_need_data(self,src,length):
        files = []

        try:
            files=[os.path.join(self.path,x) for x in os.listdir(self.path)]
            files.sort(key=os.path.getmtime)
        except:
            pass

        frame = None
        if (files):
            with open(files[0],"rb") as input:
                frame = input.read()
                if (len(frame)<self.caps["size"]):
                    # wait for complete frame
                    time.sleep(self.duration / Gst.SECOND)
                    return
          
            buf = Gst.Buffer.new_allocate(None,len(frame),None)
            buf.fill(0,frame)
            buf.duration = self.duration
            timestamp = self.number_frames * self.duration
            buf.pts = buf.dts = int(timestamp)
            retval  = src.emit('push-buffer',buf)
            if (self.options.print_rtsp_debug):
                print('pushed buffer, frame {}, duration {} ns, durations {} s {}'.format(self.number_frames,
                                                                                      self.duration,
                                                                                      self.duration / Gst.SECOND,timestamp))

            if retval != Gst.FlowReturn.OK:
                if (self.options.print_rtsp_debug):
                    print(retval)
                return 
            
            self.number_frames += 1

            if (len(files)>self.reserve):
                os.remove(files[0])
            else:
                time.sleep(self.duration / Gst.SECOND)

        return True

class MyFactory(GstRtspServer.RTSPMediaFactory):
    def __init__(self,options=None):
        GstRtspServer.RTSPMediaFactory.__init__(self)
        self.options = options

    def read_caps(self, index):
        path = "/tmp/stream_{}.caps".format(index)
        caps = []
        with open(path,"r") as file:
            caps = [x for x in file]
        return json.loads(' '.join(caps))

    def do_configure(self, rtsp_media):
        element = rtsp_media.get_element()
        appsrc = rtsp_media.get_element().get_child_by_name('source_{}'.format(element.index))
        source = Source(element.index,element.caps,self.options)
        appsrc.connect('need-data', source.on_need_data)
        appsrc.connect('enough-data',source.enough_data)
 
    def select_caps(self, caps):
        split_caps = caps["caps"].split(',')
        new_caps = []
        selected_caps = ['video/x-raw','width','height','format']
        for cap in split_caps:
            for selected in selected_caps:
                if selected in cap:
                    new_caps.append(cap)
        return new_caps

    def do_create_element(self, url):
        index=int(url.abspath.split('_')[-1])
        caps = self.read_caps(index)
        new_caps = self.select_caps(caps)

        s_src = "appsrc name=source_{} is-live=true block=true format=GST_FORMAT_TIME caps=\"{}\"".format(index,','.join(new_caps))
        s_h264 = "videoconvert ! video/x-raw,format=I420 ! x264enc speed-preset=ultrafast tune=zerolatency"
        pipeline_str = "({s_src} ! queue ! {s_h264} ! rtph264pay config-interval=1 name=pay0 pt=96 )".format(**locals())        


        element = Gst.parse_launch(pipeline_str)
        element.index = index
        element.caps = caps
        return element


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


class GstServer():
    def __init__(self, no_of_streams, print_detections, stream_prefix = "stream"):
        self.server = GstRtspServer.RTSPServer()
        self.options = print_detections
        f = MyFactory(self.options)
        f.set_shared(False)
        m = self.server.get_mount_points()
        heading = "Streaming: "
        seperator = "="*len(heading)
        print(seperator)
        print("Streaming: ")
        print(seperator)
        ip = get_ip()
        for i in range(0, no_of_streams):
            stream_path = "/{}_{}".format(stream_prefix,i)
            m.add_factory(stream_path, f)
            url = "rtsp://{}:8554{}".format(ip,stream_path)
            print("\t{}".format(url))
        print()
        self.server.attach(None)
        GLib.timeout_add_seconds(2,timeout,self.server)
