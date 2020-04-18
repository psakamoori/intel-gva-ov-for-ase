#!/usr/bin/env python
# -*- coding:utf-8 vi:ts=4:noexpandtab
# Simple RTSP server. Run as-is or with a command-line to replace the default pipeline

import sys
import gi
import argparse
import shlex
import socket
import json 
import time
import os
from threading import Thread
from concurrent.futures import ThreadPoolExecutor
import shutil
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject
import subprocess

from model_definitions import detection_models 
from model_definitions import find_model_proc
from model_definitions import classification_models

from rtsp_server import GstServer

loop = GObject.MainLoop()
GObject.threads_init()
Gst.init(None)

def get_options():
    """Process command line options"""
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--source", action="append", dest="sources",
                        default=[],
                        required=True,
                        help="Location of the content to play/analyze. \n Example: file:///root/xanadu/videos/classroom.mp4")

    parser.add_argument("--enable_rtsp",action="store_true",default=False,dest="enable_rtsp",
                        help="Restream via rtsp.")

    parser.add_argument("--print_detections", action="store_true", dest="print_detections",
                        default=False,
                        help="Enable console output for detections")

    parser.add_argument("--print_rtsp_debug", action="store_true", dest="print_rtsp_debug",
                        default=False,
                        help="Print debug information on frame push")

    parser.add_argument("--print_fps", action="store_true", dest="print_fps",
                        default=False,
                        help="print fps using gvafps counter")

    parser.add_argument("--use_rtspsrc", action="store_true", dest="use_rtspsrc",
                        default=False,
                        help="user rtspsrc instead of uridecoebin")

    parser.add_argument("--save_mp4", action="store_true", dest="save_mp4",
                        default=False,
                        help="save mp4")


    return parser.parse_args()


def spawn(command):
    print("Spawning:\n\t{}\n".format(command)) 
    args = shlex.split(command)
    while True:
        subprocess.call(args)
        print("\n\nRespawning:\n\t{}\n".format(command)) 
        

def create_inference_elements(detection,models):
    if (detection):
        element = "gvadetect"
    else:
        element = "gvaclassify"
    elements=[]

    model_procs=["model-proc={}".format(find_model_proc(x.path)) if find_model_proc(x.path) else "" for x in models]
    for model,model_proc in zip(models,model_procs):
        elements.append("{} model={} {} device={} batch-size={} nireq={} ! queue".format(element,
                                                                                         model.path,
                                                                                         model_proc,
                                                                                         model.device,
                                                                                         model.batch_size,
                                                                                         model.nireq)) 
    return elements       

def create_publish_args(options,source,index):
    return  {"source":source,
            "index":index,
            "output_frames":options.enable_rtsp,
            "print_detections":options.print_detections}

def analyze_streams(options):

    detection = ""
    classification = ""
    
    if (detection_models):
        detection = "!" + " ! ".join(create_inference_elements(True,detection_models))
    if (classification_models):    
        classification = "!" + " ! ".join(create_inference_elements(False,classification_models))
        
    watermark = "videoconvert ! gvawatermark"
    convert = "gvametaconvert method=detection" 
    publish = "gvapython module=/root/xanadu/analyzer/publisher class=Publisher"

    sink = "fakesink"

    if (options.save_mp4):
        try:
            os.makedirs("/root/xanadu/saved_clips",exist_ok=True)
        except:
            pass
        sink = "videoconvert ! x264enc ! splitmuxsink max-size-time=60500000000 location=/root/xanadu/saved_clips/stream_{i}_%d.mp4"
    
    if (options.print_fps):
        sink = "gvafpscounter ! {}".format(sink)

    pipelines=[]
    for i,source in enumerate(options.sources):
        publish_args = shlex.quote(json.dumps(create_publish_args(options,source,i)))

        if ((options.use_rtspsrc) and("rstp" in source)):
            s_src = "rtspsrc udp-buffer-size=212992 name=source location={} ! queue ! rtph264depay ! h264parse ! video/x-h264 ! queue ! avdec_h264 ! videoconvert name=\"videoconvert\" ! video/x-raw,format=BGRA ! queue leaky=upstream".format(source)
        else:
            s_src = "uridecodebin uri={} is-live=true ! videoconvert ! video/x-raw,format=BGRA ! queue".format(source)
        sink = sink.format(**locals())
        pipeline_str = "{s_src} {detection} {classification} ! {watermark} ! {convert} source={source} ! {publish} args={publish_args} ! {sink}".format(**locals())
        pipelines.append(pipeline_str)        
    command = "gst-launch-1.0 {} ".format(" ".join(pipelines))
    spawn(command)
    
def print_options(options):
    heading = "Options for {}".format(os.path.basename(__file__))
    banner = "="*len(heading) 
    print(banner)
    print(heading)
    print(banner)
    for arg in vars(options):
        print ("\t{} == {}".format(arg, getattr(options, arg)))
    print()

if __name__ == '__main__':
    options = get_options()
    print_options(options)
    # RTSP Server
    if (options.enable_rtsp):
        s = GstServer(options)

    # Analytics
    thread = Thread(target=analyze_streams, args=[options])
    thread.daemon = True
    thread.start()

    loop.run()
