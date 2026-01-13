import bpy
import os
from ..main.common import *


class ParticlesHologram:
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

        # Make nodes

        texture_coords = CurMat.nodes.new("ShaderNodeTexCoord")
        vec_mul = CurMat.nodes.new("ShaderNodeVectorMath")
        vec_mul.operation = "MULTIPLY"

        aspect = CurMat.nodes.new("ShaderNodeValue")
        combine_xyz = CurMat.nodes.new("ShaderNodeCombineXYZ")

        vec_map = CurMat.nodes.new("ShaderNodeMapping")

        dots = CreateShaderNodeTexImage(
            CurMat,
            os.path.join(self.BasePath, Data["Dots"]),
            -800,
            -250,
            "DotsTexture",
            self.image_format,
        )
        alpha_mask = CreateShaderNodeTexImage(
            CurMat,
            os.path.join(self.BasePath, Data["AlphaMask"]),
            -800,
            -250,
            "AlphaMask",
        )

        dots_mul = CurMat.nodes.new("ShaderNodeMath")
        dots_mul.operation = "MULTIPLY"
        masks_mul = CurMat.nodes.new("ShaderNodeMath")
        masks_mul.operation = "MULTIPLY"

        holo_colour = CreateShaderNodeRGB(
            CurMat, Data["ColorParam"], -800, -250, "ColorParam"
        )
        emission_mul = CurMat.nodes.new("ShaderNodeMixRGB")
        emission_mul.blend_type = "MULTIPLY"

        # Populate nodes

        aspect.outputs[0].default_value = 1.32802  # Kinda arbitrary, what I measured

        combine_xyz.inputs[0].default_value = 1
        combine_xyz.inputs[1].default_value = 1
        combine_xyz.inputs[2].default_value = 1

        vec_mul.inputs[1].default_value = (13.0, 13.0, 13.0)
        dots_mul.inputs[1].default_value = 30.0
        dots_mul.use_clamp = True

        emission_mul.inputs[0].default_value = 1.0

        pBSDF.inputs["Base Color"].default_value = (0.0, 0.0, 0.0, 1.0)
        pBSDF.inputs["Emission Strength"].default_value = 5.0

        # Position nodes

        texture_coords.location = (-1560.0, -101.2)
        aspect.location = (-1560.0, -393.5)
        vec_mul.location = (-1370.0, -24.2)
        combine_xyz.location = (-1370.0, -369.5)
        dots.location = (-1180.0, -47.9)
        vec_map.location = (-1130.0, -185.5)
        dots_mul.location = (-840.0, 52.0)
        alpha_mask.location = (-890.0, -209.2)
        masks_mul.location = (-587.5, -35.4)
        holo_colour.location = (-587.5, -239.7)
        emission_mul.location = (-385.0, -126.7)

        # Link nodes

        CurMat.links.new(texture_coords.outputs[2], vec_mul.inputs[0])
        CurMat.links.new(texture_coords.outputs[2], vec_map.inputs[0])

        CurMat.links.new(aspect.outputs[0], combine_xyz.inputs[0])
        CurMat.links.new(combine_xyz.outputs[0], vec_map.inputs[3])

        CurMat.links.new(vec_mul.outputs[0], dots.inputs[0])
        CurMat.links.new(dots.outputs[0], dots_mul.inputs[0])

        CurMat.links.new(vec_map.outputs[0], alpha_mask.inputs[0])

        CurMat.links.new(alpha_mask.outputs[0], masks_mul.inputs[0])
        CurMat.links.new(dots_mul.outputs[0], masks_mul.inputs[1])

        CurMat.links.new(holo_colour.outputs[0], emission_mul.inputs[1])
        CurMat.links.new(masks_mul.outputs[0], emission_mul.inputs[2])

        CurMat.links.new(emission_mul.outputs[0], pBSDF.inputs[sockets["Emission"]])
        CurMat.links.new(masks_mul.outputs[0], pBSDF.inputs["Alpha"])
