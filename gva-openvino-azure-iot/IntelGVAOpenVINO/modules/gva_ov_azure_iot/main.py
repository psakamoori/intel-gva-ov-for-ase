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
NUM_OF_INP_STREAMS = 1

input="dlstreamer_test/car-detection.mp4"
detection_model="dlstreamer_test/intel/vehicle-license-plate-detection-barrier-0106/FP32-INT8/vehicle-license-plate-detection-barrier-0106.xml"
label_file="dlstreamer_test/intel/vehicle-license-plate-detection-barrier-0106/vehicle-license-plate-detection-barrier-0106.json"

# File out options
def create_launch_string(pipe):
    return "filesrc location={} ! decodebin ! \
    gvadetect model={} model_proc={} device=CPU batch-size=1 nireq=5 ! queue ! \
    gvametaconvert ! gvametapublish ! gvafpscounter ! fakesink name=sink{} sync=false".format(input, detection_model, label_file, pipe)


def gobject_mainloop():
    mainloop = GObject.MainLoop()
    try:
        mainloop.run()
    except KeyboardInterrupt:
        pass

def bus_call(bus, message, pipeline):
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


def frame_callback(frame: VideoFrame):
    for message in frame.messages():
        m = json.loads(message)
        #if iot_hub_manager is not None:
        #    iot_hub_manager.send_message_to_upstream(json.dumps(message))
        print(m)


def pad_probe_callback(pad, info):
    with util.GST_PAD_PROBE_INFO_BUFFER(info) as buffer:
        caps = pad.get_current_caps()
        frame = VideoFrame(buffer, caps=caps)
        frame_callback(frame)

    return Gst.PadProbeReturn.OK


def set_callbacks(pipeline, pipe):
    sink = pipeline.get_by_name("sink"+str(pipe))
    pad = sink.get_static_pad("sink")
    pad.add_probe(Gst.PadProbeType.BUFFER, pad_probe_callback)

    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", bus_call, pipeline)

if __name__ == '__main__':
    Gst.init(sys.argv)
    gst_launch_string = ""
    pipe = NUM_OF_INP_STREAMS

    while(pipe):
        gst_launch_string += create_launch_string(pipe)
        pipe -= 1

    print(gst_launch_string)
    pipeline = Gst.parse_launch(gst_launch_string)

    pipe = NUM_OF_INP_STREAMS

    while(pipe):
       set_callbacks(pipeline, pipe)
       pipe -= 1

    pipeline.set_state(Gst.State.PLAYING)

    gobject_mainloop()

    print("Exiting")
