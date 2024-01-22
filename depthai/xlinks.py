import depthai.node
import typing

# TODO Neumožňovat plný přístup ke všem možnostem bind.Data*putQueue, ale nastavit nějak možnosti a věci jako blocking řešit na relevantním nodu

class XLinkHostIn(depthai.node.Node):
    sync = False
    def __node_init__(self, __context__, stream_name, src_device):
        self.queue = __context__["running_devices"][src_device]\
                        .getOutputQueue(stream_name)
    def __run__(self) -> typing.Any:
        rv = self.queue.tryGet()
        if rv is None: raise depthai.Abort()
        return rv

class XLinkHostOut(depthai.node.Node):
    def __node_init__(self, __context__, stream_name, dst_device):
        self.queue = __context__["running_devices"][dst_device]\
                        .getInputQueue(stream_name)
    def __run__(self, input: typing.Any):
        #FIXME I need trySend method on which I can abort to properly
        self.queue.send(input)

def create_xlinks(pipeline, context):
    stream_names = set()
    for dst in pipeline:
        for input_name, put_ref in dst.inputs.items():
            if put_ref == None: continue
            src = put_ref.node
            output_name = put_ref.name

            stream_name = str(put_ref)
            while stream_name in stream_names: stream_name += "I"
            stream_names.add(stream_name)

            # Cross-device link
            if dst.device is not None \
            and src.device is not None \
            and src.device != dst.device:
                # Change Dst(Src()) to Dst(Identity(device=None, Src()))
                #
                # Host node should be automatically added to the end of
                # pipeline and should be reprocessed later. Therefore,
                # only Dst -> Identity needs to be processed now. And
                # this already fits one of the later scenarios
                src = depthai.node.Identity(src, 
                                            pipeline=pipeline, 
                                            id="cross-link for " + stream_name,
                                            device=None)
                output_name ,= src.output_desc.keys()
                put_ref = depthai.Node.PutRef(src, output_name)
                dst.inputs[input_name] = put_ref

            # Device -> Host
            if dst.device is None \
            and src.device is not None:
                depthai.node.XLinkDevOut(put_ref,
                        stream_name=stream_name,
                        pipeline=pipeline,
                        id="for " + stream_name,
                        device=src.device)
                host_in = depthai.node.XLinkHostIn(
                            stream_name=stream_name,
                            src_device=src.device,
                            pipeline=pipeline,
                            id="for " + stream_name,
                            device=None)
                dst.link(input_name, host_in)

            # Host -> Device
            if src.device is None \
            and dst.device is not None:
                depthai.node.XLinkHostOut(put_ref,
                        stream_name=stream_name,
                        dst_device=dst.device,
                        pipeline=pipeline,
                        id="for " + stream_name,
                        device=None)
                dev_in = depthai.node.XLinkDevIn(
                            stream_name=stream_name,
                            pipeline=pipeline,
                            id="for " + stream_name,
                            device=dst.device)
                dst.link(input_name, dev_in)