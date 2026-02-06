import bpy
import bpy.utils.previews
import sys
from ..exporters import CP77HairProfileExport, mlsetup_export
from ..main.bartmoss_functions import *
from ..main.common import get_classes, get_color_presets, save_presets
from bpy.props import StringProperty, EnumProperty, PointerProperty, CollectionProperty
from bpy.types import Scene, Operator, Panel
from ..cyber_props import CP77RefitList
from ..icons.cp77_icons import get_icon
import numpy as np
import ast
from bpy_extras.io_utils import ExportHelper
from ..importers.import_with_materials import CP77GLBimport

last_active_object = None
last_palette = None
last_multilayer_index = 0
last_multilayer_color_index = None
last_palette_color = None
last_paint_brush = None


def get_layernode_by_socket(self, context):
    if bpy.context.object is None:
        return
    if bpy.context.object.active_material is None:
        return
    if bpy.context.object.active_material.get("MLSetup") is None:
        return

    active_object = bpy.context.active_object
    active_material = active_object.active_material
    LayerGroup = None

    nodes = active_material.node_tree.nodes
    layer_index = bpy.context.scene.multilayer_index_int

    mlBSDFGroup = nodes.get("Multilayered 1.8.0")
    if mlBSDFGroup:
        socket_name = "Layer " + str(layer_index)
        socket = mlBSDFGroup.inputs.get(socket_name)
        if socket.is_linked:
            layerGroupLink = socket.links[0]
            linkedLayerGroupName = layerGroupLink.from_node.name
            LayerGroup = nodes[linkedLayerGroupName]
            # print(layer_index, " | ", LayerGroup.name)
        else:
            return None

    return LayerGroup


def active_object_listener(self, context):
    global last_active_object
    if bpy.context.active_object != last_active_object:
        bpy.app.timers.register(check_if_multilayer_object)

    last_active_object = bpy.context.active_object


def check_if_multilayer_object():
    # Remove palette first to prevent setting errant color
    bpy.context.tool_settings.gpencil_paint.palette = None
    mat = bpy.context.object.active_material
    bpy.context.scene.multilayer_object_bool = False
    if mat:
        if "MLSetup" in mat:
            bpy.context.scene.multilayer_object_bool = True

    bpy.context.scene.multilayer_index_int = 1


# JATO: not used
def apply_mltemplate_mlsetup():
    bpy.ops.set_layer_mltemplate.mlsetup()


# JATO: TODO Stop this check from running constantly -- DONE???
def check_palette_change(self, context):
    print("check pal change fired")
    global last_palette
    global last_multilayer_index
    ts = context.tool_settings

    # JATO: check if layer index changed to avoid calling bpy.ops mltemplate when palette changes due to layer change
    # this check is running constantly so we tell a sweet little lie about the palette for the subsequent checks
    if last_multilayer_index != bpy.context.scene.multilayer_index_int:
        last_multilayer_index = bpy.context.scene.multilayer_index_int
        last_palette = ts.gpencil_paint.palette
        return

    active_palette = ts.gpencil_paint.palette
    if active_palette != last_palette:
        bpy.app.timers.register(apply_mltemplate_mlsetup)

    last_palette = ts.gpencil_paint.palette
    last_multilayer_index = bpy.context.scene.multilayer_index_int


# JATO: not used - useful for enum list of palettes
def get_palette_items(self, context):
    items = []
    for palette in bpy.data.palettes:
        items.append((palette.name, palette.name, ""))
    return items


def apply_mlsetup_color_override():
    bpy.ops.apply_color_override.mlsetup()


def check_palette_col_change(self, context):
    global last_palette_color
    global last_multilayer_color_index
    ts = context.tool_settings
    palette = ts.gpencil_paint.palette

    if palette:
        if last_multilayer_color_index != bpy.context.scene.multilayer_index_int:
            last_multilayer_color_index = bpy.context.scene.multilayer_index_int
            last_palette_color = palette.colors.active.color
            return

        new_palette_color = palette.colors.active.color
        if new_palette_color != last_palette_color:
            bpy.app.timers.register(apply_mlsetup_color_override)

        last_palette_color = palette.colors.active.color


def switch_brush_44(brush_name):
    brush = bpy.data.brushes.get(brush_name)
    if not brush:
        # print(f"Brush '{brush_name}' not found in bpy.data.brushes.")
        return False
    try:
        identifier = "brushes\\essentials_brushes-mesh_texture.blend\\Brush\\" + brush.name
        bpy.ops.brush.asset_activate(
            asset_library_type="ESSENTIALS",
            asset_library_identifier="",
            relative_asset_identifier=identifier,
        )
        # print(f"Successfully activated: {brush.name}")
        return True
    except Exception as e:
        # print(f"Failed to switch brush: {e}")
        return False


def apply_view_mask(self, context):
    if bpy.context.object is None:
        return
    if bpy.context.object.active_material is None:
        return
    if bpy.context.object.active_material.get("MLSetup") is None:
        return
    nt = bpy.context.object.active_material.node_tree
    nodes = nt.nodes

    LayerGroup = get_layernode_by_socket(self, context)

    if context.scene.multilayer_view_mask_bool == True:
        if not nodes.get("Multilayered Mask Output"):
            view_mask_output_node = nodes.new(type="ShaderNodeOutputMaterial")
            view_mask_output_node.name = "Multilayered Mask Output"
            view_mask_output_node.location = (-200, 400)
            view_mask_output_node.is_active_output = True
        else:
            view_mask_output_node = nodes.get("Multilayered Mask Output")
            view_mask_output_node.is_active_output = True

        # LayerGroup.select = True
        nt.links.new(LayerGroup.outputs["Layer Mask"], view_mask_output_node.inputs[0])

    else:
        nodes.remove(nodes.get("Multilayered Mask Output"))


