#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import numpy as np
import open3d as o3d

from pointr_detect.Method.sample import seprate_point_cloud
from pointr_detect.Method.trans import normalizePointArray, moveToOrigin
from pointr_detect.Method.render import renderPointArrayWithUnitBBox

from pointr_detect.Module.detector import Detector


def demo():
    pointr_model_file_path = "/home/chli/chLi/PoinTr/pointr_training_from_scratch_c55_best.pth"
    model_file_path = "./output/20221119_18:46:28/model_best.pth"
    npy_file_path = "/home/chli/chLi/PoinTr/ShapeNet55/shapenet_pc/" + \
        "04090263-2eb7e88f5355630962a5697e98a94be.npy"

    #  detector = Detector(model_file_path)
    detector = Detector()
    detector.loadPoinTrModel(pointr_model_file_path)

    points = np.load(npy_file_path)
    points = normalizePointArray(points)
    partial, _ = seprate_point_cloud(points, 0.5)
    partial = moveToOrigin(partial)

    renderPointArrayWithUnitBBox(partial)

    data = detector.detectPointArray(partial)

    print(data['predictions'].keys())
    renderPointArrayWithUnitBBox(data['predictions']['dense_points'][0])
    return True


def demo_mesh():
    pointr_model_file_path = "/home/chli/chLi/PoinTr/pointr_training_from_scratch_c55_best.pth"
    model_file_path = "./output/20221119_18:46:28/model_best.pth"
    shapenet_model_file_path = "/home/chli/chLi/ShapeNet/Core/ShapeNetCore.v2/" + \
        "02691156/1a04e3eab45ca15dd86060f189eb133" + \
        "/models/model_normalized.obj"

    #  detector = Detector(model_file_path)
    detector = Detector()
    detector.loadPoinTrModel(pointr_model_file_path)

    assert os.path.exists(shapenet_model_file_path)
    mesh = o3d.io.read_triangle_mesh(shapenet_model_file_path)
    pcd = mesh.sample_points_uniformly(8192)
    points = np.array(pcd.points)
    points = normalizePointArray(points)

    partial, _ = seprate_point_cloud(points, 0.5)
    partial = moveToOrigin(partial)
    renderPointArrayWithUnitBBox(partial)

    data = detector.detectPointArray(partial)

    print(data['predictions'].keys())
    renderPointArrayWithUnitBBox(data['predictions']['dense_points'][0])
    return True
