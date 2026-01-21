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
    _, data, mat = all_data
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


colour_dicts = {
    "ColorOneStart": {"Red": 255, "Green": 0, "Blue": 0, "Alpha": 255},
    "ColorTwo": {"Red": 8, "Green": 255, "Blue": 237, "Alpha": 255},
    "ColorThree": {"Red": 57, "Green": 170, "Blue": 86, "Alpha": 255},
    "ColorFour": {"Red": 0, "Green": 145, "Blue": 226, "Alpha": 255},
    "ColorFive": {"Red": 0, "Green": 0, "Blue": 0, "Alpha": 255},
    "ColorSix": {"Red": 92, "Green": 0, "Blue": 122, "Alpha": 255},
}


def colour_dict_to_tuple(colour_dict):
    return tuple(float(x) / 255.0 for x in colour_dict.values())


class Signages:
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

        default_main_texture = "base\\fx\\textures\\other\\plazma_mask.xbm"
        main_texture = image_node(all_data, "MainTexture", default_main_texture)
        main_texture.image.colorspace_settings.name = "Non-Color"

        invert_mask = CurMat.nodes.new("ShaderNodeMath")
        invert_mask.operation = "SUBTRACT"

        map_range = CurMat.nodes.new("ShaderNodeMapRange")

        colour_ramp_node = CurMat.nodes.new("ShaderNodeValToRGB")
        colour_ramp_node.color_ramp.interpolation = "CONSTANT"

        default_emissive_ev = 8.10361481
        emission_ev = value_node(all_data, "EmissiveEV", default_emissive_ev)

        arbitrary_emissive_ev_multiply = CurMat.nodes.new("ShaderNodeMath")
        arbitrary_emissive_ev_multiply.operation = "MULTIPLY"

        # Populate values

        invert_mask.inputs[0].default_value = 1

        map_range.inputs[2].default_value = 0.8

        colour_ramp_elements = colour_ramp_node.color_ramp.elements
        colour_ramp_elements.remove(colour_ramp_elements[1])

        for i, (colour_property_name, colour) in enumerate(colour_dicts.items()):
            colour_ramp_element = colour_ramp_elements.new(i / (len(colour_dicts) - 1))
            colour_ramp_element.color = colour_dict_to_tuple(
                Data.get(colour_property_name, colour_dicts)
            )
            colour_ramp_element.position = (i + 1) / len(colour_dicts)

        colour_ramp_elements.remove(colour_ramp_elements[0])

        arbitrary_emissive_ev_multiply.inputs[1].default_value = 10.0

        # Link nodes

        CurMat.links.new(main_texture.outputs[0], invert_mask.inputs[1])
        CurMat.links.new(invert_mask.outputs[0], map_range.inputs[0])
        CurMat.links.new(map_range.outputs[0], colour_ramp_node.inputs[0])

        CurMat.links.new(emission_ev.outputs[0], arbitrary_emissive_ev_multiply.inputs[0])

        CurMat.links.new(colour_ramp_node.outputs[0], pBSDF.inputs["Base Color"])
        CurMat.links.new(colour_ramp_node.outputs[0], pBSDF.inputs[sockets["Emission"]])

        CurMat.links.new(
            arbitrary_emissive_ev_multiply.outputs[0], pBSDF.inputs["Emission Strength"]
        )

        CurMat.links.new(pBSDF.outputs[0], mat_out.inputs[0])

        # Position nodes

        main_texture.location = (-615.6, -35.6)
        invert_mask.location = (-325.6, 85.2)
        map_range.location = (-135.6, 85.2)
        colour_ramp_node.location = (66.9, 85.2)

        emission_ev.location = (-135.6, -257.8)
        arbitrary_emissive_ev_multiply.location = (116.9, -162.8)

        pBSDF.location = (369.4, 89.8)
        mat_out.location = (659.4, 89.8)