def apply_paint_mask(self, context):
    global last_paint_brush

    if bpy.context.scene.multilayer_index_int == 1:
        return
    if context.scene.multilayer_paint_mask_bool == True:
        bpy.ops.enter_texture_paint.mlsetup()
        switch_brush_44(last_paint_brush)
    else:
        last_paint_brush = bpy.context.tool_settings.image_paint.brush.name

        switch_brush_44("Blur")
        bpy.ops.object.mode_set(mode="OBJECT")


def load_panel_data(self, context):
    if bpy.app.version[0] < 5:
        return
    if bpy.context.object is None:
        return
    if bpy.context.object.active_material is None:
        return
    if bpy.context.object.active_material.get("MLSetup") is None:
        return

    LayerGroup = get_layernode_by_socket(self, context)
    if LayerGroup == None:
        bpy.context.scene.multilayer_has_linked_layer = False
        # self.report({'ERROR'}, 'A valid Multilayered node group was not found.')
        return
    bpy.context.scene.multilayer_has_linked_layer = True

    # JATO: try setting mask as active then update any image editor windows to show active mask
    nodes = bpy.context.object.active_material.node_tree.nodes
    MaskNode = None
    socket_name = "Mask"
    socket = LayerGroup.inputs.get(socket_name)
    if socket.is_linked:
        bpy.context.scene.multilayer_paint_mask_enable_bool = True
        maskNodeLink = socket.links[0]
        linkedMaskNodeName = maskNodeLink.from_node.name
        MaskNode = nodes[linkedMaskNodeName]
        nodes.active = MaskNode
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == "IMAGE_EDITOR":
                    space = area.spaces.active
                    space.image = MaskNode.image
    else:
        bpy.context.scene.multilayer_paint_mask_enable_bool = False

    # JATO: TODO test error tolerance numbers
    # JATO: 0.00005 causes color mismatch on panam pants group #3 / layer 4, narrowed to 0.00001
    matchTolerance = 0.00001

    if context.scene.multilayer_view_mask_bool == True:
        apply_view_mask(self, context)
    if context.scene.multilayer_paint_mask_bool == True:
        apply_paint_mask(self, context)

    colorscale = (LayerGroup.inputs["ColorScale"].default_value[::])[:-1]
    normstr = LayerGroup.inputs["NormalStrength"].default_value
    metin = LayerGroup.inputs["MetalLevelsIn"].default_value[::]
    metout = LayerGroup.inputs["MetalLevelsOut"].default_value[::]
    rouin = LayerGroup.inputs["RoughLevelsIn"].default_value[::]
    rouout = LayerGroup.inputs["RoughLevelsOut"].default_value[::]

    # JATO: We get overrides after selecting the right layer and before matching palette color
    bpy.ops.get_layer_overrides.mlsetup()

    active_palette = bpy.context.tool_settings.gpencil_paint.palette

    # bpy.context.scene.multilayer_palette_string = active_palette.name
    # bpy.context.scene.multilayer_palette_enum = active_palette.name

    if active_palette:
        palette_colors = active_palette.colors

        for pal_col in palette_colors:
            col_tuple = pal_col.color[:]
            err = np.sum(np.abs(np.subtract(col_tuple, colorscale)))
            if abs(err) < matchTolerance:
                break
        for elem_nrmstr in active_palette["NormalStrengthList"]:
            elem_nrmstr_float = float(elem_nrmstr)
            err = np.sum(np.subtract(elem_nrmstr_float, normstr))
            if abs(err) < matchTolerance:
                break
        for elem_metin in active_palette["MetalLevelsInList"]:
            elem_metin_list = ast.literal_eval(elem_metin)
            err = np.sum(np.abs(np.subtract(elem_metin_list, metin)))
            if abs(err) < matchTolerance:
                break
        for elem_metout in active_palette["MetalLevelsOutList"]:
            elem_metout_list = ast.literal_eval(elem_metout)
            err = np.sum(np.abs(np.subtract(elem_metout_list, metout)))
            if abs(err) < matchTolerance:
                break
        for elem_rouin in active_palette["RoughLevelsInList"]:
            elem_rouin_list = ast.literal_eval(elem_rouin)
            err = np.sum(np.abs(np.subtract(elem_rouin_list, rouin)))
            if abs(err) < matchTolerance:
                break
        for elem_rouout in active_palette["RoughLevelsOutList"]:
            elem_rouout_list = ast.literal_eval(elem_rouout)
            err = np.sum(np.abs(np.subtract(elem_rouout_list, rouout)))
            if abs(err) < matchTolerance:
                break

        bpy.context.tool_settings.gpencil_paint.palette.colors.active = pal_col
        bpy.context.scene.multilayer_normalstr_enum = elem_nrmstr
        bpy.context.scene.multilayer_metalin_enum = elem_metin
        bpy.context.scene.multilayer_metalout_enum = elem_metout
        bpy.context.scene.multilayer_roughin_enum = elem_rouin
        bpy.context.scene.multilayer_roughout_enum = elem_rouout


