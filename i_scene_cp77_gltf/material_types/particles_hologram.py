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

        uv_width = CurMat.nodes.new("ShaderNodeValue")
        texture_speed_x = CurMat.nodes.new("ShaderNodeValue")
        texture_speed_y = CurMat.nodes.new("ShaderNodeValue")
        texture_speed_z = CurMat.nodes.new("ShaderNodeValue")

        uv_x_div = CurMat.nodes.new("ShaderNodeMath")
        uv_x_div.operation = "DIVIDE"
        uv_height = CurMat.nodes.new("ShaderNodeValue")
        combine_texture_speeds = CurMat.nodes.new("ShaderNodeCombineXYZ")

        texture_coords = CurMat.nodes.new("ShaderNodeTexCoord")
        combine_uv = CurMat.nodes.new("ShaderNodeCombineXYZ")
        scale_texture_speeds = CurMat.nodes.new("ShaderNodeVectorMath")
        scale_texture_speeds.operation = "MULTIPLY"

        uv_mul = CurMat.nodes.new("ShaderNodeVectorMath")
        uv_mul.operation = "MULTIPLY"
        uv_speed_div = CurMat.nodes.new("ShaderNodeVectorMath")
        uv_speed_div.operation = "DIVIDE"
        dots_scale = CurMat.nodes.new("ShaderNodeValue")

        alpha_mask = CreateShaderNodeTexImage(
            CurMat,
            os.path.join(self.BasePath, Data["AlphaMask"]),
            0,
            0,
            "AlphaMask",
            self.image_format,
        )
        uv_speed_scale = CurMat.nodes.new("ShaderNodeVectorMath")
        uv_speed_scale.operation = "SCALE"

        dots_texture = CreateShaderNodeTexImage(
            CurMat,
            os.path.join(self.BasePath, Data["Dots"]),
            0,
            0,
            "DotsTexture",
            self.image_format,
        )

        sharpen_mask = CurMat.nodes.new("ShaderNodeMath")
        sharpen_mask.operation = "MULTIPLY"

        combine_masks = CurMat.nodes.new("ShaderNodeMath")
        combine_masks.operation = "MULTIPLY"
        hologram_colour = CreateShaderNodeRGB(
            CurMat, Data["ColorParam"], 0, 0, "ColorParam"
        )
        hologram_strength = CurMat.nodes.new("ShaderNodeValue")

        apply_mask = CurMat.nodes.new("ShaderNodeMixRGB")
        apply_mask.blend_type = "MULTIPLY"
        scale_strength = CurMat.nodes.new("ShaderNodeMath")
        scale_strength.operation = "DIVIDE"

        # Populate values

        uv_width.outputs[0].default_value = Data["AlphaSubUVWidth"]
        texture_speeds = Data["AlphaTexCoordSpeed"]
        texture_speed_x.outputs[0].default_value = texture_speeds["X"]
        texture_speed_y.outputs[0].default_value = texture_speeds["Y"]
        texture_speed_z.outputs[0].default_value = texture_speeds["Z"]

        uv_height.outputs[0].default_value = abs(Data["AlphaSubUVHeight"])

        combine_uv.inputs[2].default_value = 1.0
        scale_texture_speeds.inputs[1].default_value = (10.0, 1000.0, 10.0)

        dots_scale.outputs[0].default_value = Data["DotsCoords"]

        sharpen_mask.inputs[1].default_value = 5

        hologram_strength.outputs[0].default_value = Data["ColorMultiplier"]

        apply_mask.inputs[0].default_value = 1.0
        scale_strength.inputs[1].default_value = 10.0

        pBSDF.inputs["Base Color"].default_value = (0.0, 0.0, 0.0, 1.0)

        # Link nodes

        CurMat.links.new(uv_width.outputs[0], uv_x_div.inputs[1])
        CurMat.links.new(texture_speed_x.outputs[0], uv_x_div.inputs[0])
        CurMat.links.new(texture_speed_x.outputs[0], combine_texture_speeds.inputs[0])
        CurMat.links.new(texture_speed_y.outputs[0], combine_texture_speeds.inputs[1])
        CurMat.links.new(texture_speed_z.outputs[0], combine_texture_speeds.inputs[2])

        CurMat.links.new(uv_x_div.outputs[0], combine_uv.inputs[0])
        CurMat.links.new(uv_height.outputs[0], combine_uv.inputs[1])
        CurMat.links.new(
            combine_texture_speeds.outputs[0], scale_texture_speeds.inputs[0]
        )

        CurMat.links.new(texture_coords.outputs[2], uv_mul.inputs[0])
        CurMat.links.new(texture_coords.outputs[2], uv_speed_div.inputs[0])
        CurMat.links.new(combine_uv.outputs[0], uv_mul.inputs[1])
        CurMat.links.new(scale_texture_speeds.outputs[0], uv_speed_div.inputs[1])

        CurMat.links.new(uv_mul.outputs[0], alpha_mask.inputs[0])
        CurMat.links.new(uv_speed_div.outputs[0], uv_speed_scale.inputs[0])
        CurMat.links.new(dots_scale.outputs[0], uv_speed_scale.inputs[1])

        CurMat.links.new(alpha_mask.outputs[0], combine_masks.inputs[0])

        CurMat.links.new(uv_speed_scale.outputs[0], dots_texture.inputs[0])

        CurMat.links.new(dots_texture.outputs[0], sharpen_mask.inputs[0])

        CurMat.links.new(sharpen_mask.outputs[0], combine_masks.inputs[1])

        CurMat.links.new(combine_masks.outputs[0], pBSDF.inputs["Alpha"])
        CurMat.links.new(combine_masks.outputs[0], apply_mask.inputs[2])
        CurMat.links.new(hologram_colour.outputs[0], apply_mask.inputs[1])
        CurMat.links.new(hologram_strength.outputs[0], scale_strength.inputs[0])

        CurMat.links.new(apply_mask.outputs[0], pBSDF.inputs[sockets["Emission"]])
        CurMat.links.new(scale_strength.outputs[0], pBSDF.inputs["Emission Strength"])

        CurMat.links.new(pBSDF.outputs[0], mat_out.inputs[0])

        # Position nodes

        uv_width.location = (-1253.9, 1.0)
        texture_speed_x.location = (-1253.9, -139.6)
        texture_speed_y.location = (-1253.9, -352.4)
        texture_speed_z.location = (-1253.9, -450.4)

        uv_x_div.location = (-1051.4, 33.5)
        uv_height.location = (-1051.4, -157.8)
        combine_texture_speeds.location = (-1051.4, -269.1)

        texture_coords.location = (-861.4, 238.2)
        combine_uv.location = (-861.4, -39.8)
        scale_texture_speeds.location = (-861.4, -269.1)

        uv_mul.location = (-646.4, 56.6)
        uv_speed_div.location = (-646.4, -269.1)
        dots_scale.location = (-646.4, -437.8)

        alpha_mask.location = (-456.4, 33.1)
        uv_speed_scale.location = (-406.4, -319.0)

        dots_texture.location = (-166.4, -342.5)

        sharpen_mask.location = (123.6, -242.3)

        combine_masks.location = (313.6, -1.5)
        hologram_colour.location = (313.6, -205.6)
        hologram_strength.location = (313.6, -372.0)

        apply_mask.location = (516.1, -92.6)
        scale_strength.location = (516.1, -300.6)

        pBSDF.location = (718.6, 189.7)

        mat_out.location = (1008.6, 189.7)

        # Label nodes

        uv_width.label = "UV Width"
        texture_speed_x.label = "Texture Speed X"
        texture_speed_y.label = "Texture Speed Y"
        texture_speed_z.label = "Texture Speed Z"

        uv_height.label = "UV Height"
        combine_texture_speeds.label = "Combine Texture Speeds"

        scale_texture_speeds.label = "Arbitrary Scale"

        dots_scale.label = "Dots Scale"

        sharpen_mask.label = "Arbitrary Sharpen Mask"

        hologram_colour.label = "Hologram Colour"
        hologram_strength.label = "Hologram Strength"

        apply_mask.label = "Apply Mask"
        scale_strength.label = "Arbitrary Strength Scale"
