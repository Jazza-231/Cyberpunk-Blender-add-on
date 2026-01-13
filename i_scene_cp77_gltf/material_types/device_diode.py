import bpy
import os
from ..main.common import *


class DeviceDiode:
    def __init__(self, BasePath, image_format, ProjPath):
        self.BasePath = BasePath
        self.ProjPath = ProjPath
        self.image_format = image_format

    def create(self, Data, Mat):
        print("jazza Data ", Data)
        print("jazza Mat ", Mat)

        CurMat = Mat.node_tree
        pBSDF = CurMat.nodes[loc("Principled BSDF")]
        sockets = bsdf_socket_names()
        pBSDF.inputs[sockets["Specular"]].default_value = 0

        emissiveNode = CreateShaderNodeRGB(CurMat, Data["EmissiveColor1"], -800, 250, "EmissiveColor1")

        CurMat.links.new(emissiveNode.outputs[0], pBSDF.inputs[sockets["Emission"]])

        if "EmissiveEV" in Data:
            pBSDF.inputs["Emission Strength"].default_value = Data["EmissiveEV"]
