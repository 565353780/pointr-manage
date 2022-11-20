#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import torch
import numpy as np
from tqdm import tqdm
from torch.utils.data import Dataset

from points_shape_detect.Data.io import IO
from points_shape_detect.Method.trans import \
    normalizePointArray, randomTransPointArray, getInverseTrans

import sys

sys.path.append("../auto-cad-recon")
sys.path.append("../mesh-manage/")
sys.path.append("../udf-generate/")
sys.path.append("../scannet-dataset-manage")
sys.path.append("../scan2cad-dataset-manage")
sys.path.append("../shapenet-dataset-manage")

from auto_cad_recon.Module.dataset_manager import DatasetManager


class CADDataset(Dataset):

    def __init__(self):
        self.cad_model_file_path_list = []

        self.loadShapeNet55()
        return

    def reset(self):
        self.cad_model_file_path_list = []
        return True

    def loadScan2CAD(self):
        scannet_dataset_folder_path = "/home/chli/chLi/ScanNet/scans/"
        scannet_object_dataset_folder_path = "/home/chli/chLi/ScanNet/objects/"
        scannet_bbox_dataset_folder_path = "/home/chli/chLi/ScanNet/bboxes/"
        scan2cad_dataset_folder_path = "/home/chli/chLi/Scan2CAD/scan2cad_dataset/"
        scan2cad_object_model_map_dataset_folder_path = "/home/chli/chLi/Scan2CAD/object_model_maps/"
        shapenet_dataset_folder_path = "/home/chli/chLi/ShapeNet/Core/ShapeNetCore.v2/"
        shapenet_udf_dataset_folder_path = "/home/chli/chLi/ShapeNet/udfs/"
        print_progress = True

        dataset_manager = DatasetManager(
            scannet_dataset_folder_path, scannet_object_dataset_folder_path,
            scannet_bbox_dataset_folder_path, scan2cad_dataset_folder_path,
            scan2cad_object_model_map_dataset_folder_path,
            shapenet_dataset_folder_path, shapenet_udf_dataset_folder_path)

        scene_name_list = dataset_manager.getScanNetSceneNameList()

        print("[INFO][CADDataset::loadScan2CAD]")
        print("\t start load scan2cad dataset...")
        for scene_name in tqdm(scene_name_list):
            object_file_name_list = dataset_manager.getScanNetObjectFileNameList(
                scene_name)
            for object_file_name in object_file_name_list:
                shapenet_model_dict = dataset_manager.getShapeNetModelDict(
                    scene_name, object_file_name)
                cad_model_file_path = shapenet_model_dict[
                    'shapenet_model_file_path']
                self.cad_model_file_path_list.append(cad_model_file_path)
        return True

    def loadShapeNet55(self):
        dataset_folder_path = '/home/chli/chLi/PoinTr/ShapeNet55/shapenet_pc/'
        file_name_list = os.listdir(dataset_folder_path)
        for file_name in file_name_list:
            self.cad_model_file_path_list.append(dataset_folder_path +
                                                 file_name)
        return True

    def __getitem__(self, idx):
        cad_model_file_path = self.cad_model_file_path_list[idx]

        data = {'inputs': {}, 'predictions': {}, 'losses': {}, 'logs': {}}

        point_array = IO.get(cad_model_file_path).astype(np.float32)
        point_array = normalizePointArray(point_array)

        point_array, translate, quat, scale = randomTransPointArray(
            point_array, True)
        translate_inv, quat_inv, scale_inv = getInverseTrans(
            translate, quat, scale)

        min_point = np.min(point_array, axis=0)
        max_point = np.max(point_array, axis=0)

        bbox = np.hstack((min_point, max_point))
        center = np.mean([min_point, max_point], axis=0)

        data['inputs']['point_array'] = torch.from_numpy(point_array).float()
        data['inputs']['bbox'] = torch.from_numpy(bbox).float()
        data['inputs']['center'] = torch.from_numpy(center).float()
        data['inputs']['quat_inv'] = torch.from_numpy(quat_inv).float()
        data['inputs']['scale_inv'] = torch.from_numpy(scale_inv).float()
        return data

    def __len__(self):
        return len(self.cad_model_file_path_list)
