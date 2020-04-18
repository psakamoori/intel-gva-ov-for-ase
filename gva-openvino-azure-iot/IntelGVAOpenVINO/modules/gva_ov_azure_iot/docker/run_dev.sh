parent_dir=$(dirname $(dirname "$(readlink -f "$0")"))
docker run --privileged --network host --rm -it -v$HOME/.Xauthority:/root/.Xauthority -eDISPLAY=$DISPLAY \
-eHTTP_PROXY=$HTTP_PROXY -eHTTPS_PROXY=$HTTPS_PROXY -ehttp_proxy=$http_proxy -ehttps_proxy=$https_proxy -eno_proxy=$no_proxy -eNO_PROXY=$NO_PROXY \
-v$parent_dir:/root/xanadu xanadu-image 