def apply_mltemplate(self, context):
    global last_palette
    global last_multilayer_index
    ts = context.tool_settings

    # print("palette ml index: ", last_multilayer_index, "  |  ", bpy.context.scene.multilayer_index_int, " ---------------")

    if last_multilayer_index != bpy.context.scene.multilayer_index_int:
        last_palette = ts.gpencil_paint.palette
        return

    bpy.context.tool_settings.gpencil_paint.palette = bpy.data.palettes.get(
        bpy.context.scene.multilayer_palette_string
    )

    active_palette = ts.gpencil_paint.palette
    if active_palette != last_palette:
        print("mltemplate operator called")
        bpy.ops.set_layer_mltemplate.mlsetup()

    # bpy.ops.set_layer_mltemplate.mlsetup()
    # bpy.context.tool_settings.gpencil_paint.palette = bpy.data.palettes.get(bpy.context.scene.multilayer_palette_enum)

    last_palette = ts.gpencil_paint.palette


def microblend_filter(self, object):
    if bpy.context.scene.multilayer_microblend_filter_bool == False:
        return True
    abs_path = bpy.path.abspath(object.filepath)
    # Check if "textures" is part of the path string
    return "microblend" in abs_path.lower()


def apply_microblend_mlsetup(self, context):
    global last_multilayer_index
    print(
        "microblend fired ml index: ",
        last_multilayer_index,
        "  |  ",
        bpy.context.scene.multilayer_index_int,
    )
    if last_multilayer_index != bpy.context.scene.multilayer_index_int:
        return
    bpy.ops.apply_microblend.mlsetup()
    print("microblend operator called")


def get_normalstr_ovrd(self, context):
    normal_str_list = []
    ts = context.tool_settings
    active_palette = ts.gpencil_paint.palette
    if active_palette:
        for x in active_palette["NormalStrengthList"]:
            normal_str_list.append((x, x, f"Select {x}"))
        return normal_str_list


def get_metalin_ovrd(self, context):
    metal_in_list = []
    ts = context.tool_settings
    active_palette = ts.gpencil_paint.palette
    if active_palette:
        for x in active_palette["MetalLevelsInList"]:
            metal_in_list.append((x, x, f"Select {x}"))
        return metal_in_list


def get_metalout_ovrd(self, context):
    metal_out_list = []
    ts = context.tool_settings
    active_palette = ts.gpencil_paint.palette
    if active_palette:
        for x in active_palette["MetalLevelsOutList"]:
            metal_out_list.append((x, x, f"Select {x}"))
        return metal_out_list


def get_roughin_ovrd(self, context):
    rough_in_list = []
    ts = context.tool_settings
    active_palette = ts.gpencil_paint.palette
    if active_palette:
        for x in active_palette["RoughLevelsInList"]:
            rough_in_list.append((x, x, f"Select {x}"))
        return rough_in_list


def get_roughout_ovrd(self, context):
    rough_out_list = []
    ts = context.tool_settings
    active_palette = ts.gpencil_paint.palette
    if active_palette:
        for x in active_palette["RoughLevelsOutList"]:
            rough_out_list.append((x, x, f"Select {x}"))
        return rough_out_list


def apply_normalstr_ovrd(self, context):
    global last_multilayer_index
    print(
        "nrml fired ml index: ",
        last_multilayer_index,
        "  |  ",
        bpy.context.scene.multilayer_index_int,
    )
    if last_multilayer_index != bpy.context.scene.multilayer_index_int:
        return
    bpy.ops.apply_normalstr_override.mlsetup()
    print("normalstr operator called")


def apply_metalin_ovrd(self, context):
    global last_multilayer_index
    print(
        "metalin fired ml index: ",
        last_multilayer_index,
        "  |  ",
        bpy.context.scene.multilayer_index_int,
    )
    if last_multilayer_index != bpy.context.scene.multilayer_index_int:
        return
    bpy.ops.apply_metalin_override.mlsetup()
    print("metalin operator called")


def apply_metalout_ovrd(self, context):
    global last_multilayer_index
    print(
        "metalout fired ml index: ",
        last_multilayer_index,
        "  |  ",
        bpy.context.scene.multilayer_index_int,
    )
    if last_multilayer_index != bpy.context.scene.multilayer_index_int:
        return
    bpy.ops.apply_metalout_override.mlsetup()
    print("metalout operator called")


def apply_roughin_ovrd(self, context):
    global last_multilayer_index
    print(
        "roughin fired ml index: ",
        last_multilayer_index,
        "  |  ",
        bpy.context.scene.multilayer_index_int,
    )
    if last_multilayer_index != bpy.context.scene.multilayer_index_int:
        return
    bpy.ops.apply_roughin_override.mlsetup()
    print("roughin operator called")


# JATO: important! idk why but this is always the last function executed so we update the last_multilayer_index here
def apply_roughout_ovrd(self, context):
    global last_multilayer_index
    print(
        "roughout fired ml index: ",
        last_multilayer_index,
        "  |  ",
        bpy.context.scene.multilayer_index_int,
    )
    if last_multilayer_index != bpy.context.scene.multilayer_index_int:
        last_multilayer_index = bpy.context.scene.multilayer_index_int
        return
    bpy.ops.apply_roughout_override.mlsetup()
    print("roughout operator called")
    last_multilayer_index = bpy.context.scene.multilayer_index_int


