# ==============================================================================
# ==============================================================================
import sys
import json
import gi
#import iot_hub_manager

gi.require_version('GObject', '2.0')
gi.require_version('Gst', '1.0')
gi.require_version('GstApp', '1.0')
gi.require_version('GstVideo', '1.0')

from gi.repository import Gst, GObject, GstApp, GstVideo
from gstgva import VideoFrame, util

# Adding iot support
# Choose HTTP, AMQP or MQTT as transport protocol.  Currently only MQTT is supported.
#IOT_HUB_PROTOCOL = IoTHubTransportProvider.MQTT
#iot_hub_manager = IotHubManager(IOT_HUB_PROTOCOL)

class OVDLStreamer():

    def __init__(self, stream_type, stream_source, no_of_streams,  \
                                            clas_model, det_model, label_file):
        self.inp_stream_type ="file"
        self.inp_stream_source="dlstreamer_test/ch-lp.mp4"
        self.num_of_inp_streams = 1
        self.veh_lp_det="dlstreamer_test/intel/vehicle-license-plate-detection-barrier-0106/FP32-INT8/vehicle-license-plate-detection-barrier-0106.xml"
        #self.veh_att_model="dlstreamer_test/intel/vehicle-attributes-recognition-barrier-0039/FP32-INT8/vehicle-attributes-recognition-barrier-0039.xml"

        #self.label_file="dlstreamer_test/intel/vehicle-license-plate-detection-barrier-0106/vehicle-license-plate-detection-barrier-0106.json"
        self.lp_recog="dlstreamer_test/intel/license-plate-recognition-barrier-0001/FP32-INT8/license-plate-recognition-barrier-0001.xml"
        self.label_file="dlstreamer_test/intel/license-plate-recognition-barrier-0001/license-plate-recognition-barrier-0001.json"
        self.render = False

    # File out options
    def create_launch_string(self, pipe):
        if(self.inp_stream_type == "file"):
            if(self.render):
               return "filesrc location={} ! decodebin ! \
                   gvadetect model={} device=CPU batch-size=1 nireq=5 ! queue ! \
                   gvaclassify model={} model_proc={} device=CPU batch-size=1 nireq=5 ! queue ! \
                   gvametaconvert ! gvametapublish ! videoconvert ! gvawatermark ! \
                   fpsdisplaysink video-sink=xvimagesink name=sink{} async-handling=true".format(self.inp_stream_source, self.veh_lp_det,
                                                                    self.lp_recog, self.label_file, pipe)
            else:
                return "filesrc location={} ! decodebin ! \
                   gvadetect model={} device=CPU batch-size=1 nireq=5 ! queue ! \
                   gvaclassify model={} model_proc={} device=CPU batch-size=1 nireq=5 ! queue ! \
                   gvametaconvert ! gvametapublish ! gvafpscounter ! \
                   fakesink name=sink{} sync=false ".format(self.inp_stream_source, self.veh_lp_det,
                                                                    self.lp_recog, self.label_file, pipe)

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

        if(self.render == False):
           pad = sink.get_static_pad("sink")
           pad.add_probe(Gst.PadProbeType.BUFFER, self.pad_probe_callback)

        bus = pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.bus_call, pipeline)

if __name__ == '__main__':

    dlstr = OVDLStreamer("file", None, 1, None, None, None)

    Gst.init(sys.argv)
    gst_launch_string = ""
    pipe = dlstr.num_of_inp_streams

    while(pipe):
        gst_launch_string += dlstr.create_launch_string(pipe)
        pipe -= 1

    print(gst_launch_string)
    pipeline = Gst.parse_launch(gst_launch_string)

    pipe = dlstr.num_of_inp_streams

    while(pipe):
       dlstr.set_callbacks(pipeline, pipe)
       pipe -= 1

    pipeline.set_state(Gst.State.PLAYING)

    dlstr.gobject_mainloop()

    print("Exiting")
