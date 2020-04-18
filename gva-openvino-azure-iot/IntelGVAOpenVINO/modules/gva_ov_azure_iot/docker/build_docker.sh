parent_dir=$(dirname $(dirname "$(readlink -f "$0")"))

docker build https://github.com/opencv/gst-video-analytics.git#preview/python_api-yolov3_support --target gst-build -f docker/Dockerfile \
 -t xanadu-gst-build

docker build https://github.com/opencv/gst-video-analytics.git#preview/python_api-yolov3_support -f docker/Dockerfile \
 -t xanadu-gst-base

 docker build $parent_dir/docker --build-arg \
 -t xanadu-image
 
 