# JATO: TODO idk where these props should go, probably somewhere else?
bpy.types.Scene.multilayer_index_int = bpy.props.IntProperty(
    name="Layer", default=1, min=1, max=20, update=load_panel_data
)
bpy.types.Scene.multilayer_palette_string = bpy.props.StringProperty(
    name="MLTEMPLATE", update=apply_mltemplate
)
bpy.types.Scene.multilayer_object_bool = bpy.props.BoolProperty(name="", default=False)
bpy.types.Scene.multilayer_overrides_disconnected_bool = bpy.props.BoolProperty(
    name="Toggle Override Method", default=False
)
bpy.types.Scene.multilayer_paint_mask_enable_bool = bpy.props.BoolProperty(name="", default=False)
bpy.types.Scene.multilayer_view_mask_bool = bpy.props.BoolProperty(
    name="View Mask", default=False, update=apply_view_mask
)
bpy.types.Scene.multilayer_paint_mask_bool = bpy.props.BoolProperty(
    name="Paint Mask", default=False, update=apply_paint_mask
)
bpy.types.Scene.multilayer_has_linked_layer = bpy.props.BoolProperty(name="", default=True)
bpy.types.Scene.multilayer_normalstr_enum = bpy.props.EnumProperty(
    name="NormalStrength",
    description="NormalStrength",
    items=get_normalstr_ovrd,
    update=apply_normalstr_ovrd,
    default=0,
)
bpy.types.Scene.multilayer_metalin_enum = bpy.props.EnumProperty(
    name="MetalLevelsIn",
    description="MetalLevelsIn",
    items=get_metalin_ovrd,
    update=apply_metalin_ovrd,
    default=0,
)
bpy.types.Scene.multilayer_metalout_enum = bpy.props.EnumProperty(
    name="MetalLevelsOut",
    description="MetalLevelsOut",
    items=get_metalout_ovrd,
    update=apply_metalout_ovrd,
    default=0,
)
bpy.types.Scene.multilayer_roughin_enum = bpy.props.EnumProperty(
    name="RoughLevelsIn",
    description="RoughLevelsIn",
    items=get_roughin_ovrd,
    update=apply_roughin_ovrd,
    default=0,
)
bpy.types.Scene.multilayer_roughout_enum = bpy.props.EnumProperty(
    name="RoughLevelsOut",
    description="RoughLevelsOut",
    items=get_roughout_ovrd,
    update=apply_roughout_ovrd,
    default=0,
)
bpy.types.Scene.multilayer_microblend_pointer = bpy.props.PointerProperty(
    type=bpy.types.Image, name="Microblend", update=apply_microblend_mlsetup, poll=microblend_filter
)
bpy.types.Scene.multilayer_microblend_filter_bool = bpy.props.BoolProperty(
    name="Microblend Filter",
    description="Filters available images for filepaths containing 'microblend'",
    default=True,
)

# bpy.types.Scene.multilayer_palette_enum = bpy.props.EnumProperty(name="MLTEMPLATE",description="",items=get_palette_items,update=apply_mltemplate)


