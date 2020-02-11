FROM python:3.6-slim 

## Necessary dependencies to run OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsm6 libxext6 libxrender-dev libglib2.0-0 python3-tk

## Copy the application 
WORKDIR /opt/is
COPY src/ src
COPY setup.py ./
COPY etc/conf/options.json ./

## Collect the dependecies
RUN pip install .

CMD ["is-skeletons-3d"]