# Copyright (c) 2018 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function

from six.moves import reduce

from .. import core
from ..layers import utils
from . import layers
from ..framework import Variable, OpProtoHolder
from ..param_attr import ParamAttr
from ..initializer import Normal, Constant

__all__ = [
    'Conv2D',
    'Pool2D',
    'FC',
]


class Conv2D(layers.PyLayer):
    def __init__(self,
                 num_channels,
                 num_filters,
                 filter_size,
                 stride=1,
                 padding=0,
                 dilation=1,
                 groups=None,
                 use_cudnn=True,
                 act=None,
                 param_attr=None,
                 bias_attr=None,
                 name=None,
                 dtype=core.VarDesc.VarType.FP32):
        assert param_attr is not False, "param_attr should not be False here."
        super(Conv2D, self).__init__(
            param_attr=param_attr, bias_attr=bias_attr, name=name, dtype=dtype)

        self._groups = groups
        self._stride = utils.convert_to_list(stride, 2, 'stride')
        self._padding = utils.convert_to_list(padding, 2, 'padding')
        self._dilation = utils.convert_to_list(dilation, 2, 'dilation')
        if not isinstance(use_cudnn, bool):
            raise ValueError("use_cudnn should be True or False")
        self._use_cudnn = use_cudnn
        self._num_channels = num_channels
        if (self._num_channels == self._groups and
                num_filters % self._num_channels == 0 and not self._use_cudnn):
            self._l_type = 'depthwise_conv2d'
        else:
            self._l_type = 'conv2d'

        if groups is None:
            num_filter_channels = num_channels
        else:
            if num_channels % groups != 0:
                raise ValueError("num_channels must be divisible by groups.")
            num_filter_channels = num_channels // groups
        filter_size = utils.convert_to_list(filter_size, 2, 'filter_size')
        filter_shape = [num_filters, int(num_filter_channels)] + filter_size

        def _get_default_param_initializer():
            filter_elem_num = filter_size[0] * filter_size[1] * num_channels
            std = (2.0 / filter_elem_num)**0.5
            return Normal(0.0, std, 0)

        self._filter_param = self._helper.create_parameter(
            attr=self._helper.param_attr,
            shape=filter_shape,
            dtype=self._dtype,
            default_initializer=_get_default_param_initializer())

        if self._use_cudnn:
            self._helper.create_variable(
                name="kCUDNNFwdAlgoCache",
                persistable=True,
                type=core.VarDesc.VarType.RAW)
            self._helper.create_variable(
                name="kCUDNNBwdDataAlgoCache",
                persistable=True,
                type=core.VarDesc.VarType.RAW)
            self._helper.create_variable(
                name="kCUDNNBwdFilterAlgoCache",
                persistable=True,
                type=core.VarDesc.VarType.RAW)

        self._pre_bias = self._helper.create_variable_for_type_inference(
            dtype=self._dtype)

    def forward(self, input):
        self._helper.append_op(
            type=self._l_type,
            inputs={
                'Input': input,
                'Filter': self._filter_param,
            },
            outputs={"Output": self._pre_bias},
            attrs={
                'strides': self._stride,
                'paddings': self._padding,
                'dilations': self._dilation,
                'groups': self._groups,
                'use_cudnn': self._use_cudnn,
                'use_mkldnn': False,
            })

        self._pre_act = self._helper.append_bias_op(
            self._pre_bias, dim_start=1, dim_end=2)

        out = self._helper.append_activation(self._pre_act)
        return out


class Pool2D(layers.PyLayer):
    def __init__(self,
                 pool_size=-1,
                 pool_type="max",
                 pool_stride=1,
                 pool_padding=0,
                 global_pooling=False,
                 use_cudnn=True,
                 ceil_mode=False,
                 exclusive=True,
                 name=None,
                 dtype=core.VarDesc.VarType.FP32):
        if pool_type not in ["max", "avg"]:
            raise ValueError(
                "Unknown pool_type: '%s'. It can only be 'max' or 'avg'.",
                str(pool_type))

        if global_pooling is False and pool_size == -1:
            raise ValueError(
                "When the global_pooling is False, pool_size must be passed "
                "and be a valid value. Received pool_size: " + str(pool_size))

        if not isinstance(use_cudnn, bool):
            raise ValueError("use_cudnn should be True or False")

        super(Pool2D, self).__init__(name=name, dtype=dtype)

        self._pool_type = pool_type
        self._pool_size = utils.convert_to_list(pool_size, 2, 'pool_size')
        self._pool_padding = utils.convert_to_list(pool_padding, 2,
                                                   'pool_padding')
        self._pool_stride = utils.convert_to_list(pool_stride, 2, 'pool_stride')
        self._global_pooling = global_pooling
        self._use_cudnn = use_cudnn
        self._ceil_mode = ceil_mode
        self._exclusive = exclusive
        self._l_type = 'pool2d'

        self._pool_out = self._helper.create_variable_for_type_inference(
            self._dtype)

    def forward(self, input):
        self._helper.append_op(
            type=self._l_type,
            inputs={"X": input},
            outputs={"Out": self._pool_out},
            attrs={
                "pooling_type": self._pool_type,
                "ksize": self._pool_size,
                "global_pooling": self._global_pooling,
                "strides": self._pool_stride,
                "paddings": self._pool_padding,
                "use_cudnn": self._use_cudnn,
                "ceil_mode": self._ceil_mode,
                "use_mkldnn": False,
                "exclusive": self._exclusive,
            })
        return self._pool_out


class FC(layers.PyLayer):
    def __init__(self,
                 size_in,
                 size_out,
                 num_flatten_dims=1,
                 param_attr=None,
                 dtype=core.VarDesc.VarType.FP32):
        super(FC, self).__init__(param_attr=param_attr, dtype=dtype)

        self._size_in = size_in
        self._size_out = size_out
        self._num_flatten_dims = num_flatten_dims
        self._dtype = dtype
        if self._size_in != -1:
            self._w = self._helper.create_parameter(
                attr=self._helper.param_attr,
                shape=[size_in, size_out],
                dtype=self._dtype,
                is_bias=False)
        self._tmp = self._helper.create_variable_for_type_inference(self._dtype)
        self._out = self._helper.create_variable_for_type_inference(self._dtype)

    def _build_once(self, input):
        if self._size_in != -1:
            return

        input_shape = input.shape
        param_shape = [
            reduce(lambda a, b: a * b, input_shape[self._num_flatten_dims:], 1)
        ] + [self._size_out]
        self._w = self._helper.create_parameter(
            attr=self._helper.param_attr,
            shape=param_shape,
            dtype=self._dtype,
            is_bias=False)

    def forward(self, input):
        self._helper.append_op(
            type="mul",
            inputs={"X": input,
                    "Y": self._w},
            outputs={"Out": self._tmp},
            attrs={
                "x_num_col_dims": self._num_flatten_dims,
                "y_num_col_dims": 1
            })

        self._helper.append_op(
            type="sum",
            inputs={"X": [self._tmp]},
            outputs={"Out": self._out},
            attrs={"use_mkldnn": False})
        return self._out