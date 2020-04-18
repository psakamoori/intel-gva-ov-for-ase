from collections import namedtuple
import os

Model = namedtuple("Model",'path device batch_size nireq')

detection_models=[
    Model("/root/xanadu/models/vehicle-license-plate-detection-barrier-0106/INT8/vehicle-license-plate-detection-barrier-0106.xml",
          "CPU",
           1,
           5)]


# detection_models=[
#     Model("/root/xanadu/models/face_detection_adas/1/FP32/face-detection-adas-0001.xml",
#           "CPU",
#            1,
#            5),
#     Model("/root/xanadu/models/person-detection-retail-0013/FP32/person-detection-retail-0013.xml",
#            "CPU",
#             1,
#             5)]

classification_models=[]

# classification_models=[Model("/root/xanadu/models/age-gender-recognition-retail-0013/FP32/age-gender-recognition-retail-0013.xml",
#                        "CPU",
#                        1,
#                        5)]


def find_model_proc(model_path):
    if not model_path:
        return None
    model_path = os.path.abspath(model_path)
    parent = os.path.dirname(os.path.dirname(model_path))
    basename = os.path.basename(model_path)
    (name,ext) = os.path.splitext(basename)
    for (root,dirs,filenames) in os.walk(parent):
        for filename in filenames:
            (candidate_name,candidate_ext)=os.path.splitext(filename)
            if (candidate_name == name) and (candidate_ext==".json"):
                return os.path.abspath(os.path.join(root,candidate_name+candidate_ext)) 
