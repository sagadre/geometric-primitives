import argparse
import json
import os
import random
import shutil
import uuid

import trimesh


def create_primitive_variations(args):
    variations = []

    for o in os.listdir(args.primitives):
        if 'obj' in o:
            for i in range(args.num_raw_meshes):

                x_scaling = random.random() * .1 + 0.05
                y_scaling = random.random() * .1 + 0.05
                mesh = trimesh.load(os.path.join(args.primitives, o))
                mesh.vertices[:, 0] *= x_scaling
                mesh.vertices[:, 1] *= y_scaling

                name = o.split('.')[0]
                obj_path = os.path.join(args.meshes, f'{name}_{i}.obj')
                mesh.export(obj_path)

                variations.append(obj_path)

    return variations


def create_link(mesh, name, x, y, z, filename, num_colors, r=0, p=0, yaw=0, mass=0.75):

    inertia = mesh.moment_inertia
    xx = inertia[0, 0]
    xy = inertia[0, 1]
    xz = inertia[0, 2]
    yy = inertia[1, 1]
    yz = inertia[1, 2]
    zz = inertia[2, 2]

    color_ref = random.randint(1, num_colors)

    template = f"""
    <link name="{name}">
    <inertial>
        <origin rpy="{r} {p} {yaw}" xyz="{x} {y} {z}"/>
        <mass value="{mass}"/>
        <inertia ixx="{xx}" ixy="{xy}" ixz="{xz}" iyy="{yy}" iyz="{yz}" izz="{zz}"/>
    </inertial>
    <visual>
        <origin rpy="{r} {p} {yaw}" xyz="{x} {y} {z}"/>
        <geometry>
        <mesh filename="{filename}" scale="1 1 1"/>
        </geometry>
        <material name="mat_{color_ref}"/>
    </visual>
    <collision>
        <origin rpy="{r} {p} {yaw}" xyz="{x} {y} {z}"/>
        <geometry>
        <mesh filename="{filename}" scale="1 1 1"/>
        </geometry>
    </collision>
    </link>
"""

    return template


def create_joint(joint_name, x, y, z, child_name, parent_name):
    template = f"""
    <joint name="{joint_name}" type="revolute" >
        <origin xyz="{x} {y} {z}" />
        <axis xyz="0 1 0" />
        <child link="{child_name}" />
        <parent link="{parent_name}" />
        <limit lower="-1.57079632679" upper="1.57079632679" effort="10" velocity="3"/>
    </joint>
"""

    return template


def create_materials(num_materials):
    urdf_materials = ''
    for i in range(num_materials):
        mat = [random.random() for _ in range(3)]

        urdf_materials += f"""
    <material name="mat_{i+1}">
        <color rgba="{mat[0]} {mat[1]} {mat[2]} 1"/>
    </material>
"""

    return urdf_materials


def create_urdf(num_links, mesh_paths, partnet_dir):

    body = f"""
<?xml version='1.0' encoding='utf-8'?>
<robot name="partnet_{uuid.uuid4().hex}">
    <link name="base"><inertial><mass value="1.0" /><inertia ixx="1.0" ixy="0.0" ixz="0.0" iyy="1.0" iyz="0.0" izz="1.0" /></inertial></link>
"""

    # num_colors = random.randint(1, num_links)
    body += create_materials(num_links)

    partnet_meshes_dir = os.path.join(partnet_dir, 'meshes')
    os.mkdir(partnet_meshes_dir)

    for i in range(num_links):
        mesh_path = random.choice(mesh_paths)
        dest = os.path.join(partnet_meshes_dir, os.path.basename(mesh_path))

        shutil.copyfile(mesh_path, dest)

        mesh = trimesh.load(mesh_path)
        body += create_link(mesh, f'link_{i}', 0, 0, 0,
                            mesh_path, num_links, r=0, p=0, yaw=0, mass=0.75)

        if i != num_links-1:
            # add joint
            body += create_joint(f'joint_{i}', 0,
                                 0, 1, f'link_{i}', f'link_{i+1}')

    offset = num_links / 2.
    body += f"""
    <joint name="joint_{num_links-1}" type="fixed">
        <origin rpy="1.570796326794897 0 -1.570796326794897" xyz="{offset} 0 0" />
        <child link="link_{num_links-1}" />
        <parent link="base" />
    </joint>
</robot>"""

    return body


def check_inputs(args):
    if not os.path.exists(args.primitives):
        raise ValueError(
            f'primitive dir path does not exist: {args.primitives}')

    if os.path.exists(args.multilink):
        shutil.rmtree(args.multilink)
        os.mkdir(args.multilink)

    if not os.path.exists(args.multilink):
        os.mkdir(args.multilink)

    if os.path.exists(args.meshes):
        shutil.rmtree(args.meshes)
        os.mkdir(args.meshes)

    if not os.path.exists(args.meshes):
        os.mkdir(args.meshes)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description='take geometric primitives and make snakes in the inertial partnet mobility style')

    parser.add_argument(
        '--primitives',
        required=False,
        type=str,
        default='./primitives',
        help='Specify dataset path that contains test and train folders')

    parser.add_argument(
        '--meshes',
        required=False,
        type=str,
        default='./meshes',
        help='TODO')

    parser.add_argument(
        '--multilink',
        required=False,
        type=str,
        default='./multilink',
        help='TODO')

    parser.add_argument(
        '--num-raw-meshes',
        required=False,
        type=int,
        default=10,
        help='TODO')

    parser.add_argument(
        '--num-urdfs',
        required=False,
        type=int,
        default=40,
        help='TODO')

    parser.add_argument(
        '--all-test',
        action='store_true',
        default=False)

    parser.add_argument(
        '--min-links',
        required=False,
        type=int,
        default=2,
        help='TODO')

    parser.add_argument(
        '--max-links',
        required=False,
        type=int,
        default=3,
        help='TODO')

    args = parser.parse_args()
    check_inputs(args)

    variations = create_primitive_variations(args)

    partnet_ids = []
    for i in range(args.num_urdfs):
        partnet_id = str(i)
        partnet_id = '0' * (6 - len(partnet_id)) + partnet_id
        partnet_ids.append(partnet_id)

    metadata = {'train': [], 'val': [], 'test': []}

    for partnet_id in partnet_ids:
        partnet_dir = os.path.join(args.multilink, partnet_id)
        os.mkdir(partnet_dir)

        num_links = random.randint(args.min_links, args.max_links)
        urdf = create_urdf(num_links, variations, partnet_dir)
        with open(os.path.join(partnet_dir, 'mobility_inertia.urdf'), 'w') as f:
            f.write(urdf)

        partnet_meta = {
            "user_id": "sy",
            "model_cat": "Multilink",
            "model_id": "3d1914946ded40bcb5c1c7d56b18e569",
            "version": "1",
            "anno_id": "1234",
            "time_in_sec": "1"}

        if args.all_test:
            metadata['test'].append(partnet_id)
        else:
            cutoff_val = int(args.num_urdfs * 0.8)
            if i > cutoff_val:
                metadata['val'].append(partnet_id)
            else:
                metadata['train'].append(partnet_id)

        with open(os.path.join(partnet_dir, 'meta.json'), 'w') as f:
            json.dump(partnet_meta, f, indent=4)

        with open(os.path.join(args.multilink, 'meta.json'), 'w') as f:
            json.dump(metadata, f, indent=4)
