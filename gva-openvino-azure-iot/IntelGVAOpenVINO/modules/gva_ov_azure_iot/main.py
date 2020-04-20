# ==============================================================================
# ==============================================================================
import sys
import json
import gi
#import iot_hub_manager

import shlex, socket, shutil
import os, time

from threading import Thread
from concurrent.futures import ThreadPoolExecutor
import subprocess

gi.require_version('GObject', '2.0')
gi.require_version('Gst', '1.0')
gi.require_version('GstApp', '1.0')
gi.require_version('GstVideo', '1.0')

from gi.repository import Gst, GObject, GstApp, GstVideo
from gstgva import VideoFrame, util
from rtsp.rtsp_server import GstServer
from rtsp.publisher import Publisher

# Adding iot support
# Choose HTTP, AMQP or MQTT as transport protocol.  Currently only MQTT is supported.
#IOT_HUB_PROTOCOL = IoTHubTransportProvider.MQTT
#iot_hub_manager = IotHubManager(IOT_HUB_PROTOCOL)

class OVDLStreamer():

    def __init__(self, stream_type, stream_source, no_of_streams,  \
                                            clas_model, det_model, label_file):
        self.type ="file"
        self.source=["dlstreamer_test/car-detection.mp4"]
        self.streams = 1
        self.det_model="dlstreamer_test/intel/vehicle-license-plate-detection-barrier-0106/FP32-INT8/vehicle-license-plate-detection-barrier-0106.xml"
        self.label_file="dlstreamer_test/intel/vehicle-license-plate-detection-barrier-0106/vehicle-license-plate-detection-barrier-0106.json"

        self.print_fps = True
        self.use_rtspsrc = False
        self.save_mp4 = False
        self.print_rtsp_debug = False
        self.enable_rtsp = True
        self.print_detections = True
        self.index = 1

    def create_launch_string(self, sink_no):

        #publish_args = shlex.quote(json.dumps(publish_args))

        #print("publish_args == ", publish_args)

        if(self.type == "file"):
           return "filesrc location={} ! decodebin ! videoconvert ! \
               gvadetect model={} model_proc={} device=CPU batch-size=1 ! queue ! \
               gvawatermark ! videoconvert ! gvametaconvert ! gvafpscounter ! gvapython name=Publisher{} ! \
               fakesink name=sink{} sync=false ".format(self.source[sink_no], self.det_model, self.label_file, sink_no+1, sink_no+1)

        if(self.type == "rtsp"):
            return "rtspsrc udp-buffer-size=212992 name=source location={} ! queue ! rtph264depay ! \
                    h264parse ! video/x-h264 ! queue ! avdec_h264 ! videoconvert name=\"videoconvert\" ! \
                    video/x-raw,format=BGRA ! queue leaky=upstream !  gvadetect model={} model_proc={} device=CPU batch-size=1 ! \
                    queue ! gvawatermark ! gvametaconvert method=detection ! gvapython name=Publisher{} ! \
                     fakesink name=sink{} ".format(self.source[sink_no], self.det_model, self.label_file, sink_no+1, sink_no+1)

    def gobject_mainloop(self):
       mainloop = GObject.MainLoop()
       try:
           mainloop.run()
       except KeyboardInterrupt:
           pass

    def bus_call(self, bus, message, pipeline):
        t = message.type
        if t == Gst.MessageType.EOS:
           print("pipeline ended")
           pipeline.set_state(Gst.State.NULL)
           sys.exit()
        elif t == Gst.MessageType.ERROR:
           err, debug = message.parse_error()
           print("element {} error {} dbg {}".format(message.src.name, err, debug))
        else:
           pass
        return True

    def frame_callback(self, frame: VideoFrame):
        for message in frame.messages():
            m = json.loads(message)
            #if iot_hub_manager is not None:
            #iot_hub_manager.send_message_to_upstream(json.dumps(message))
            print(m)

    def pad_probe_callback(self, pad, info):
        with util.GST_PAD_PROBE_INFO_BUFFER(info) as buffer:
            caps = pad.get_current_caps()
            frame = VideoFrame(buffer, caps=caps)
            self.frame_callback(frame)

        return Gst.PadProbeReturn.OK


    def set_callbacks(self, pipeline, pipe):
        sink = pipeline.get_by_name("sink"+str(pipe))
        pad = sink.get_static_pad("sink")
        pad.add_probe(Gst.PadProbeType.BUFFER, self.pad_probe_callback)

        bus = pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.bus_call, pipeline)

if __name__ == '__main__':

    dlstr = OVDLStreamer("file", None, 1, None, None, None)

    Gst.init(sys.argv)

    if (dlstr.enable_rtsp):
        s = GstServer(len(dlstr.source), dlstr.print_detections)

    gst_launch_string = ""
    idx = dlstr.streams

    while(idx):
        gst_launch_string += dlstr.create_launch_string(idx - 1)
        idx -= 1

    print(gst_launch_string)
    pipeline = Gst.parse_launch(gst_launch_string)

    for i in range(dlstr.streams):
        publisher = pipeline.get_by_name("Publisher{}".format(i+1))
        args = json.dumps({"source":dlstr.source[i], "index":i,
                "output_frames":dlstr.enable_rtsp,
                "print_detections":dlstr.print_detections})

        publisher.set_property("module","./rtsp/publisher")
        publisher.set_property("class","Publisher")
        publisher.set_property("args",args)

    pipe = dlstr.streams

    while(pipe):
       dlstr.set_callbacks(pipeline, pipe)
       pipe -= 1

    pipeline.set_state(Gst.State.PLAYING)

    dlstr.gobject_mainloop()

    print("Exiting")
