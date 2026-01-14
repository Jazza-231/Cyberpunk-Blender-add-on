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

        print("jazza Data ", Data)

        # start with a clean node tree
        for node in CurMat.nodes:
            CurMat.nodes.remove(node)

        pBSDF = CurMat.nodes.new("ShaderNodeBsdfPrincipled")
        mat_out = CurMat.nodes.new("ShaderNodeOutputMaterial")
        sockets = bsdf_socket_names()

        print('jazza Data["AlphaTexCoordSpeed"]', Data["AlphaTexCoordSpeed"])

        # Make nodes

        AlphaTexCoordSpeed = CurMat.nodes.new("ShaderNodeCombineXYZ")

        AlphaSubUVWidth = CurMat.nodes.new("ShaderNodeValue")
        TextureCoordinates = CurMat.nodes.new("ShaderNodeTexCoord")
        AlphaTexCoordSpeedMul = CurMat.nodes.new("ShaderNodeVectorMath")
        AlphaTexCoordSpeedMul.operation = "MULTIPLY"

        AlphaSubWidthDiv = CurMat.nodes.new("ShaderNodeMath")
        AlphaSubWidthDiv.operation = "DIVIDE"
        AlphaSubUVHeight = CurMat.nodes.new("ShaderNodeValue")
        TextureCoordinatesDiv = CurMat.nodes.new("ShaderNodeVectorMath")
        TextureCoordinatesDiv.operation = "DIVIDE"
        DotsCoords = CurMat.nodes.new("ShaderNodeValue")

        CombineUV = CurMat.nodes.new("ShaderNodeCombineXYZ")
        DotsCoordsMul = CurMat.nodes.new("ShaderNodeVectorMath")
        DotsCoordsMul.operation = "MULTIPLY"

        CombineUVMul = CurMat.nodes.new("ShaderNodeVectorMath")
        CombineUVMul.operation = "MULTIPLY"
        DotsTexture = CreateShaderNodeTexImage(
            CurMat,
            os.path.join(self.BasePath, Data["Dots"]),
            -800,
            -250,
            "DotsTexture",
            self.image_format,
        )

        AlphaMask = CreateShaderNodeTexImage(
            CurMat,
            os.path.join(self.BasePath, Data["AlphaMask"]),
            -800,
            -250,
            "AlphaMask",
            self.image_format,
        )
        DotsTextureMul = CurMat.nodes.new("ShaderNodeMath")
        DotsTextureMul.operation = "MULTIPLY"

        AlphaMaskMul = CurMat.nodes.new("ShaderNodeMath")
        AlphaMaskMul.operation = "MULTIPLY"
        ColorParam = CreateShaderNodeRGB(
            CurMat,
            Data["ColorParam"],
            -400,
            200,
            "ColorParam",
        )

        ColorParamMul = CurMat.nodes.new("ShaderNodeMixRGB")
        ColorParamMul.blend_type = "MULTIPLY"
        # Populate nodes

        AlphaTexCoordSpeed.inputs[0].default_value = Data["AlphaTexCoordSpeed"]["X"]
        AlphaTexCoordSpeed.inputs[1].default_value = Data["AlphaTexCoordSpeed"]["Y"]
        AlphaTexCoordSpeed.inputs[2].default_value = Data["AlphaTexCoordSpeed"]["Z"]

        AlphaSubUVWidth.outputs[0].default_value = Data["AlphaSubUVWidth"]
        AlphaTexCoordSpeedMul.inputs[1].default_value = (1.0, 100.0, 1.0)

        AlphaSubWidthDiv.inputs[0].default_value = Data["AlphaTexCoordSpeed"]["X"]
        AlphaSubUVHeight.outputs[0].default_value = abs(Data["AlphaSubUVHeight"])
        DotsCoords.outputs[0].default_value = Data["DotsCoords"] * 10.0

        CombineUV.inputs[2].default_value = 1.0

        DotsTextureMul.inputs[1].default_value = 5.0

        ColorParamMul.inputs[0].default_value = 1.0

        pBSDF.inputs["Base Color"].default_value = (0.0, 0.0, 0.0, 1.0)
        pBSDF.inputs["Emission Strength"].default_value = 5.0

        # Link nodes

        CurMat.links.new(AlphaTexCoordSpeed.outputs[0], AlphaTexCoordSpeedMul.inputs[0])

        CurMat.links.new(AlphaSubUVWidth.outputs[0], AlphaSubWidthDiv.inputs[1])
        CurMat.links.new(TextureCoordinates.outputs[2], CombineUVMul.inputs[0])
        CurMat.links.new(TextureCoordinates.outputs[2], TextureCoordinatesDiv.inputs[0])
        CurMat.links.new(
            AlphaTexCoordSpeedMul.outputs[0], TextureCoordinatesDiv.inputs[1]
        )

        CurMat.links.new(AlphaSubWidthDiv.outputs[0], CombineUV.inputs[0])
        CurMat.links.new(AlphaSubUVHeight.outputs[0], CombineUV.inputs[1])
        CurMat.links.new(TextureCoordinatesDiv.outputs[0], DotsCoordsMul.inputs[0])
        CurMat.links.new(DotsCoords.outputs[0], DotsCoordsMul.inputs[1])

        CurMat.links.new(CombineUV.outputs[0], CombineUVMul.inputs[1])
        CurMat.links.new(DotsCoordsMul.outputs[0], DotsTexture.inputs[0])

        CurMat.links.new(CombineUVMul.outputs[0], AlphaMask.inputs[0])
        CurMat.links.new(DotsTexture.outputs[0], DotsTextureMul.inputs[0])

        CurMat.links.new(AlphaMask.outputs[0], AlphaMaskMul.inputs[0])
        CurMat.links.new(DotsTextureMul.outputs[0], AlphaMaskMul.inputs[1])

        CurMat.links.new(AlphaMaskMul.outputs[0], ColorParamMul.inputs[2])
        CurMat.links.new(AlphaMaskMul.outputs[0], pBSDF.inputs["Alpha"])
        CurMat.links.new(ColorParam.outputs[0], ColorParamMul.inputs[1])

        CurMat.links.new(ColorParamMul.outputs[0], pBSDF.inputs[sockets["Emission"]])

        CurMat.links.new(pBSDF.outputs[0], mat_out.inputs[0])

        # Position nodes

        AlphaTexCoordSpeed.location = (-1147.8, -241.9)

        AlphaSubUVWidth.location = (-957.8, 205.7)
        TextureCoordinates.location = (-957.8, 107.7)
        AlphaTexCoordSpeedMul.location = (-957.8, -241.9)

        AlphaSubWidthDiv.location = (-742.8, 47.4)
        AlphaSubUVHeight.location = (-742.8, -143.9)
        TextureCoordinatesDiv.location = (-742.8, -241.9)
        DotsCoords.location = (-742.8, -410.6)

        CombineUV.location = (-552.8, -26.2)
        DotsCoordsMul.location = (-552.8, -291.7)

        CombineUVMul.location = (-312.8, 43.8)
        DotsTexture.location = (-362.8, -315.3)

        AlphaMask.location = (-72.8, 19.9)
        DotsTextureMul.location = (-22.8, -215.6)

        AlphaMaskMul.location = (217.2, -0.9)
        ColorParam.location = (217.2, -205.1)

        ColorParamMul.location = (419.7, -92.4)

        pBSDF.location = (609.7, 135.8)

        mat_out.location = (899.7, 135.8)
