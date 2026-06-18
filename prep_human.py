"""
Prep: CC0 Quaternius human (assets/human.glb) -> arms-down static mesh,
exported as assets/human_posed.glb. Renders a preview too.

The source glTF has a 69x node scale, so we pose in the armature's own space, then
bake: keep-transform unparent -> apply armature deform -> apply scale -> recenter.

Run from this folder:  blender -b -P prep_human.py -- --arm 78
  --arm <deg>   how far to swing the upper arms down from the source pose (default 78)
"""
import bpy, math, mathutils, sys, os

# resolve paths relative to this script so the repo is portable
ABS = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ARM = float(argv[argv.index("--arm") + 1]) if "--arm" in argv else 78.0

bpy.ops.wm.read_factory_settings(use_empty=True)
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=ABS + "/assets/human.glb")
new = [o for o in bpy.data.objects if o not in before]
arm = next(o for o in new if o.type == 'ARMATURE')

# rest pose (drop stride animation)
arm.animation_data_clear()
for pb in arm.pose.bones:
    pb.matrix_basis.identity()
bpy.context.view_layer.update()

# swing the upper arms down — pivot & axis expressed in the armature's OBJECT space
axis_obj = (arm.matrix_world.to_3x3().inverted() @ mathutils.Vector((1, 0, 0))).normalized()
for name, sign in (("LeftArm", -1), ("RightArm", 1)):
    pb = arm.pose.bones[name]
    piv = pb.bone.head_local
    R = mathutils.Matrix.Rotation(math.radians(sign * ARM), 4, axis_obj)
    T = mathutils.Matrix.Translation(piv)
    pb.matrix = T @ R @ T.inverted() @ pb.matrix
    bpy.context.view_layer.update()

# bake the pose into the mesh(es)
meshes = [o for o in new if o.type == 'MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')      # keep world transform
for o in meshes:
    bpy.context.view_layer.objects.active = o
    for m in [m for m in o.modifiers if m.type == 'ARMATURE']:
        bpy.ops.object.modifier_apply(modifier=m.name)        # bake pose
for o in [x for x in new if x.type != 'MESH']:
    bpy.data.objects.remove(o, do_unlink=True)                # drop rig/empties

# join, bake the 69x scale, recenter at origin with feet on z=0
bpy.ops.object.select_all(action='DESELECT')
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1:
    bpy.ops.object.join()
body = bpy.context.view_layer.objects.active
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
body.location = (0, 0, 0)
bpy.ops.object.transform_apply(location=True)

dims = [round(d, 3) for d in body.dimensions]
print("POSED_DIMS_XYZ:", dims)
bpy.ops.export_scene.gltf(filepath=ABS + "/assets/human_posed.glb",
                          use_selection=True, export_format='GLB')
print("EXPORTED human_posed.glb")

# ---- preview render (camera framed from the final bounds) ----
H = max(dims)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.samples = 16
sc.render.resolution_x = 480; sc.render.resolution_y = 640
sc.render.filepath = ABS + "/assets/human_preview.png"
w = bpy.data.worlds.new("W"); sc.world = w
w.node_tree.nodes["Background"].inputs[1].default_value = 0.7
bpy.ops.object.camera_add(location=(H*0.9, -H*1.6, H*0.2))
cam = bpy.context.object
d = mathutils.Vector((0, 0, 0)) - cam.location
cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
cam.data.lens = 45; sc.camera = cam
bpy.ops.object.light_add(type='SUN', location=(2, -3, 4))
bpy.context.object.data.energy = 4
bpy.ops.render.render(write_still=True)
print("PREVIEW done")