class CP77_PT_MaterialTools(Panel):
    bl_label = "Material Tools"
    bl_idname = "CP77_PT_MaterialTools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "CP77 Modding"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        cp77_addon_prefs = bpy.context.preferences.addons["i_scene_cp77_gltf"].preferences
        if cp77_addon_prefs.context_only:
            return context.active_object and context.active_object.type == "MESH"
        else:
            return context

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        box1 = layout.box()
        props = context.scene.cp77_panel_props
        vers = bpy.app.version

        # JATO: can be used to display selected node name
        # nt = bpy.context.object.active_material.node_tree
        # selected_nodes = [n for n in nt.nodes if n.select]

        cp77_addon_prefs = bpy.context.preferences.addons["i_scene_cp77_gltf"].preferences
        if cp77_addon_prefs.show_modtools:
            if cp77_addon_prefs.show_meshtools:
                ts = context.tool_settings
                palette = ts.gpencil_paint.palette

                active_palette = bpy.context.tool_settings.gpencil_paint.palette

                box1.label(text="Materials", icon="MATERIAL")
                col = box1.column()
                if vers[0] < 5:
                    row_error = col.row()
                    row_error.alert = True
                    row_error.label(
                        text="Upgrade to Blender 5 for Multilayer features", icon="ERROR"
                    )
                    return

                col.operator("reload_material.cp77")
                col.operator("export_scene.hp")
                col.operator("create_multilayer_object.mlsetup", icon="ADD")

                box2 = layout.box()
                box2.enabled = bpy.context.scene.multilayer_object_bool
                box2.label(text="MULTILAYERED")
                col = box2.column()

                row_overrides = col.row()
                if scene.multilayer_overrides_disconnected_bool == False:
                    row_overrides.operator("generate_layer_overrides.mlsetup")
                else:
                    row_overrides.operator("generate_layer_overrides_disconnected.mlsetup")
                row_overrides.prop(
                    scene,
                    "multilayer_overrides_disconnected_bool",
                    text="",
                    icon="MESH_MONKEY",
                    toggle=True,
                )

                row_export = col.row()
                row_export.operator("export_scene.mlsetup")
                row_export.operator("export_mlmasks.mlsetup")

                if bpy.context.scene.multilayer_object_bool == False:
                    row_error = col.row()
                    row_error.alignment = "CENTER"
                    row_error.scale_y = 3
                    row_error.label(text="Select a Multilayer object to access Multilayer-Editing")
                    return
                if not active_palette:
                    row_error = col.row()
                    row_error.alignment = "CENTER"
                    row_error.scale_y = 3
                    row_error.label(text="Generate Overrides to access Multilayer-Editing")
                    return
                if "MLTemplatePath" not in active_palette:
                    row_error = col.row()
                    row_error.alignment = "CENTER"
                    row_error.scale_y = 3
                    row_error.alert = True
                    row_error.label(
                        text="Active Palette does not have MLTemplate Data", icon="ERROR"
                    )
                    return

                box3 = layout.box()
                col = box3.column()
                row_layer = col.row()
                row_layer.scale_x = 1.25
                row_layer.scale_y = 1.25
                row_layer.prop(scene, "multilayer_index_int", text="")
                row_layer.operator("refresh_layer.mlsetup", text="", icon="FILE_REFRESH")

                if bpy.context.scene.multilayer_has_linked_layer == False:
                    row = col.row()
                    row.scale_y = 2
                    row.alert = True
                    row.label(text=f"Empty Layer - No link detected", icon="ERROR")
                    return

                row = col.row()
                row.scale_y = 1.5
                col_paint = row.column()
                col_paint.prop(scene, "multilayer_paint_mask_bool", toggle=True)
                col_paint.enabled = scene.multilayer_paint_mask_enable_bool
                row.prop(scene, "multilayer_view_mask_bool", toggle=True)

                rowColor = box3.row(align=True)

                row_mltemplate = col.row()
                row_mltemplate.scale_x = 1.5
                row_mltemplate.scale_y = 1.5
                row_mltemplate.prop_search(
                    scene, "multilayer_palette_string", bpy.data, "palettes", text=""
                )

                # row_mltemplate2 = col.row()
                # row_mltemplate2.scale_x = 1.5
                # row_mltemplate2.scale_y = 1.5
                # row_mltemplate2.prop(scene, "multilayer_palette_enum", text="")
                # row_mltemplate.prop_menu_enum(scene, "multilayer_palette_enum")
                # row_mltemplate.template_ID(ts.gpencil_paint, "palette", new="palette.new")

                row_mltemp = col.row()
                row_mltemp.label(text=(str(active_palette["MLTemplatePath"])).split(".")[0])
                row_mltemp.active = False
                row_mb = col.row()
                row_mb.prop(scene, "multilayer_microblend_pointer")
                row_mb.prop(
                    scene,
                    "multilayer_microblend_filter_bool",
                    text="",
                    icon="VIEWZOOM",
                    toggle=True,
                )
                col.prop(scene, "multilayer_normalstr_enum")
                col.prop(scene, "multilayer_metalin_enum")
                col.prop(scene, "multilayer_metalout_enum")
                col.prop(scene, "multilayer_roughin_enum")
                col.prop(scene, "multilayer_roughout_enum")

                palette_box = box3.column()
                palette_box.template_palette(ts.gpencil_paint, "palette", color=True)

                # if ts.gpencil_paint.palette:
                #     colR, colG, colB = palette.colors.active.color
                #     rowColor.label(text="Color  {:.4f}  {:.4f}  {:.4f}".format(colR, colG, colB))


class CP77MlSetupGenerateOverrides(Operator):
    bl_idname = "generate_layer_overrides.mlsetup"
    bl_label = "Generate Overrides"
    bl_description = "Create Override data for Layers connected to the Multilayered shader node."

    def execute(self, context):
        mlsetup_export.cp77_mlsetup_generateoverrides(self, context)

        bpy.ops.get_layer_overrides.mlsetup()

        # Do this to trigger update function so active color is set when we first generate overrides
        bpy.context.scene.multilayer_index_int = 1

        return {"FINISHED"}


class CP77MlSetupGenerateOverridesDisconnected(Operator):
    bl_idname = "generate_layer_overrides_disconnected.mlsetup"
    bl_label = "Generate Overrides for All Nodes"
    bl_description = "Create Override data for Layers using the mat_mod_layer naming scheme found within the selected material. Useful for generating extra multilayer-resources with a modified MLSETUP json."

    def execute(self, context):
        mlsetup_export.cp77_mlsetup_generateoverrides(self, context, include_disconnected=True)

        bpy.ops.get_layer_overrides.mlsetup()

        # Do this to trigger update function so active color is set when we first generate overrides
        bpy.context.scene.multilayer_index_int = 1

        return {"FINISHED"}


class CP77MlSetupRefreshOverrides(Operator):
    bl_idname = "refresh_layer.mlsetup"
    bl_label = "Refresh Layer"
    bl_description = "Refreshes the active Multilayered Layer data"

    def execute(self, context):
        bpy.context.scene.multilayer_index_int = bpy.context.scene.multilayer_index_int

        return {"FINISHED"}


