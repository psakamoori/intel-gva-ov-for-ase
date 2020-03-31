# ==============================================================================
# ==============================================================================
import sys
import json

import gi

gi.require_version('GObject', '2.0')
gi.require_version('Gst', '1.0')
gi.require_version('GstApp', '1.0')
gi.require_version('GstVideo', '1.0')

from gi.repository import Gst, GObject, GstApp, GstVideo
from gstgva import VideoFrame, util

input="dlstreamer_test/head-pose-face-detection-female-and-male.mp4"
detection_model="dlstreamer_test/intel/face-detection-adas-0001/FP32/face-detection-adas-0001.xml"
classification_age_gender="dlstreamer_test/intel/age-gender-recognition-retail-0013/FP32/age-gender-recognition-retail-0013.xml"
#classification_person="dlstreamer_test/intel/person-detection-retail-0013/FP32/person-detection-retail-0013.xml"
label_file="dlstreamer_test/age-gender-recognition-retail-0013.json"

def create_launch_string():
    return "filesrc location={} ! decodebin ! \
    gvadetect model={} device=CPU ! \
    gvaclassify model={} model_proc={} device=CPU ! \
    gvametaconvert ! gvafpscounter ! fakesink name=sink sync=false".format(input, detection_model, classification_age_gender, label_file)

#gvawatermark ! videoconvert ! fpsdisplaysink video-sink=xvimagesink (Render)
#fakesink name=sink sync=false (No Render)

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
        print(m)


def pad_probe_callback(pad, info):
    with util.GST_PAD_PROBE_INFO_BUFFER(info) as buffer:
        caps = pad.get_current_caps()
        frame = VideoFrame(buffer, caps=caps)
        frame_callback(frame)

    return Gst.PadProbeReturn.OK


def set_callbacks(pipeline):
    sink = pipeline.get_by_name("sink")
    pad = sink.get_static_pad("sink")
    pad.add_probe(Gst.PadProbeType.BUFFER, pad_probe_callback)

    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", bus_call, pipeline)

if __name__ == '__main__':
    Gst.init(sys.argv)
    gst_launch_string = create_launch_string()
    print(gst_launch_string)
    pipeline = Gst.parse_launch(gst_launch_string)

    set_callbacks(pipeline)

    pipeline.set_state(Gst.State.PLAYING)

    gobject_mainloop()

    print("Exiting")
