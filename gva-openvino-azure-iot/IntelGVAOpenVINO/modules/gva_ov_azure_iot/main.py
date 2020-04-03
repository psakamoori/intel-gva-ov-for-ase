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
NUM_OF_INP_STREAMS = 4

input="dlstreamer_test/head-pose-face-detection-female-and-male.mp4"
detection_model="dlstreamer_test/intel/face-detection-adas-binary-0001/FP32-INT1/face-detection-adas-binary-0001.xml"
classification_age_gender="dlstreamer_test/intel/age-gender-recognition-retail-0013/FP16/age-gender-recognition-retail-0013.xml"
detect_person="dlstreamer_test/intel/person-detection-retail-0013/FP16/person-detection-retail-0013.xml"
label_file_age_gender="dlstreamer_test/age-gender-recognition-retail-0013.json"
#lable_file_person="dlstreamer_test/intel/person-vehicle-bike-detection-crossroad-1016/person-vehicle-bike-detection-crossroad-0078.json"

def create_launch_string(pipe):
    return "filesrc location={} ! decodebin ! \
    gvadetect model={} device=CPU batch-size=1 nireq=5 ! queue !\
    gvaclassify model={} model_proc={} device=CPU batch-size=1 nireq=5 ! queue ! \
    gvadetect model={} device=CPU batch-size=1 nireq=5 ! queue ! \
    gvafpscounter ! fakesink sync=false name=sink{} ".format(input, detection_model, classification_age_gender, label_file_age_gender, detect_person, pipe)
#    gvametaconvert ! gvawatermark ! videoconvert ! fpsdisplaysink video-sink=fakesink sync=false name=sink{} async-handling=true ".

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
        print("error {}".format(message))
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
