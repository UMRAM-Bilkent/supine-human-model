"""
Build the smoothed, supine human .blend from assets/human_posed.glb.

Pipeline:  import posed glb -> weld split verts -> recalc normals ->
shade smooth + Subdivision Surface (lvl 2) -> scale to 1.75 m ->
lay supine (on its back, head +Y, facing up +Z), drop onto z=0 ->
add ground + lights + camera -> render preview -> save human_supine.blend

Run from this folder:
  blender -b -P build_blend.py
  blender -b -P build_blend.py -- --height 1.8 --subdiv 2
"""
import bpy, math, mathutils, sys, os

ABS    = os.path.dirname(os.path.abspath(__file__))
argv   = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
HEIGHT = float(argv[argv.index("--height") + 1]) if "--height" in argv else 1.75
SUBDIV = int(argv[argv.index("--subdiv") + 1]) if "--subdiv" in argv else 2

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system = 'METRIC'

# ---- import the posed mesh ------------------------------------------------
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=ABS + "/assets/human_posed.glb")
body = next(o for o in bpy.data.objects if o not in before and o.type == 'MESH')
bpy.context.view_layer.objects.active = body
body.select_set(True)
body.name = "Human_Supine"

# ---- clean: weld split verts + recompute normals -------------------------
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=1e-4)      # weld glTF split verts
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode='OBJECT')
print("VERTS_AFTER_WELD:", len(body.data.vertices))

# ---- smooth: shade smooth + subdivision surface --------------------------
bpy.ops.object.shade_smooth()
sub = body.modifiers.new("Subdivision", 'SUBSURF')
sub.levels = SUBDIV
sub.render_levels = SUBDIV

# ---- scale + orient by transforming the mesh DATA directly ---------------
# (operator-based transform_apply is context-flaky in -b; data.transform is
#  deterministic). Import is standing: head +Z, long axis Z (~5.54 units).
s = HEIGHT / max(body.dimensions)
body.data.transform(mathutils.Matrix.Scale(s, 4))
# lay supine: -90 deg about X tips head +Z -> +Y and the front face up (+Z)
body.data.transform(mathutils.Matrix.Rotation(math.radians(-90), 4, 'X'))
body.data.update()
# drop so the lowest point rests on z = 0
zmin = min(v.co.z for v in body.data.vertices)
body.data.transform(mathutils.Matrix.Translation((0, 0, -zmin)))
body.data.update()
print("SUPINE_DIMS_XYZ:", [round(d, 3) for d in body.dimensions])

# ---- simple set: ground, lights, world -----------------------------------
bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, 0))
floor = bpy.context.object; floor.name = "ground"
mfl = bpy.data.materials.new("ground"); mfl.use_nodes = True
mfl.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.12, 0.13, 0.15, 1)
mfl.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
floor.data.materials.append(mfl)

world = bpy.data.worlds.new("W"); bpy.context.scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[1].default_value = 0.4

bpy.ops.object.light_add(type='AREA', location=(1.2, -1.4, 2.4))
key = bpy.context.object; key.data.energy = 220; key.data.size = 2.0
key.rotation_euler = (math.radians(35), 0, math.radians(25))
bpy.ops.object.light_add(type='SUN', location=(-2, 2, 3))
bpy.context.object.data.energy = 1.5

# ---- camera: 3/4 elevated view that clearly reads as 'lying down' --------
bpy.ops.object.camera_add(location=(1.7, -2.6, 1.7))
cam = bpy.context.object
target = mathutils.Vector((0, 0, 0.2))
cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
cam.data.lens = 40
bpy.context.scene.camera = cam

# ---- render preview -------------------------------------------------------
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.samples = 64
sc.render.resolution_x = 1280
sc.render.resolution_y = 720
sc.render.filepath = ABS + "/assets/human_supine_preview.png"
bpy.ops.render.render(write_still=True)
print("PREVIEW done")

# ---- save the .blend ------------------------------------------------------
bpy.ops.wm.save_as_mainfile(filepath=ABS + "/human_supine.blend")
print("SAVED human_supine.blend")