class CP77MlSetupGetOverrides(Operator):
    bl_idname = "get_layer_overrides.mlsetup"
    bl_label = "View Layer Overrides"
    bl_description = (
        "View the Overrides for the MLTemplate within the selected Multilayered Layer Node Group"
    )

    def execute(self, context):
        ts = context.tool_settings
        active_object = bpy.context.active_object
        if (
            not active_object
            or active_object.material_slots is None
            or len(active_object.material_slots) == 0
        ):
            return {"CANCELLED"}
        active_material = active_object.active_material
        if not active_material.get("MLSetup"):
            self.report({"ERROR"}, "Multilayered setup not found within selected material.")
            return {"CANCELLED"}

        LayerGroup = get_layernode_by_socket(self, context)

        mlTemplateGroupInputNode = LayerGroup.node_tree.nodes["Group"].node_tree.nodes[
            "Group Input"
        ]
        mlTemplatePath = str(mlTemplateGroupInputNode["mlTemplate"])
        mlTemplatePathStripped = ((mlTemplatePath.split("\\"))[-1])[:-11]

        microblendtexnode = LayerGroup.node_tree.nodes["Image Texture"]
        bpy.context.scene.multilayer_microblend_pointer = microblendtexnode.image

        # JATO: for performance, first we try getting palette by direct name-match and ensure the mlTemplate path matches
        # If mlTemplate paths don't match try searching all palettes which can be slow
        match_palette = None
        palette_byname = bpy.data.palettes.get(mlTemplatePathStripped)
        if palette_byname:
            if palette_byname["MLTemplatePath"] == mlTemplateGroupInputNode["mlTemplate"]:
                match_palette = palette_byname
        else:
            for palette in bpy.data.palettes:
                if palette["MLTemplatePath"] == mlTemplateGroupInputNode["mlTemplate"]:
                    match_palette = palette
        if match_palette == None:
            self.report(
                {"WARNING"},
                "A Palette and Node Group with corresponding MLTEMPLATE path were not found.",
            )
            return {"CANCELLED"}

        ts.gpencil_paint.palette = match_palette
        bpy.context.scene.multilayer_palette_string = match_palette.name

        return {"FINISHED"}


class CP77MlSetupApplyColorOverride(Operator):
    bl_idname = "apply_color_override.mlsetup"
    bl_label = "Apply Color Override"
    bl_description = (
        "Apply the current color override to the selected Multilayered Layer Node Group"
    )

    def execute(self, context):
        ts = context.tool_settings
        if "MLTemplatePath" not in ts.gpencil_paint.palette:
            self.report({"ERROR"}, "MLTEMPLATE path not found on active palette.")
            return {"CANCELLED"}
        palette = ts.gpencil_paint.palette
        if ts.gpencil_paint.palette:
            colR, colG, colB = palette.colors.active.color
            active_color = (colR, colG, colB, 1)

        LayerGroup = get_layernode_by_socket(self, context)

        LayerGroup.inputs["ColorScale"].default_value = active_color

        return {"FINISHED"}


class CP77MlSetupApplyNormalStrOverride(Operator):
    bl_idname = "apply_normalstr_override.mlsetup"
    bl_label = "Apply NormalStrength Override"
    bl_description = (
        "Apply the NormalStrength override to the selected Multilayered Layer Node Group"
    )

    def execute(self, context):
        LayerGroup = get_layernode_by_socket(self, context)

        LayerGroup.inputs["NormalStrength"].default_value = float(
            bpy.context.scene.multilayer_normalstr_enum
        )

        return {"FINISHED"}


class CP77MlSetupApplyMetalLevelsInOverride(Operator):
    bl_idname = "apply_metalin_override.mlsetup"
    bl_label = "Apply MetalLevelsIn Override"
    bl_description = (
        "Apply the MetalLevelsIn override to the selected Multilayered Layer Node Group"
    )

    def execute(self, context):
        LayerGroup = get_layernode_by_socket(self, context)

        LayerGroup.inputs["MetalLevelsIn"].default_value = ast.literal_eval(
            bpy.context.scene.multilayer_metalin_enum
        )

        return {"FINISHED"}


class CP77MlSetupApplyMetalLevelsOutOverride(Operator):
    bl_idname = "apply_metalout_override.mlsetup"
    bl_label = "Apply MetalLevelsOut Override"
    bl_description = (
        "Apply the MetalLevelsOut override to the selected Multilayered Layer Node Group"
    )

    def execute(self, context):
        LayerGroup = get_layernode_by_socket(self, context)

        LayerGroup.inputs["MetalLevelsOut"].default_value = ast.literal_eval(
            bpy.context.scene.multilayer_metalout_enum
        )

        return {"FINISHED"}


class CP77MlSetupApplyRoughLevelsInOverride(Operator):
    bl_idname = "apply_roughin_override.mlsetup"
    bl_label = "Apply RoughLevelsIn Override"
    bl_description = (
        "Apply the RoughLevelsIn override to the selected Multilayered Layer Node Group"
    )

    def execute(self, context):
        LayerGroup = get_layernode_by_socket(self, context)

        LayerGroup.inputs["RoughLevelsIn"].default_value = ast.literal_eval(
            bpy.context.scene.multilayer_roughin_enum
        )

        return {"FINISHED"}


class CP77MlSetupApplyRoughLevelsOutOverride(Operator):
    bl_idname = "apply_roughout_override.mlsetup"
    bl_label = "Apply RoughLevelsOut Override"
    bl_description = (
        "Apply the RoughLevelsOut override to the selected Multilayered Layer Node Group"
    )

    def execute(self, context):
        LayerGroup = get_layernode_by_socket(self, context)

        LayerGroup.inputs["RoughLevelsOut"].default_value = ast.literal_eval(
            bpy.context.scene.multilayer_roughout_enum
        )

        return {"FINISHED"}


