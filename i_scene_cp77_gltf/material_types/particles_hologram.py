import bpy
import os
from ..main.common import *


class ParticlesHologram:
    def __init__(self, BasePath, image_format, ProjPath):
        self.BasePath = BasePath
        self.ProjPath = ProjPath
        self.image_format = image_format

    def create(self, Data, Mat):
        CurMat = Mat.node_tree

        # start with a clean node tree
        for node in CurMat.nodes:
            CurMat.nodes.remove(node)

        pBSDF = CurMat.nodes.new("ShaderNodeBsdfPrincipled")
        mat_out = CurMat.nodes.new("ShaderNodeOutputMaterial")
        sockets = bsdf_socket_names()

        # Make nodes

        texture_coords = CurMat.nodes.new("ShaderNodeTexCoord")
        vec_mul = CurMat.nodes.new("ShaderNodeVectorMath")
        vec_mul.operation = "MULTIPLY"
        scale_vec_mul = CurMat.nodes.new("ShaderNodeVectorMath")
        scale_vec_mul.operation = "MULTIPLY"

        aspect = CurMat.nodes.new("ShaderNodeValue")
        scale = CurMat.nodes.new("ShaderNodeValue")
        scale_aspect = CurMat.nodes.new("ShaderNodeMath")
        scale_aspect.operation = "MULTIPLY"
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
        scale.outputs[0].default_value = 9.0

        combine_xyz.inputs[0].default_value = 1
        combine_xyz.inputs[1].default_value = 1
        combine_xyz.inputs[2].default_value = 1

        vec_mul.inputs[1].default_value = (13.0, 1.5, 1.5)
        dots_mul.inputs[1].default_value = 5.0
        dots_mul.use_clamp = True

        emission_mul.inputs[0].default_value = 1.0

        pBSDF.inputs["Base Color"].default_value = (0.0, 0.0, 0.0, 1.0)
        pBSDF.inputs["Emission Strength"].default_value = 5.0

        # Position nodes

        texture_coords.location = (-1396.3, 61.9)
        aspect.location = (-1396.3, -304.2)
        scale.location = (-1396.3, -466.1)
        vec_mul.location = (-1206.3, -4.6)
        scale_aspect.location = (-1206.3, -233.3)
        combine_xyz.location = (-1003.8, -119.0)
        scale_vec_mul.location = (-1003.8, -284.6)
        vec_map.location = (-763.8, 65.1)
        dots.location = (-813.8, -308.8)
        alpha_mask.location = (-523.8, 41.0)
        dots_mul.location = (-473.8, -208.7)
        masks_mul.location = (-221.3, -55.3)
        holo_colour.location = (-221.3, 18.2)
        emission_mul.location = (-31.3, 131.6)
        pBSDF.location = (183.7, 222.2)
        mat_out.location = (473.7, 222.2)

        # Link nodes

        CurMat.links.new(texture_coords.outputs[2], vec_mul.inputs[0])
        CurMat.links.new(texture_coords.outputs[2], vec_map.inputs[0])

        CurMat.links.new(aspect.outputs[0], scale_aspect.inputs[0])
        CurMat.links.new(scale.outputs[0], scale_aspect.inputs[1])

        CurMat.links.new(vec_mul.outputs[0], scale_vec_mul.inputs[0])
        CurMat.links.new(scale.outputs[0], scale_vec_mul.inputs[1])

        CurMat.links.new(scale_aspect.outputs[0], combine_xyz.inputs[0])
        CurMat.links.new(combine_xyz.outputs[0], vec_map.inputs[3])

        CurMat.links.new(scale_vec_mul.outputs[0], dots.inputs[0])
        CurMat.links.new(dots.outputs[0], dots_mul.inputs[0])

        CurMat.links.new(vec_map.outputs[0], alpha_mask.inputs[0])

        CurMat.links.new(alpha_mask.outputs[0], masks_mul.inputs[0])
        CurMat.links.new(dots_mul.outputs[0], masks_mul.inputs[1])

        CurMat.links.new(holo_colour.outputs[0], emission_mul.inputs[1])
        CurMat.links.new(masks_mul.outputs[0], emission_mul.inputs[2])

        CurMat.links.new(emission_mul.outputs[0], pBSDF.inputs[sockets["Emission"]])
        CurMat.links.new(masks_mul.outputs[0], pBSDF.inputs["Alpha"])

        CurMat.links.new(pBSDF.outputs[0], mat_out.inputs[0])
