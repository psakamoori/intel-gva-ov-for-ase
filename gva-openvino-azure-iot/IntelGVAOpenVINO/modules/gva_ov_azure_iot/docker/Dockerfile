FROM xanadu-gst-build as build

ARG GST_VER=1.16.0

ARG GST_RTSP_SERVER_REPO=https://gstreamer.freedesktop.org/src/gst-rtsp-server/gst-rtsp-server-${GST_VER}.tar.xz

RUN  wget -O - ${GST_RTSP_SERVER_REPO} | tar xJ && \
     cd gst-rtsp-server-${GST_VER} && \
     ./autogen.sh \
        --prefix=/usr \
        --libdir=/usr/lib/x86_64-linux-gnu \
        --libexecdir=/usr/lib/x86_64-linux-gnu \
        --enable-introspection \
        --enable-shared \
        --disable-examples  \
        --disable-gtk-doc && \
     make -j $(nproc) && \
     make install DESTDIR=/home/build-gst-rtsp && \
     make install

FROM xanadu-gst-base 

COPY --from=build /home/build-gst-rtsp /

RUN pip3 install paho-mqtt