class CP77MlSetupApplyMLTemplate(Operator):
    bl_idname = "set_layer_mltemplate.mlsetup"
    bl_label = "Apply Selected MLTemplate"
    bl_description = (
        "Apply the selected MLTemplate within the selected Multilayered Layer Node Group"
    )

    def execute(self, context):
        ts = context.tool_settings
        if not ts.gpencil_paint.palette:
            # self.report({'WARNING'}, 'No active palette to match with MLTEMPLATE.')
            return {"CANCELLED"}
        if "MLTemplatePath" not in ts.gpencil_paint.palette:
            # self.report({'WARNING'}, 'MLTEMPLATE path not found on active palette.')
            return {"CANCELLED"}
        palette_name = ts.gpencil_paint.palette.name

        LayerGroup = get_layernode_by_socket(self, context)
        if LayerGroup == None:
            return

        # JATO: for performance, first we try getting node group by direct name-match and ensure the mlTemplate path matches
        # If mlTemplate paths don't match try searching all node-groups which can be slow
        ngmatch = None
        nodeGroup = bpy.data.node_groups.get(palette_name)
        if nodeGroup["mlTemplate"] == ts.gpencil_paint.palette["MLTemplatePath"]:
            ngmatch = nodeGroup
        else:
            for ng in bpy.data.node_groups:
                if "mlTemplate" in ng:
                    if ng["mlTemplate"] == ts.gpencil_paint.palette["MLTemplatePath"]:
                        ngmatch = ng
        if ngmatch == None:
            self.report(
                {"WARNING"},
                "A Palette and Node Group with corresponding MLTEMPLATE path were not found.",
            )
            return {"CANCELLED"}

        LayerGroup.node_tree.nodes["Group"].node_tree = ngmatch

        return {"FINISHED"}


class CP77MlSetupApplyMicroblend(Operator):
    bl_idname = "apply_microblend.mlsetup"
    bl_label = "Apply Microblend"
    bl_description = "Apply the Microblend to the selected Multilayered Layer Node Group"

    def execute(self, context):
        LayerGroup = get_layernode_by_socket(self, context)

        microblendtexnode = LayerGroup.node_tree.nodes["Image Texture"]
        microblendtexnode.image = bpy.context.scene.multilayer_microblend_pointer

        return {"FINISHED"}


class CP77MlSetupEnterTexturePaint(Operator):
    bl_idname = "enter_texture_paint.mlsetup"
    bl_label = "Paint Mask"

    def execute(self, context):
        LayerGroup = get_layernode_by_socket(self, context)
        if LayerGroup == None:
            return

        active_object = bpy.context.active_object
        active_material = active_object.active_material
        nodes = active_material.node_tree.nodes
        MaskNode = None

        socket_name = "Mask"
        socket = LayerGroup.inputs.get(socket_name)
        if not socket.is_linked:
            self.report({"ERROR"}, "No Image Texture Node linked to Selected Layer")
            return {"CANCELLED"}
        maskNodeLink = socket.links[0]
        linkedMaskNodeName = maskNodeLink.from_node.name
        MaskNode = nodes[linkedMaskNodeName]
        # print(layer_index, " | ", MaskNode.name)

        nodes.active = MaskNode

        bpy.ops.object.mode_set(mode="TEXTURE_PAINT")

        return {"FINISHED"}


class CP77MlSetupExportMasks(Operator, ExportHelper):
    bl_idname = "export_mlmasks.mlsetup"
    bl_label = "Export Masks"
    bl_description = "Export mask images from selected material and create a masklist file which can be imported in WolvenKit"

    filename_ext = ""

    export_format: EnumProperty(
        name="File Format",
        description="Choose the format for exported images",
        items=[
            ("PNG", "PNG", "Save as Portable Network Graphics"),
            ("JPEG", "JPEG", "Save as Joint Photographic Experts Group"),
            ("TARGA", "Targa", "Save as Targa graphic"),
            ("TIFF", "TIFF", "Save as Tagged Image File Format"),
        ],
        default="PNG",
    )

    directory: StringProperty(name="Target Folder", subtype="DIR_PATH")

    def invoke(self, context, event):
        active_material = bpy.context.active_object.active_material
        projpath = str(active_material["ProjPath"])
        maskpath = str(active_material["MultilayerMask"])
        maskpath_split = (maskpath.split(".")[0]) + "_layers"

        default_path = projpath + maskpath_split
        if not os.path.exists(default_path):
            os.makedirs(default_path)

        self.directory = bpy.path.abspath(default_path)

        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        active_object = bpy.context.active_object
        active_material = active_object.active_material
        nodes = active_material.node_tree.nodes
        # print("Exporting Mask Images from " + active_material.name + " on " + active_object.name)

        projpath = str(active_material["ProjPath"])
        maskpath = str(active_material["MultilayerMask"])
        maskpath_split = (maskpath.split(".")[0]) + ".masklist"
        mask_name = maskpath.split("\\")[-1]
        mask_folder = (mask_name.split(".")[0]) + "_layers/"
        file_path = projpath + maskpath_split
        mask_list = []

        mlBSDFGroup = nodes.get("Multilayered 1.8.0")
        if not mlBSDFGroup:
            self.report({"ERROR"}, "Multilayered shader node not found within selected material.")
            return {"CANCELLED"}

        target_dir = bpy.path.abspath(self.directory)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        ext_map = {"PNG": "png", "JPEG": "jpg", "TARGA": "tga", "TIFF": "tif"}
        selected_ext = ext_map.get(self.export_format, "png")

        numLayers = 20
        layerBSDF = 1
        while layerBSDF <= numLayers:
            socket_name = "Layer " + str(layerBSDF)
            socket = mlBSDFGroup.inputs.get(socket_name)
            # JATO: if there's no connected node group skip to next layer. TODO warn user this breaks mlmask/mlsetup relationship? or maybe write dummy mask?
            if not socket.is_linked:
                layerBSDF += 1
                continue

            layerGroupLink = socket.links[0]
            linkedLayerGroupName = layerGroupLink.from_node.name
            LayerGroup = nodes[linkedLayerGroupName]
            # print("# ", socket.name, " linked to Node Group: ", LayerGroup.name)

            MaskNode = None
            socket_name = "Mask"
            socket = LayerGroup.inputs.get(socket_name)
            # JATO: if there's no connected mask node skip to next layer. TODO warn user this breaks mlmask/mlsetup relationship? or maybe write dummy mask?
            if not socket.is_linked:
                layerBSDF += 1
                continue
            maskNodeLink = socket.links[0]
            linkedMaskNodeName = maskNodeLink.from_node.name
            MaskNode = nodes[linkedMaskNodeName]

            if MaskNode and MaskNode.type == "TEX_IMAGE" and MaskNode.image:
                img = MaskNode.image
                # JATO: LLM thinks this is a good idea... who am i to judge?
                safe_name = "".join(
                    [c for c in img.name if c.isalnum() or c in (" ", ".", "_")]
                ).strip()
                filepath = os.path.join(target_dir, f"{safe_name}.{selected_ext}")

                mask_list.append(f"{mask_folder}{safe_name}.{selected_ext}")

                try:
                    original_format = img.file_format
                    img.file_format = self.export_format
                    img.save_render(filepath)
                    img.file_format = original_format

                    # JATO: swap internal image to exported path. any reason not to?
                    img.filepath = filepath
                    # img.reload()
                except Exception as e:
                    self.report({"ERROR"}, f"Failed {img.name}: {str(e)}")

            layerBSDF += 1

        # JATO: Create masklist file. is there a scenario where user doesn't want to do this?
        with open(file_path, "w") as f:
            f.writelines(f"{item}\n" for item in mask_list)
        print(f"Masklist file saved to: {file_path}")

        success_message = (
            "Exported MLMASK from " + active_material.name + " on " + active_object.name
        )
        self.report({"INFO"}, success_message)

        return {"FINISHED"}


