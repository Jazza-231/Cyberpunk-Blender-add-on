import os
from ..main.common import (
    CreateShaderNodeTexImage,
    CreateShaderNodeRGB,
    CreateShaderNodeValue,
    bsdf_socket_names,
)


# My own because I dont need to specify the other stuff every time, e.g. I reposition later
def image_node(all_data, name, default_path):
    mat_self, data, mat = all_data

    image = CreateShaderNodeTexImage(
        mat.node_tree,
        os.path.join(mat_self.BasePath, data.get(name, default_path)),
        0,
        0,
        name,
        mat_self.image_format,
    )
    return image


def colour_node(all_data, name, default_colour):
    mat_self, data, mat = all_data
    colour = CreateShaderNodeRGB(
        mat.node_tree,
        data.get(name, default_colour),
        0,
        0,
        name,
    )
    return colour


def value_node(all_data, name, default_value):
    _, data, mat = all_data
    value = CreateShaderNodeValue(
        mat.node_tree,
        data.get(name, default_value),
        0,
        0,
        name,
    )
    return value


def link_nodes(CurMat, socket1, socket2):
    CurMat.links.new(socket1, socket2)


class DeviceDiode:
    def __init__(self, BasePath, image_format, ProjPath):
        self.BasePath = BasePath
        self.ProjPath = ProjPath
        self.image_format = image_format

    def create(self, Data, Mat):
        all_data = (self, Data, Mat)
        CurMat = Mat.node_tree

        # start with a clean node tree
        for node in CurMat.nodes:
            CurMat.nodes.remove(node)

        pBSDF = CurMat.nodes.new("ShaderNodeBsdfPrincipled")
        mat_out = CurMat.nodes.new("ShaderNodeOutputMaterial")
        sockets = bsdf_socket_names()

        # Make nodes

        default_base_colour = "base\\surfaces\\materials\\common\\plastic_common_01_300_d.xbm"
        base_colour_texture = image_node(all_data, "BaseColor", default_base_colour)

        default_base_colour_scale = (150, 0, 0, 0)
        base_colour_scale = colour_node(all_data, "BaseColorScale", default_base_colour_scale)

        base_colour_multiply = CurMat.nodes.new("ShaderNodeMixRGB")
        base_colour_multiply.blend_type = "MULTIPLY"

        default_roughness = (
            "base\\surfaces\\materials\\plastic\\plastic_lightcover\\plastic_lightcover_01_50_r.xbm"
        )
        roughness = image_node(all_data, "Roughness", default_roughness)

        default_normal_texture = (
            "base\\surfaces\\materials\\plastic\\plastic_lightcover\\plastic_lightcover_01_50_n.xbm"
        )
        normal_texture = image_node(all_data, "Normal", default_normal_texture)

        normal_map = CurMat.nodes.new("ShaderNodeNormalMap")

        default_emissive_texture = (
            "base\\fx\\_textures\\masks\\gradients\\fx_reflected_vertical_gradient_01_d.xbm"
        )
        emissive_texture = image_node(all_data, "Emissive", default_emissive_texture)

        default_emissive_ev = 5.0
        emissive_ev = value_node(all_data, "EmissiveEV", default_emissive_ev)

        arbitrary_emissive_ev_multiply = CurMat.nodes.new("ShaderNodeMath")
        arbitrary_emissive_ev_multiply.operation = "MULTIPLY"

        emission_strength_multiply = CurMat.nodes.new("ShaderNodeMath")
        emission_strength_multiply.operation = "MULTIPLY"

        default_emissive_colour1 = (127, 0, 0)
        emissive_colour1 = colour_node(all_data, "EmissiveColor1", default_emissive_colour1)

        default_emissive_colour2 = (0, 0, 127)
        emissive_colour2 = colour_node(all_data, "EmissiveColor2", default_emissive_colour2)

        default_blinking_speed = 8.0
        blinking_speed = value_node(all_data, "BlinkingSpeed", default_blinking_speed)

        # Populate values

        base_colour_multiply.inputs[0].default_value = 1
        arbitrary_emissive_ev_multiply.inputs[1].default_value = 10.0

        # Link nodes

        CurMat.links.new(pBSDF.outputs[0], mat_out.inputs[0])

        CurMat.links.new(base_colour_texture.outputs[0], base_colour_multiply.inputs[1])
        CurMat.links.new(base_colour_scale.outputs[0], base_colour_multiply.inputs[2])
        CurMat.links.new(base_colour_multiply.outputs[0], pBSDF.inputs["Base Color"])

        CurMat.links.new(roughness.outputs[0], pBSDF.inputs["Roughness"])

        CurMat.links.new(normal_texture.outputs[0], normal_map.inputs[1])
        CurMat.links.new(normal_map.outputs[0], pBSDF.inputs["Normal"])

        CurMat.links.new(emissive_colour1.outputs[0], pBSDF.inputs[sockets["Emission"]])

        CurMat.links.new(emissive_ev.outputs[0], arbitrary_emissive_ev_multiply.inputs[0])
        CurMat.links.new(
            arbitrary_emissive_ev_multiply.outputs[0], emission_strength_multiply.inputs[0]
        )
        CurMat.links.new(emissive_texture.outputs[0], emission_strength_multiply.inputs[1])
        CurMat.links.new(emission_strength_multiply.outputs[0], pBSDF.inputs["Emission Strength"])

        # Position nodes

        base_colour_texture.location = (-300.0, 206.6)
        base_colour_scale.location = (-250.0, 129.5)
        base_colour_multiply.location = (40.0, 294.6)

        roughness.location = (-10.0, 81.7)

        normal_texture.location = (-300.0, -112.2)
        normal_map.location = (35.0, 8.2)

        emissive_colour1.location = (40.0, -186.3)

        emissive_ev.location = (-490.0, -317.1)
        arbitrary_emissive_ev_multiply.location = (-250.0, -222.3)
        emissive_texture.location = (-300.0, -417.2)
        emission_strength_multiply.location = (40.0, -259.8)

        pBSDF.location = (292.5, 134.2)
        mat_out.location = (582.5, 134.2)

        blinking_speed.location = (582.5, 207.7)
        emissive_colour2.location = (582.5, -54.0)

        # Label nodes

        base_colour_texture.label = "Base Colour Texture"
        base_colour_scale.label = "Base Colour"
        base_colour_multiply.label = "Multiple Base Colour"
