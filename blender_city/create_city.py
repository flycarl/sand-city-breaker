"""Generate a stylized waterfront city in Blender.

The script is intentionally self-contained: run it with Blender's Python mode to
produce an editable .blend, a rendered preview, and a portable GLB export.
"""

import bpy
import math
import os
import random
from mathutils import Vector


ROOT = os.path.dirname(os.path.abspath(__file__))
OUTPUT_BLEND = os.path.join(ROOT, "waterfront_city.blend")
OUTPUT_RENDER = os.path.join(ROOT, "waterfront_city_preview.png")
OUTPUT_GLB = os.path.join(ROOT, "waterfront_city.glb")
REFERENCE_IMAGE = os.path.join(ROOT, "reference.png")
random.seed(18)


# -----------------------------------------------------------------------------
# Scene reset and common helpers
# -----------------------------------------------------------------------------
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
for block in bpy.data.materials:
    bpy.data.materials.remove(block)


def material(name, color, metallic=0.0, roughness=0.5, emission=None, emission_strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    # Node display names are localized by the user's Blender language, so use
    # the stable node type instead of the visible English label.
    bsdf = next(node for node in mat.node_tree.nodes if node.bl_idname == "ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if emission:
        emission_key = "Emission Color" if "Emission Color" in bsdf.inputs else "Emission"
        bsdf.inputs[emission_key].default_value = (*emission, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    return mat


MAT = {
    "white": material("Warm White Concrete", (0.83, 0.86, 0.84), roughness=0.34),
    "white2": material("Clean White Cladding", (0.96, 0.97, 0.94), roughness=0.24),
    "concrete": material("Urban Concrete", (0.36, 0.42, 0.43), roughness=0.72),
    "dark": material("Dark Structural Metal", (0.035, 0.075, 0.09), metallic=0.58, roughness=0.23),
    "glass": material("Deep Blue Glass", (0.025, 0.24, 0.40), metallic=0.28, roughness=0.10),
    "glass2": material("Sky Glass", (0.12, 0.48, 0.63), metallic=0.18, roughness=0.11),
    "window": material("Window Lights", (0.08, 0.24, 0.33), metallic=0.10, roughness=0.16,
                       emission=(0.20, 0.52, 0.65), emission_strength=0.24),
    "yellow": material("Sun Yellow Panels", (1.0, 0.54, 0.055), metallic=0.04, roughness=0.32,
                       emission=(1.0, 0.22, 0.015), emission_strength=0.18),
    "orange": material("Orange Panels", (0.95, 0.18, 0.045), metallic=0.04, roughness=0.38),
    "green": material("Landscape Green", (0.15, 0.43, 0.17), roughness=0.84),
    "green2": material("Fresh Green", (0.38, 0.68, 0.17), roughness=0.80),
    "trunk": material("Tree Trunks", (0.24, 0.12, 0.045), roughness=0.88),
    "road": material("Promenade Asphalt", (0.11, 0.15, 0.15), roughness=0.74),
    "paving": material("Pale Plaza Paving", (0.58, 0.62, 0.58), roughness=0.68),
    "water": material("City Water", (0.018, 0.28, 0.42), metallic=0.52, roughness=0.075),
    "water_light": material("Water Light Lines", (0.14, 0.65, 0.78), metallic=0.25, roughness=0.12,
                            emission=(0.05, 0.35, 0.52), emission_strength=0.35),
    "sky": material("Bright Blue Sky", (0.04, 0.48, 0.82), roughness=0.90,
                    emission=(0.04, 0.42, 0.78), emission_strength=0.42),
    "cloud": material("Soft White Clouds", (0.86, 0.94, 0.96), roughness=0.95,
                      emission=(0.54, 0.62, 0.64), emission_strength=0.18),
}


def add_box(name, location, scale, mat, bevel=0.0, collection=None):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = (scale[0] / 2, scale[1] / 2, scale[2] / 2)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        obj.data.materials.append(mat)
    if bevel > 0:
        mod = obj.modifiers.new("Soft architectural edges", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    if collection:
        for old in list(obj.users_collection):
            old.objects.unlink(obj)
        collection.objects.link(obj)
    return obj


def add_cylinder(name, location, radius, depth, mat, vertices=12, rotation=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location,
                                       rotation=rotation or (0, 0, 0))
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    return obj


def append_box(vertices, faces, center, size):
    cx, cy, cz = center
    sx, sy, sz = size[0] / 2, size[1] / 2, size[2] / 2
    start = len(vertices)
    vertices.extend([
        (cx-sx, cy-sy, cz-sz), (cx+sx, cy-sy, cz-sz),
        (cx+sx, cy+sy, cz-sz), (cx-sx, cy+sy, cz-sz),
        (cx-sx, cy-sy, cz+sz), (cx+sx, cy-sy, cz+sz),
        (cx+sx, cy+sy, cz+sz), (cx-sx, cy+sy, cz+sz),
    ])
    faces.extend([
        (start, start+1, start+2, start+3), (start+4, start+7, start+6, start+5),
        (start, start+4, start+5, start+1), (start+1, start+5, start+6, start+2),
        (start+2, start+6, start+7, start+3), (start+4, start, start+3, start+7),
    ])


def window_grid(name, location, width, height, cols, rows, mat, axis="front", margin=0.12):
    """Create a whole facade grid as one mesh to keep the scene lightweight."""
    verts, faces = [], []
    win_w = width / cols * (1.0 - margin)
    win_h = height / rows * 0.52
    for row in range(rows):
        z = location[2] - height / 2 + (row + 0.55) * height / rows
        for col in range(cols):
            offset = -width / 2 + (col + 0.5) * width / cols
            if axis == "front":
                center = (location[0] + offset, location[1], z)
                size = (win_w, 0.10, win_h)
            else:
                center = (location[0], location[1] + offset, z)
                size = (0.10, win_w, win_h)
            append_box(verts, faces, center, size)
    mesh = bpy.data.meshes.new(name + " Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def add_tower(name, x, y, w, d, h, body_mat=None, window_mat=None, cap=True):
    body_mat = body_mat or MAT["white"]
    window_mat = window_mat or MAT["window"]
    body = add_box(name, (x, y, h/2 + 0.25), (w, d, h), body_mat, bevel=0.18)
    rows = max(4, int(h / 1.45))
    cols = max(3, int(w / 1.05))
    window_grid(name + " Front Windows", (x, y-d/2-0.055, h/2+0.25), w*0.84, h*0.84, cols, rows, window_mat)
    window_grid(name + " Side Windows", (x+w/2+0.055, y, h/2+0.25), d*0.74, h*0.82,
                max(2, int(d/1.2)), rows, window_mat, axis="side")
    if cap:
        add_box(name + " Roof Cap", (x, y, h+0.42), (w*0.82, d*0.78, 0.38), MAT["dark"], bevel=0.08)
        add_cylinder(name + " Antenna", (x, y, h+1.35), 0.07, 1.5, MAT["dark"], vertices=8)
    return body


def add_tree(name, x, y, scale=1.0):
    add_cylinder(name + " Trunk", (x, y, 0.62*scale), 0.12*scale, 1.25*scale, MAT["trunk"], vertices=7)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.72*scale, location=(x, y, 1.72*scale))
    crown = bpy.context.object
    crown.name = name + " Crown"
    crown.data.materials.append(MAT["green2"] if random.random() > 0.42 else MAT["green"])
    crown.scale.z = 1.18


def add_triangular_canopy(name, x, y, z, width, depth, height, mat):
    verts = [
        (x-width/2, y-depth/2, z), (x+width/2, y-depth/2, z),
        (x-width/2, y+depth/2, z), (x+width/2, y+depth/2, z),
        (x, y-depth/2, z+height), (x, y+depth/2, z+height),
    ]
    faces = [(0,1,4), (2,5,3), (0,4,5,2), (1,3,5,4), (0,2,3,1)]
    mesh = bpy.data.meshes.new(name + " Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


# -----------------------------------------------------------------------------
# Environment and waterfront
# -----------------------------------------------------------------------------
add_box("Sky Backdrop", (0, 36.5, 28), (116, 0.30, 72), MAT["sky"])
for cluster, (cx, cz, scale) in enumerate([
    (-29, 31, 1.4), (-13, 38, 1.0), (8, 32, 1.3), (28, 39, 1.15), (42, 28, 0.9)
]):
    for lobe, (ox, oz, size) in enumerate([(-2.1, 0, 1.7), (0, 0.7, 2.4), (2.4, -0.1, 1.6)]):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=size*scale,
                                             location=(cx+ox*scale, 36.0, cz+oz*scale))
        cloud = bpy.context.object
        cloud.name = f"Cloud {cluster+1} Lobe {lobe+1}"
        cloud.scale = (1.8, 0.22, 0.62)
        cloud.data.materials.append(MAT["cloud"])
        cloud.visible_shadow = False

add_box("Water Basin", (0, -18, -0.35), (92, 38, 0.55), MAT["water"], bevel=0.15)
add_box("City Ground", (0, 17.5, -0.45), (92, 35, 0.8), MAT["concrete"])
add_box("Waterfront Promenade", (0, 0.65, 0.02), (92, 4.0, 0.28), MAT["paving"], bevel=0.12)
add_box("Promenade Dark Edge", (0, -1.15, 0.25), (92, 0.48, 0.72), MAT["dark"], bevel=0.06)
add_box("City Boulevard", (0, 5.1, 0.06), (92, 4.4, 0.22), MAT["road"])

for x in range(-43, 44, 4):
    add_box(f"Road Dash {x}", (x, 5.1, 0.19), (2.15, 0.10, 0.03), MAT["white2"])
    add_cylinder(f"Railing Post {x}", (x, -0.82, 0.98), 0.055, 1.45, MAT["dark"], vertices=8)
add_box("Waterfront Railing", (0, -0.82, 1.40), (92, 0.08, 0.09), MAT["dark"])

# Landscape islands along the water.
for i, x in enumerate(range(-40, 41, 4)):
    if i % 3 != 1:
        add_tree(f"Promenade Tree {i}", x + random.uniform(-0.5, 0.5), 2.05, random.uniform(0.68, 1.0))
for i in range(18):
    x = random.uniform(-43, 43)
    y = random.uniform(7, 31)
    add_tree(f"Background Tree {i}", x, y, random.uniform(0.65, 1.15))

# Stylized reflection strips guarantee a readable waterfront reflection in Eevee.
reflection_colors = [MAT["water_light"], MAT["yellow"], MAT["orange"], MAT["glass2"]]
for i in range(110):
    x = random.uniform(-39, 39)
    y = random.uniform(-17, -2.2)
    length = random.uniform(0.8, 6.5) * (1.0 - abs(x)/55)
    width = random.uniform(0.025, 0.15)
    add_box(f"Water Reflection {i:03d}", (x, y, 0.015+random.uniform(0,0.025)),
            (width, length, 0.018), random.choice(reflection_colors))


# -----------------------------------------------------------------------------
# Left landmark cluster: tall, blue, vertical and asymmetrical
# -----------------------------------------------------------------------------
for i, (dx, dy, w, d, h) in enumerate([
    (-37.0, 13.0, 4.2, 5.2, 39), (-33.5, 13.6, 2.5, 4.4, 31),
    (-39.6, 15.0, 2.2, 3.4, 27), (-35.2, 17.0, 3.0, 3.7, 35)
]):
    add_tower(f"Blue Landmark {i+1}", dx, dy, w, d, h, MAT["glass"], MAT["window"], cap=False)
    for fin in range(-2, 3):
        fx = dx + fin * (w / 5.5)
        add_box(f"Landmark Fin {i} {fin}", (fx, dy-d/2-0.15, h/2+0.3),
                (0.09, 0.22, h*0.96), MAT["white2"])

# Midground apartment skyline.
apartment_data = [
    (-26, 16, 4.6, 4.2, 20), (-20.5, 18, 4.2, 4.4, 23), (-15.5, 17, 4.0, 4.0, 21),
    (-10.8, 19, 4.5, 4.3, 25), (-5.0, 22, 4.8, 4.5, 19), (1.0, 24, 4.4, 4.6, 23),
    (7.0, 25, 5.0, 4.8, 18), (14.0, 27, 4.5, 4.3, 21), (21.0, 28, 4.6, 4.1, 18),
    (28.0, 27, 4.5, 4.4, 22), (35.0, 25, 4.7, 4.5, 20)
]
for i, data in enumerate(apartment_data):
    add_tower(f"Apartment Tower {i+1}", *data, MAT["white"], MAT["window"], cap=True)


# -----------------------------------------------------------------------------
# Central cultural/commercial building with colorful faceted canopy
# -----------------------------------------------------------------------------
add_box("Central Podium", (-3.0, 9.1, 1.45), (20.0, 8.0, 2.9), MAT["white2"], bevel=0.36)
add_box("Central Glass Hall", (-3.0, 5.65, 3.65), (18.0, 1.45, 3.0), MAT["glass2"], bevel=0.16)
window_grid("Central Hall Mullions", (-3.0, 4.89, 3.65), 17.2, 2.5, 19, 2, MAT["window"])

for i in range(12):
    x = -11.0 + i * 1.43
    mat = MAT["yellow"] if i % 3 else MAT["orange"]
    canopy = add_triangular_canopy(f"Color Canopy {i+1}", x, 4.55, 5.05 + (i%2)*0.18, 1.55, 1.8, 1.35, mat)
    canopy.rotation_euler[2] = (-0.16 if i % 2 else 0.14)

# Stacked white volumes above the center podium.
add_box("Central Upper Volume A", (-5.2, 9.9, 6.15), (9.0, 5.0, 3.1), MAT["white2"], bevel=0.25)
add_box("Central Upper Glass A", (-5.2, 7.35, 6.1), (8.1, 0.18, 2.1), MAT["glass"])
add_box("Central Upper Volume B", (-2.0, 10.4, 9.15), (8.0, 4.5, 2.2), MAT["white2"], bevel=0.20)
add_box("Central Upper Glass B", (-2.0, 8.1, 9.15), (7.2, 0.16, 1.4), MAT["glass2"])
add_box("Central Roof Garden", (-2.0, 10.2, 10.42), (6.5, 3.3, 0.28), MAT["green2"], bevel=0.12)

# Two rooftop frame towers with a recognizable grid crown.
for tower_x, tower_y, tower_h, tower_w in [(-1.6, 17.2, 20.5, 8.0), (19.5, 20.5, 18.5, 8.5)]:
    add_box("Frame Tower Core", (tower_x, tower_y, tower_h/2+0.4), (tower_w, 4.0, tower_h), MAT["white2"], bevel=0.18)
    window_grid("Frame Tower Front", (tower_x, tower_y-2.06, tower_h/2+0.4), tower_w*0.86, tower_h*0.88,
                8, 14, MAT["window"])
    for col in range(9):
        x = tower_x - tower_w/2 + col * tower_w/8
        add_box("Crown Vertical", (x, tower_y-2.12, tower_h-1.1), (0.10, 0.12, 4.0), MAT["white2"])


# -----------------------------------------------------------------------------
# Right-side layered mega complex: long white ribbons and glass bands
# -----------------------------------------------------------------------------
right_x = 25.5
levels = [
    (4.6, 25.0, 6.1, 3.2),
    (8.2, 22.0, 5.1, 3.0),
    (11.4, 19.0, 4.7, 2.8),
]
for i, (z, width, depth, height) in enumerate(levels):
    add_box(f"Right Ribbon {i+1}", (right_x+(i-1)*1.8, 9.8+i*0.4, z),
            (width, depth, height), MAT["white2"], bevel=0.30)
    add_box(f"Right Glass Band {i+1}", (right_x+(i-1)*1.8, 9.8+i*0.4-depth/2-0.10, z),
            (width*0.89, 0.22, height*0.58), MAT["glass2"], bevel=0.06)
    # Horizontal white sunshades create the characteristic layered facade.
    for rail in range(3):
        rz = z-height/2+0.5+rail*(height-1.0)/2
        add_box(f"Right Sunshade {i} {rail}", (right_x+(i-1)*1.8, 9.8+i*0.4-depth/2-0.30, rz),
                (width*0.94, 0.28, 0.16), MAT["white2"])

# Elevated connector bridges.
add_box("Sky Bridge West", (8.5, 9.1, 6.5), (13.0, 2.15, 2.05), MAT["white2"], bevel=0.20)
add_box("Sky Bridge West Glass", (8.5, 8.0, 6.5), (11.8, 0.14, 1.25), MAT["glass2"])
add_box("Sky Bridge East", (39.0, 11.4, 9.5), (11.5, 2.0, 1.85), MAT["white2"], bevel=0.18)
add_box("Sky Bridge East Glass", (39.0, 10.35, 9.5), (10.5, 0.12, 1.05), MAT["glass2"])

# Foreground retail colonnade and warm storefronts.
add_box("Retail Roof", (18, 3.35, 3.35), (48, 4.0, 0.42), MAT["dark"], bevel=0.10)
for i, x in enumerate(range(-5, 42, 3)):
    add_cylinder(f"Retail Column {i}", (x, 3.4, 1.72), 0.10, 3.15, MAT["white2"], vertices=10)
    if i < 15:
        add_box(f"Retail Storefront {i}", (x+1.25, 2.34, 1.6), (2.25, 0.16, 2.45),
                MAT["yellow"] if i % 4 == 0 else MAT["glass"])


# Small marina/civic pavilion on the far right.
add_box("Water Pavilion Deck", (39, -0.2, 0.50), (13, 5.2, 0.32), MAT["paving"], bevel=0.15)
add_box("Water Pavilion", (39, 0.5, 2.4), (10.5, 3.4, 3.4), MAT["glass2"], bevel=0.32)
add_box("Water Pavilion Roof", (39, 0.5, 4.4), (11.8, 4.0, 0.38), MAT["white2"], bevel=0.14)


# -----------------------------------------------------------------------------
# Lighting, camera, compositing and metadata
# -----------------------------------------------------------------------------
world = bpy.context.scene.world
world.use_nodes = True
world_bg = next(node for node in world.node_tree.nodes if node.bl_idname == "ShaderNodeBackground")
world_bg.inputs["Color"].default_value = (0.055, 0.30, 0.52, 1.0)
world_bg.inputs["Strength"].default_value = 0.52

bpy.ops.object.light_add(type="SUN", location=(-20, -25, 50))
sun = bpy.context.object
sun.name = "Late Morning Sun"
sun.rotation_euler = (math.radians(30), math.radians(-22), math.radians(-28))
sun.data.energy = 4.0
sun.data.angle = math.radians(7.0)

bpy.ops.object.light_add(type="AREA", location=(0, -20, 34))
fill = bpy.context.object
fill.name = "Waterfront Fill"
fill.data.energy = 1700
fill.data.shape = "RECTANGLE"
fill.data.size = 42
fill.data.size_y = 20

bpy.ops.object.camera_add(location=(58, -73, 30))
camera = bpy.context.object
camera.name = "Waterfront Hero Camera"
bpy.context.scene.camera = camera


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


look_at(camera, (1.0, 8.5, 9.0))
camera.data.lens = 56
camera.data.sensor_width = 36

# A second camera gives the user an orthographic planning view inside the blend.
bpy.ops.object.camera_add(location=(0, 7, 78))
plan_camera = bpy.context.object
plan_camera.name = "City Plan Camera"
plan_camera.data.type = "ORTHO"
plan_camera.data.ortho_scale = 96
look_at(plan_camera, (0, 7, 0))

# Keep the supplied photo as a non-rendering modeling reference.
if os.path.exists(REFERENCE_IMAGE):
    try:
        image = bpy.data.images.load(REFERENCE_IMAGE, check_existing=True)
        ref = bpy.data.objects.new("Source Photo Reference", None)
        ref.empty_display_type = "IMAGE"
        ref.data = image
        ref.empty_display_size = 18
        ref.location = (0, 34, 18)
        ref.rotation_euler = (math.radians(90), 0, 0)
        ref.hide_render = True
        bpy.context.collection.objects.link(ref)
    except Exception as exc:
        print("Reference image could not be embedded:", exc)

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.render.filepath = OUTPUT_RENDER
scene.render.image_settings.color_mode = "RGBA"
scene.render.resolution_percentage = 100
scene.render.use_file_extension = True
scene.view_settings.look = "AgX - Medium High Contrast"

# Mild ambient occlusion/contact shadows through Eevee ray tracing when available.
try:
    scene.world.color = (0.05, 0.19, 0.28)
except Exception:
    pass

# Metadata makes the model easier to hand off and reuse.
scene["asset_title"] = "Stylized Waterfront City"
scene["reference_style"] = "Bright contemporary Chinese waterfront city"
scene["model_scale"] = "1 Blender unit = 1 meter (approximate)"
scene["generated_with"] = "Blender Python"

# Organize reference and cameras in a dedicated collection after generation.
camera_collection = bpy.data.collections.new("Cameras and Reference")
scene.collection.children.link(camera_collection)
for obj in [camera, plan_camera]:
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    camera_collection.objects.link(obj)

# Save before and after render so the output is recoverable even if rendering fails.
bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_BLEND)
bpy.context.scene.camera = camera
bpy.ops.render.render(write_still=True)

try:
    bpy.ops.export_scene.gltf(
        filepath=OUTPUT_GLB,
        export_format="GLB",
        export_apply=True,
        export_cameras=False,
        export_lights=False,
    )
    print("GLB exported:", OUTPUT_GLB)
except Exception as exc:
    print("GLB export skipped:", exc)

bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_BLEND)
print("BLEND saved:", OUTPUT_BLEND)
print("Preview rendered:", OUTPUT_RENDER)