class CP77MlSetupCreateMultilayerObject(Operator):
    bl_idname = "create_multilayer_object.mlsetup"
    bl_label = "Create Multilayer Object"

    def execute(self, context):

        script_directory = os.path.dirname(os.path.abspath(__file__))
        relative_filepath = os.path.join("..", "resources", "all_multilayered_resources.glb")
        filepath = os.path.normpath(os.path.join(script_directory, relative_filepath))

        CP77GLBimport(with_materials=True, remap_depot=True, scripting=True, filepath=filepath)
        # (with_materials=True, remap_depot=True, exclude_unused_mats=True, image_format='png', filepath='',
        # hide_armatures=True, import_garmentsupport=False, files=[], directory='', appearances=[], scripting=False,
        # import_tracks=False, generate_overrides=False)

        active_object = bpy.context.active_object
        active_material = active_object.active_material
        nodes = active_material.node_tree.nodes
        links = active_material.node_tree.links

        mlBSDFGroup = nodes.get("Multilayered 1.8.0")
        if not mlBSDFGroup:
            self.report({"ERROR"}, "Multilayered shader node not found within selected material.")
            return {"CANCELLED"}

        numLayers = 20
        layerBSDF = 1
        while layerBSDF <= numLayers:
            if layerBSDF == 1:
                layerBSDF += 1
                continue
            socket_name = "Layer " + str(layerBSDF)
            socket = mlBSDFGroup.inputs.get(socket_name)
            if not socket.is_linked:
                layerBSDF += 1
                continue

            layerGroupLink = socket.links[0]
            linkedLayerGroupName = layerGroupLink.from_node.name
            LayerGroup = nodes[linkedLayerGroupName]
            # print("# ", socket.name, " linked to Node Group: ", LayerGroup.name)

            MaskNode = None
            socket_name = "Mask"
            socket = LayerGroup.inputs.get(socket_name)

            image_name = "ml_default_masksset_" + str(layerBSDF)
            dimensions = 1024
            new_img = bpy.data.images.new(
                name=image_name, width=dimensions, height=dimensions, alpha=False
            )
            new_img.source = "GENERATED"
            new_img.generated_type = "BLANK"
            new_img.colorspace_settings.name = "Non-Color"

            img_node = nodes.new(type="ShaderNodeTexImage")
            img_node.location = (-1250, 800 - (400 * layerBSDF))
            img_node.width = 300
            img_node.image = new_img

            links.new(img_node.outputs[0], LayerGroup.inputs["Mask"])

            layerBSDF += 1

        return {"FINISHED"}


operators, other_classes = get_classes(sys.modules[__name__])


def register_materialtools():
    for cls in operators:
        if not hasattr(bpy.types, cls.__name__):
            bpy.utils.register_class(cls)
    for cls in other_classes:
        if not hasattr(bpy.types, cls.__name__):
            bpy.utils.register_class(cls)
    # CP77_PT_MaterialTools.append(check_palette_change)
    CP77_PT_MaterialTools.append(check_palette_col_change)
    CP77_PT_MaterialTools.append(active_object_listener)


def unregister_materialtools():
    for cls in reversed(other_classes):
        bpy.utils.unregister_class(cls)
    for cls in reversed(operators):
        bpy.utils.unregister_class(cls)
