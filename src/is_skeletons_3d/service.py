import re
import time
import numpy as np
import dateutil.parser as dp
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from itertools import permutations
from mpl_toolkits.mplot3d import Axes3D
from .utils import load_options, to_image
from is_msgs.image_pb2 import ObjectAnnotations
from is_msgs.image_pb2 import HumanKeypoints as HKP
from opencensus.ext.zipkin.trace_exporter import ZipkinExporter
from is_wire.core import Subscription, Message, Channel, Logger, Tracer, AsyncTransport


def render_skeletons_3d(ax, skeletons, links, colors):
    """ Function to render the skeletons on the plot
    """
    for skeleton in skeletons.objects:
        parts = {}
        for part in skeleton.keypoints:
            parts[part.id] = (part.position.x, part.position.y, part.position.z)
        for link_parts, color in zip(links, colors):
            begin, end = link_parts
            if begin in parts and end in parts:
                x_pair = [parts[begin][0], parts[end][0]]
                y_pair = [parts[begin][1], parts[end][1]]
                z_pair = [parts[begin][2], parts[end][2]]
                ax.plot(
                    x_pair,
                    y_pair,
                    zs=z_pair,
                    linewidth=3,
                    color='#{:02X}{:02X}{:02X}'.format(*reversed(color)))


def span_duration_ms(span):
    """ Funtion to measure the time of a span in the Zipkin instrumentation
    """
    dt = dp.parse(span.end_time) - dp.parse(span.start_time)
    return dt.total_seconds() * 1000.0


def create_exporter(service_name, uri):
    """ Funtion to create the exporter in the Zipkin instrumentation
    """
    log = Logger(name="CreateExporter")
    zipkin_ok = re.match("http:\\/\\/([a-zA-Z0-9\\.]+)(:(\\d+))?", uri)
    if not zipkin_ok:
        log.critical("Invalid zipkin uri \"{}\", expected http://<hostname>:<port>", uri)
    exporter = ZipkinExporter(
        service_name=service_name,
        host_name=zipkin_ok.group(1),
        port=zipkin_ok.group(3),
        transport=AsyncTransport)
    return exporter


def main():

    #defining to colors and link to plot
    colors = list(permutations([0, 255, 85, 170], 3))
    links = [(HKP.Value('HEAD'), HKP.Value('NECK')), (HKP.Value('NECK'), HKP.Value('CHEST')),
             (HKP.Value('CHEST'), HKP.Value('RIGHT_HIP')),
             (HKP.Value('CHEST'), HKP.Value('LEFT_HIP')),
             (HKP.Value('NECK'), HKP.Value('LEFT_SHOULDER')),
             (HKP.Value('LEFT_SHOULDER'), HKP.Value('LEFT_ELBOW')),
             (HKP.Value('LEFT_ELBOW'), HKP.Value('LEFT_WRIST')),
             (HKP.Value('NECK'), HKP.Value('LEFT_HIP')),
             (HKP.Value('LEFT_HIP'), HKP.Value('LEFT_KNEE')),
             (HKP.Value('LEFT_KNEE'), HKP.Value('LEFT_ANKLE')),
             (HKP.Value('NECK'), HKP.Value('RIGHT_SHOULDER')),
             (HKP.Value('RIGHT_SHOULDER'), HKP.Value('RIGHT_ELBOW')),
             (HKP.Value('RIGHT_ELBOW'), HKP.Value('RIGHT_WRIST')),
             (HKP.Value('NECK'), HKP.Value('RIGHT_HIP')),
             (HKP.Value('RIGHT_HIP'), HKP.Value('RIGHT_KNEE')),
             (HKP.Value('RIGHT_KNEE'), HKP.Value('RIGHT_ANKLE')),
             (HKP.Value('NOSE'), HKP.Value('LEFT_EYE')),
             (HKP.Value('LEFT_EYE'), HKP.Value('LEFT_EAR')),
             (HKP.Value('NOSE'), HKP.Value('RIGHT_EYE')),
             (HKP.Value('RIGHT_EYE'), HKP.Value('RIGHT_EAR'))]

    # Defining our service
    service_name = 'Skeletons3D.Render'
    log = Logger(name=service_name)

    # initialized the matplotlib figure
    plt.ioff()
    fig = plt.figure(figsize=(5, 5))
    ax = Axes3D(fig)

    # Loading options
    op = load_options()

    # Conecting to the broker
    channel = Channel(op.broker_uri)
    log.info('Connected to broker {}', op.broker_uri)

    # creating the Zipking exporter
    exporter = create_exporter(service_name=service_name, uri=op.zipkin_uri)

    # Subcripting on desired topics

    subscription = Subscription(channel=channel, name=service_name)
    for group_id in list(op.group_ids):
        subscription.subscribe('SkeletonsGrouper.{}.Localization'.format(group_id))

    # begining the service
    while True:

        # waiting to receive a message from SkeletonsGrouper
        msg = channel.consume()

        # start a span to collect time metrics
        tracer = Tracer(exporter, span_context=msg.extract_tracing())
        span = tracer.start_span(name='render')

        annotations = msg.unpack(ObjectAnnotations)

        # plotting the image
        ax.clear()
        ax.view_init(azim=28, elev=32)
        ax.set_xlim(op.x_axis.start, op.x_axis.end)
        ax.set_xticks(np.arange(op.x_axis.start, op.x_axis.end + 0.5, 0.5))
        ax.set_ylim(op.y_axis.start, op.y_axis.end)
        ax.set_yticks(np.arange(op.y_axis.start, op.y_axis.end + 0.5, 0.5))
        ax.set_zlim(op.z_axis.start, op.z_axis.end)
        ax.set_zticks(np.arange(0, op.z_axis.end + 0.25, 0.5))
        ax.set_xlabel('X', labelpad=20)
        ax.set_ylabel('Y', labelpad=10)
        ax.set_zlabel('Z', labelpad=5)
        render_skeletons_3d(ax, annotations, links, colors)
        fig.canvas.draw()

        # generate a image from a matplotlib figure
        data = np.fromstring(fig.canvas.tostring_rgb(), dtype=np.uint8, sep='')
        view_3d = data.reshape(fig.canvas.get_width_height()[::-1] + (3,))

        # publish the image
        for group_id in list(op.group_ids):
            rendered_msg = Message()
            rendered_msg.topic = 'Skeletons3d.{}.Rendered'.format(group_id)
            rendered_msg.pack(to_image(view_3d))
            channel.publish(rendered_msg)

        # end the spans
        tracer.end_span()

        # logging usefull informations
        info = {
            'skeletons': len(annotations.objects),
            'took_ms': {
                'service': round(span_duration_ms(span), 2)
            }
        }
        log.info('{}', str(info).replace("'", '"'))


if __name__ == "__main__":
    main()