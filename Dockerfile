FROM anaderi/rep-develop:latest

ENV TEMP /tmp
RUN mkdir $TEMP/build
COPY AUTHORS $TEMP/build/
COPY debian $TEMP/build/debian
COPY Dockerfile $TEMP/build/
COPY ipykee.js $TEMP/build/
COPY ipykee-ssh-wrapper.sh $TEMP/build/
COPY LICENSE $TEMP/build/
COPY py-modules $TEMP/build/py-modules
COPY README.md $TEMP/build/
COPY setup.py $TEMP/build/
RUN cd $TEMP/build/ && \
  pip install . && \
  rm -rf $TEMP/build

RUN cp $TEMP/build/ipykee.js /root/.ipython/nbextensions/
