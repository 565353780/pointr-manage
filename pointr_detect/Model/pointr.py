#!/usr/bin/env python
# -*- coding: utf-8 -*-

import torch
from torch import nn

from pointnet2_ops import pointnet2_utils

from pointr_detect.Model.fold import Fold
from pointr_detect.Model.pc_transformer import PCTransformer

from pointr_detect.Lib.chamfer_dist import ChamferDistanceL1


def fps(pc, num):
    fps_idx = pointnet2_utils.furthest_point_sample(pc, num)
    sub_pc = pointnet2_utils.gather_operation(
        pc.transpose(1, 2).contiguous(), fps_idx).transpose(1, 2).contiguous()
    return sub_pc


class PoinTr(nn.Module):

    def __init__(self):
        super().__init__()
        self.trans_dim = 384
        self.knn_layer = 1
        self.num_pred = 6144
        self.num_query = 96

        self.fold_step = int(pow(self.num_pred // self.num_query, 0.5) + 0.5)
        self.base_model = PCTransformer(in_chans=3,
                                        embed_dim=self.trans_dim,
                                        depth=[6, 8],
                                        drop_rate=0.,
                                        num_query=self.num_query,
                                        knn_layer=self.knn_layer)

        self.foldingnet = Fold(self.trans_dim,
                               step=self.fold_step,
                               hidden_dim=256)  # rebuild a cluster point

        self.increase_dim = nn.Sequential(nn.Conv1d(self.trans_dim, 1024, 1),
                                          nn.BatchNorm1d(1024),
                                          nn.LeakyReLU(negative_slope=0.2),
                                          nn.Conv1d(1024, 1024, 1))
        self.reduce_map = nn.Linear(self.trans_dim + 1027, self.trans_dim)
        self.build_loss_func()

    def build_loss_func(self):
        self.loss_func = ChamferDistanceL1()

    def get_loss(self, ret, gt):
        loss_coarse = self.loss_func(ret[0], gt)
        loss_fine = self.loss_func(ret[1], gt)
        return loss_coarse, loss_fine

    def forward(self, xyz):
        q, coarse_point_cloud = self.base_model(xyz)  # B M C and B M 3

        B, M, C = q.shape

        global_feature = self.increase_dim(q.transpose(1, 2)).transpose(
            1, 2)  # B M 1024
        global_feature = torch.max(global_feature, dim=1)[0]  # B 1024

        rebuild_feature = torch.cat([
            global_feature.unsqueeze(-2).expand(-1, M, -1), q,
            coarse_point_cloud
        ],
                                    dim=-1)  # B M 1027 + C

        rebuild_feature = self.reduce_map(rebuild_feature.reshape(B * M,
                                                                  -1))  # BM C
        # # NOTE: try to rebuild pc
        # coarse_point_cloud = self.refine_coarse(rebuild_feature).reshape(B, M, 3)

        # NOTE: foldingNet
        relative_xyz = self.foldingnet(rebuild_feature).reshape(B, M, 3,
                                                                -1)  # B M 3 S
        rebuild_points = (relative_xyz +
                          coarse_point_cloud.unsqueeze(-1)).transpose(
                              2, 3).reshape(B, -1, 3)  # B N 3

        # NOTE: fc
        # relative_xyz = self.refine(rebuild_feature)  # BM 3S
        # rebuild_points = (relative_xyz.reshape(B,M,3,-1) + coarse_point_cloud.unsqueeze(-1)).transpose(2,3).reshape(B, -1, 3)

        # cat the input
        inp_sparse = fps(xyz, self.num_query)
        coarse_point_cloud = torch.cat([coarse_point_cloud, inp_sparse],
                                       dim=1).contiguous()
        rebuild_points = torch.cat([rebuild_points, xyz], dim=1).contiguous()

        ret = (coarse_point_cloud, rebuild_points)
        return ret