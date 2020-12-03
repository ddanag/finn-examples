# Copyright (c) 2020, Xilinx
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of FINN nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
from finn.core.modelwrapper import ModelWrapper
from finn.builder.build_dataflow_config import DataflowBuildConfig
from finn.transformation.streamline import Streamline
from finn.transformation.double_to_single_float import DoubleToSingleFloat
import finn.transformation.streamline.absorb as absorb
import finn.transformation.streamline.reorder as reorder
from finn.transformation.infer_data_layouts import InferDataLayouts
from finn.transformation.streamline.collapse_repeated import CollapseRepeatedMul
from finn.transformation.streamline.remove import RemoveIdentityOps
from finn.transformation.streamline.round_thresholds import RoundAndClipThresholds
from finn.transformation.lower_convs_to_matmul import LowerConvsToMatMul
from finn.transformation.general import (
    GiveReadableTensorNames,
    GiveUniqueNodeNames,
)
import finn.transformation.fpgadataflow.convert_to_hls_layers as to_hls
from finn.transformation.infer_shapes import InferShapes
from finn.transformation.change_datalayout import ChangeDataLayoutQuantAvgPool2d
from finn.transformation.infer_datatypes import InferDataTypes


def step_mobilenet_streamline(model: ModelWrapper, cfg: DataflowBuildConfig):
    model = model.transform(Streamline())
    additional_streamline_transformations = [
        DoubleToSingleFloat(),
        reorder.MoveMulPastDWConv(),
        absorb.AbsorbMulIntoMultiThreshold(),
        ChangeDataLayoutQuantAvgPool2d(),
        InferDataLayouts(),
        reorder.MoveTransposePastScalarMul(),
        absorb.AbsorbTransposeIntoFlatten(),
        reorder.MoveFlattenPastAffine(),
        reorder.MoveFlattenPastTopK(),
        reorder.MoveScalarMulPastMatMul(),
        CollapseRepeatedMul(),
        RemoveIdentityOps(),
        RoundAndClipThresholds(),
    ]
    for trn in additional_streamline_transformations:
        model = model.transform(trn)
        model = model.transform(GiveUniqueNodeNames())
        model = model.transform(GiveReadableTensorNames())
        model = model.transform(InferDataTypes())
    return model


def step_mobilenet_lower_convs(model: ModelWrapper, cfg: DataflowBuildConfig):
    model = model.transform(LowerConvsToMatMul())
    model = model.transform(absorb.AbsorbTransposeIntoMultiThreshold())
    model = model.transform(GiveUniqueNodeNames())
    model = model.transform(GiveReadableTensorNames())
    model = model.transform(InferDataTypes())
    model = model.transform(RoundAndClipThresholds())
    return model


def step_mobilenet_convert_to_hls_layers(model: ModelWrapper, cfg: DataflowBuildConfig):
    mem_mode = cfg.default_mem_mode.value
    model = model.transform(to_hls.InferPool_Batch())
    model = model.transform(to_hls.InferConvInpGen())
    model = model.transform(to_hls.InferVVAU())
    model = model.transform(to_hls.InferQuantizedStreamingFCLayer(mem_mode))
    model = model.transform(to_hls.InferChannelwiseLinearLayer())
    model = model.transform(to_hls.InferLabelSelectLayer())
    model = model.transform(InferShapes())
    model = model.transform(GiveUniqueNodeNames())
    model = model.transform(GiveReadableTensorNames())
    return model
