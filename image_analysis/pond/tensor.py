import random
import numpy as np
from math import log
from im2col.im2col import im2col_indices, col2im_indices
import time

try:
    from im2col.im2col_cython_float import im2col_cython_float, col2im_cython_float
    from im2col.im2col_cython_object import im2col_cython_object, col2im_cython_object
    use_cython = True
except ImportError as e:
    print(e)
    print('\nRun the following from the image_analysis/im2col directory to use cython:')
    print('python setup.py build_ext --inplace\n')
    use_cython = False


class NativeTensor:

    def __init__(self, values):
        self.values = values

    def from_values(values):
        return NativeTensor(values)

    @property
    def size(self):
        return self.values.size

    @property
    def shape(self):
        return self.values.shape

    def __getitem__(self, index):
        return NativeTensor(self.values[index])

    def __setitem__(self, idx, other):
        assert isinstance(other, NativeTensor)
        self.values[idx] = other.values

    def concatenate(self, other):
        assert isinstance(other, NativeTensor), type(other)
        return NativeTensor.from_values(np.concatenate([self.values, other.values]))

    def reveal(self):
        return self

    def unwrap(self):
        return self.values

    def __repr__(self):
        return "NativeTensor(%s)" % self.values

    def wrap_if_needed(y):
        if isinstance(y, int) or isinstance(y, float): return NativeTensor.from_values(np.array([y]))
        if isinstance(y, np.ndarray): return NativeTensor.from_values(y)
        return y

    def add(x, y):
        y = NativeTensor.wrap_if_needed(y)
        if isinstance(y, NativeTensor): return NativeTensor(x.values + y.values)
        if isinstance(y, PublicEncodedTensor): return PublicEncodedTensor.from_values(x.values).add(y)
        if isinstance(y, PrivateEncodedTensor): return PublicEncodedTensor.from_values(x.values).add(y)
        raise TypeError("%s does not support %s" % (type(x), type(y)))

    def __add__(x, y):
        return x.add(y)

    def __iadd__(self, y):
        if isinstance(y, NativeTensor): self.values = self.values + y.values
        elif isinstance(y, PublicEncodedTensor): self = PublicEncodedTensor.from_values(self.values).add(y)
        elif isinstance(y, PrivateEncodedTensor): self = PublicEncodedTensor.from_values(self.values).add(y)
        else: raise TypeError("does not support %s" % (type(y)))
        return self

    def add_at(self, indices, y):
        if isinstance(y, NativeTensor):
            np.add.at(self.values, indices, y.values)
        else:
            raise TypeError("%s does not support %s" % (type(self), type(y)))

    def sub(x, y):
        y = NativeTensor.wrap_if_needed(y)
        if isinstance(y, NativeTensor): return NativeTensor(x.values - y.values)
        if isinstance(y, PublicEncodedTensor): return PublicEncodedTensor.from_values(x.values).sub(y)
        if isinstance(y, PrivateEncodedTensor): return PublicEncodedTensor.from_values(x.values).sub(y)
        raise TypeError("%s does not support %s" % (type(x), type(y)))

    def __sub__(x, y):
        return x.sub(y)

    def mul(x, y):
        y = NativeTensor.wrap_if_needed(y)
        if isinstance(y, NativeTensor): return NativeTensor(x.values * y.values)
        if isinstance(y, PublicEncodedTensor): return PublicEncodedTensor.from_values(x.values).mul(y)
        if isinstance(y, PrivateEncodedTensor): return PublicEncodedTensor.from_values(x.values).mul(y)
        if isinstance(y, float): return NativeTensor(x.values * y)
        raise TypeError("%s does not support %s" % (type(x), type(y)))

    def __mul__(x, y):
        return x.mul(y)

    def dot(x, y):
        y = NativeTensor.wrap_if_needed(y)
        if isinstance(y, NativeTensor): return NativeTensor(x.values.dot(y.values))
        if isinstance(y, PublicEncodedTensor): return PublicEncodedTensor.from_values(x.values).dot(y)
        if isinstance(y, PrivateEncodedTensor): return PublicEncodedTensor.from_values(x.values).dot(y)
        raise TypeError("%s does not support %s" % (type(x), type(y)))

    def matmul(x, y):
        y = NativeTensor.wrap_if_needed(y)
        if isinstance(y, NativeTensor): return NativeTensor(np.matmul(x.values, y.values))
        if isinstance(y, PublicEncodedTensor): return PublicEncodedTensor.from_values(x.values).matmul(y)
        if isinstance(y, PrivateEncodedTensor): return PublicEncodedTensor.from_values(x.values).matmul(y)
        raise TypeError("%s does not support %s" % (type(x), type(y)))

    def div(x, y):
        y = NativeTensor.wrap_if_needed(y)
        if isinstance(y, NativeTensor): return NativeTensor(x.values / y.values)
        raise TypeError("%s does not support %s" % (type(x), type(y)))

    def __div__(x, y):
        return x.div(y)

    def __truediv__(x, y):
        return x.div(y)

    def __gt__(x, y):
        y = NativeTensor.wrap_if_needed(y)
        if isinstance(y, NativeTensor): return NativeTensor(x.values > y.values)
        raise TypeError("%s does not support %s" % (type(x), type(y)))

    def pow(x, y):
        y = NativeTensor.wrap_if_needed(y)
        if isinstance(y, NativeTensor): return NativeTensor(x.values ** y.values)
        raise TypeError("%s does not support %s" % (type(x), type(y)))

    def __pow__(x, y):
        return x.pow(y)

    def transpose(x, *axes):
        if axes == ():
            return NativeTensor(x.values.transpose())
        else:
            return NativeTensor(x.values.transpose(axes))
        
    def copy(x):
        return NativeTensor(x.values)

    def neg(x):
        return NativeTensor(0 - x.values)

    def sum(x, axis=None, keepdims=False):
        return NativeTensor(x.values.sum(axis=axis, keepdims=keepdims))

    def clip(x, min, max):
        return NativeTensor.from_values(np.clip(x.values, min, max))

    def argmax(x, axis):
        return NativeTensor.from_values(x.values.argmax(axis=axis))

    def max(x, axis=None, keepdims=False):
        return NativeTensor.from_values(x.values.max(axis=axis, keepdims=keepdims))

    def min(x, axis=None, keepdims=False):
        return NativeTensor.from_values(x.values.min(axis=axis, keepdims=keepdims))

    def exp(x):
        return NativeTensor(np.exp(x.values))

    def log(x):
        # use this log to set log 0 -> -10^2
        return NativeTensor(np.ma.log(x.values).filled(-1e2))

    def inv(x):
        return NativeTensor(1. / x.values)

    def repeat(self, repeats, axis=None):
        self.values = np.repeat(self.values, repeats, axis=axis)
        return self

    def reshape(self, *shape):
        # ugly hack to unwrap shape if the shape is given as a tuple
        if isinstance(shape[0], tuple):
            shape = shape[0]
        return NativeTensor(self.values.reshape(shape))

    def pad(self, pad_width, mode='constant'):
        return NativeTensor(np.pad(self.values, pad_width=pad_width, mode=mode))

    def expand_dims(self, axis=0):
        self.values = np.expand_dims(self.values, axis=axis)
        return self

    def im2col(x, h_filter, w_filter, padding, strides):
        if use_cython:
            return NativeTensor(im2col_cython_float(x.values, h_filter, w_filter, padding, strides))
        else:
            return NativeTensor(im2col_indices(x.values, field_height=h_filter, field_width=w_filter, padding=padding,
                                               stride=strides))

    def col2im(x, imshape, field_height, field_width, padding, stride):
        if use_cython:
            return NativeTensor(col2im_cython_float(x.values, imshape[0], imshape[1], imshape[2], imshape[3],
                                            field_height, field_width, padding, stride))
        else:
            return NativeTensor(col2im_indices(x.values, imshape, field_height, field_width, padding, stride))

    def conv2d(x, filters, strides, padding):
        # shapes, assuming NCHW
        h_filter, w_filter, d_filters, n_filters = filters.shape
        n_x, d_x, h_x, w_x = x.shape
        h_out = int((h_x - h_filter + 2 * padding) / strides + 1)
        w_out = int((w_x - w_filter + 2 * padding) / strides + 1)

        # x to col
        X_col = x.im2col(h_filter, w_filter, padding, strides)
        W_col = filters.transpose(3, 2, 0, 1).reshape(n_filters, -1)
        out = W_col.dot(X_col)

        out = out.reshape(n_filters, h_out, w_out, n_x)
        out = out.transpose(3, 0, 1, 2)
        return out, X_col

    def conv2d_bw(x, d_y, cached_col, filter_shape, **kwargs):
        if isinstance(d_y, NativeTensor) or isinstance(d_y, PublicEncodedTensor):
            assert cached_col is not None
            h_filter, w_filter, d_filter, n_filter = filter_shape
            X_col = cached_col
            dout_reshaped = d_y.transpose(1, 2, 3, 0).reshape(n_filter, -1)
            dw = dout_reshaped.dot(X_col.transpose())
            dw = dw.reshape(filter_shape)
            return dw

        raise TypeError("%s does not support %s" % (type(x), type(y)))



DTYPE = 'object'
Q = 2657003489534545107915232808830590043

log2 = lambda x: log(x) / log(2)

# for arbitrary precision ints

# we need room for summing MAX_SUM values of MAX_DEGREE before during modulus reduction
MAX_DEGREE = 2
MAX_SUM = 2 ** 12
assert MAX_DEGREE * log2(Q) + log2(MAX_SUM) < 256

BASE = 2
PRECISION_INTEGRAL = 16
PRECISION_FRACTIONAL = 32
# TODO Gap as needed for local truncating

# we need room for double precision before truncating
assert PRECISION_INTEGRAL + 2 * PRECISION_FRACTIONAL < log(Q) / log(BASE)

COMMUNICATION_ROUNDS = 0
COMMUNICATED_VALUES = 0
USE_SPECIALIZED_TRIPLE=True
REUSE_MASK=True

def encode(rationals):
    # return (rationals * BASE ** PRECISION_FRACTIONAL).astype('int').astype(DTYPE) % Q
    try:
        return (rationals * BASE ** PRECISION_FRACTIONAL).astype('int').astype(DTYPE) % Q
    except OverflowError as e:
        print(rationals)
        raise e
        # print(e)
        # exit()


def decode(elements):
    try:
        map_negative_range = np.vectorize(lambda element: element if element <= Q / 2 else element - Q)
        return (map_negative_range(elements) / BASE ** PRECISION_FRACTIONAL)
    except OverflowError as e:
        print(elements)
        raise e


def wrap_if_needed(y):
    if isinstance(y, int) or isinstance(y, float): return PublicEncodedTensor.from_values(np.array([y]))
    if isinstance(y, np.ndarray):return PublicEncodedTensor.from_values(y)
    if isinstance(y, NativeTensor): return PublicEncodedTensor.from_values(y.values)
    return y


class PublicEncodedTensor:

    def __init__(self, values, elements=None):
        if not values is None:
            if not isinstance(values, np.ndarray):
                values = np.array([values])
            elements = encode(values)
        assert isinstance(elements, np.ndarray), "%s, %s, %s" % (values, elements, type(elements))
        self.elements = elements

    def from_values(values):
        return PublicEncodedTensor(values)

    def from_elements(elements):
        return PublicEncodedTensor(None, elements)

    def __repr__(self):
        return "PublicEncodedTensor(%s)" % decode(self.elements)

    def __getitem__(self, index):
        return PublicEncodedTensor.from_elements(self.elements[index])

    def __setitem__(self, idx, other):
        assert isinstance(other, PublicEncodedTensor)
        self.elements[idx] = other.elements

    def concatenate(self, other):
        assert isinstance(other, PublicEncodedTensor), type(other)
        return PublicEncodedTensor.from_elements(np.concatenate([self.elements, other.elements]))

    @property
    def shape(self):
        return self.elements.shape

    @property
    def size(self):
        return self.elements.size

    def unwrap(self):
        return decode(self.elements)

    def reveal(self):
        return NativeTensor.from_values(decode(self.elements))

    def truncate(self, amount=PRECISION_FRACTIONAL):
        positive_numbers = (self.elements <= Q // 2).astype(int)
        elements = self.elements
        elements = (Q + (2 * positive_numbers - 1) * elements) % Q  # x if x <= Q//2 else Q - x
        elements = np.floor_divide(elements, BASE ** amount)        # x // BASE**amount
        elements = (Q + (2 * positive_numbers - 1) * elements) % Q  # x if x <= Q//2 else Q - x
        return PublicEncodedTensor.from_elements(elements.astype(DTYPE))

    def add(x, y):
        y = wrap_if_needed(y)
        if isinstance(y, PublicEncodedTensor):
            return PublicEncodedTensor.from_elements((x.elements + y.elements) % Q)
        if isinstance(y, PrivateEncodedTensor):
            shares0 = (x.elements + y.shares0) % Q
            shares1 = y.shares1
            return PrivateEncodedTensor.from_shares(shares0, shares1)
        raise TypeError("%s does not support %s" % (type(x), type(y)))

    def __add__(x, y):
        return x.add(y)

    def sub(x, y):
        y = wrap_if_needed(y)
        if isinstance(y, PublicEncodedTensor): return PublicEncodedTensor.from_elements((x.elements - y.elements) % Q)
        if isinstance(y, PrivateEncodedTensor): return x.add(y.neg())  # TODO there might be a more efficient way
        raise TypeError("%s does not support %s" % (type(x), type(y)))

    def __sub__(x, y):
        return x.sub(y)

    def __gt__(x, y):
        y = wrap_if_needed(y)
        if isinstance(y, PublicEncodedTensor):
            return PublicEncodedTensor.from_values((x.elements - y.elements) % Q <=  0.5 * Q)
        raise TypeError("%s does not support %s" % (type(x), type(y)))

    def mul(x, y):
        y = wrap_if_needed(y)
        if isinstance(y, PublicFieldTensor):
            return PublicFieldTensor.from_elements((x.elements * y.elements) % Q)
        if isinstance(y, PublicEncodedTensor):
            return PublicEncodedTensor.from_elements((x.elements * y.elements) % Q).truncate()
        if isinstance(y, PrivateEncodedTensor):
            shares0 = (x.elements * y.shares0) % Q
            shares1 = (x.elements * y.shares1) % Q
            return PrivateEncodedTensor.from_shares(shares0, shares1).truncate()
        raise TypeError("%s does not support %s" % (type(x), type(y)))

    def __mul__(x, y):
        return x.mul(y)

    def dot(x, y):
        y = wrap_if_needed(y)
        if isinstance(y, PublicEncodedTensor): return PublicEncodedTensor.from_elements(
            x.elements.dot(y.elements) % Q).truncate()
        if isinstance(y, PrivateEncodedTensor):
            shares0 = x.elements.dot(y.shares0) % Q
            shares1 = x.elements.dot(y.shares1) % Q
            return PrivateEncodedTensor.from_shares(shares0, shares1).truncate()
        raise TypeError("%s does not support %s" % (type(x), type(y)))

    def div(x, y):
        y = wrap_if_needed(y)
        if isinstance(y, NativeTensor): return x.mul(y.inv())
        if isinstance(y, PublicEncodedTensor): return x.mul(y.inv())
        raise TypeError("%s does not support %s" % (type(x), type(y)))

    def matmul(x, y):
        return PublicEncodedTensor(np.matmul(x.elements, y.elements))

    def __div__(x, y):
        return x.div(y)

    def __truediv__(x, y):
        return x.div(y)

    def transpose(x, *axes):
        if axes == ():
            return PublicEncodedTensor.from_elements(x.elements.transpose())
        else:
            return PublicEncodedTensor.from_elements(x.elements.transpose(axes))

    def sum(x, axis=None, keepdims=False):
        return PublicEncodedTensor.from_elements(x.elements.sum(axis=axis, keepdims=keepdims))

    def argmax(x, axis):
        return PublicEncodedTensor.from_values(decode(x.elements).argmax(axis=axis))

    def neg(x):
        return PublicEncodedTensor.from_values(decode(x.elements) * -1)

    def inv(x):
        return PublicEncodedTensor.from_values(1. / decode(x.elements))

    def repeat(self, repeats, axis=None):
        self.elements = np.repeat(self.elements, repeats, axis=axis)
        return self

    def reshape(self, *shape):
        # ugly hack to unwrap shape if the shape is given as a tuple
        if isinstance(shape[0], tuple):
            shape = shape[0]
        return PublicEncodedTensor.from_elements(self.elements.reshape(shape))

    def expand_dims(self, axis=0):
        self.elements = np.expand_dims(self.elements, axis=axis)
        return self

    def pad(self, pad_width, mode='constant'):
        return PublicEncodedTensor.from_elements(np.pad(self.elements, pad_width=pad_width, mode=mode))

    def im2col(x, h_filter, w_filter, padding, strides):
        if use_cython:
            return PublicEncodedTensor.from_elements(im2col_cython_object(x.elements, h_filter, w_filter, padding, strides))
        else:
            return PublicEncodedTensor.from_elements(im2col_indices(x.elements.astype('float'),
                                                                    field_height=h_filter, field_width=w_filter,
                                                                    padding=padding,stride=strides).astype('int').astype(DTYPE))

    def col2im(x, imshape, field_height, field_width, padding, stride):
        if use_cython:
            return PublicEncodedTensor.from_elements(col2im_cython(x.elements, imshape[0], imshape[1], imshape[2], imshape[3],
                                              field_height, field_width, padding, stride))
        else:
            return PublicEncodedTensor.from_elements(col2im_indices(x.elements.astype('float'), imshape, field_height,
                                                                    field_width, padding, stride).astype('int').astype(DTYPE))

    def conv2d(x, filters, strides, padding):
        # shapes, assuming NCHW
        h_filter, w_filter, d_filters, n_filters = filters.shape
        n_x, d_x, h_x, w_x = x.shape
        h_out = int((h_x - h_filter + 2 * padding) / strides + 1)
        w_out = int((w_x - w_filter + 2 * padding) / strides + 1)

        # x to col
        X_col = x.im2col(h_filter, w_filter, padding, strides)
        W_col = filters.transpose(3, 2, 0, 1).reshape(n_filters, -1)
        out = W_col.dot(X_col)

        out = out.reshape(n_filters, h_out, w_out, n_x)
        out = out.transpose(3, 0, 1, 2)
        return out, X_col


    def conv2d_bw(x, d_y, cached_col, filter_shape, **kwargs):
        if isinstance(d_y, NativeTensor) or isinstance(d_y, PublicEncodedTensor):
            assert cached_col is not None
            h_filter, w_filter, d_filter, n_filter = filter_shape
            X_col = cached_col
            dout_reshaped = d_y.transpose(1, 2, 3, 0).reshape(n_filter, -1)
            dw = dout_reshaped.dot(X_col.transpose())
            dw = dw.reshape(filter_shape)
            return dw

        raise TypeError("%s does not support %s" % (type(x), type(y)))


class PublicFieldTensor:

    def __init__(self, elements):
        self.elements = elements

    def from_elements(elements):
        return PublicFieldTensor(elements)

    def __repr__(self):
        return "PublicFieldTensor(%s)" % self.elements

    def __getitem__(self, index):
        return PublicFieldTensor.from_elements(self.elements[index])

    @property
    def size(self):
        return self.elements.size

    @property
    def shape(self):
        return self.elements.shape

    def add(x, y):
        if isinstance(y, PublicFieldTensor):
            return PublicFieldTensor.from_elements((x.elements + y.elements) % Q)
        if isinstance(y, PrivateFieldTensor):
            shares0 = (x.elements + y.shares0) % Q
            shares1 = y.shares1
            return PrivateFieldTensor.from_shares(shares0, shares1)
        raise TypeError("%s does not support %s" % (type(x), type(y)))

    def __add__(x, y):
        return x.add(y)

    def mul(x, y):
        if isinstance(y, PublicFieldTensor):
            return PublicFieldTensor.from_elements((x.elements * y.elements) % Q)
        if isinstance(y, PrivateFieldTensor):
            shares0 = (x.elements * y.shares0) % Q
            shares1 = (x.elements * y.shares1) % Q
            return PrivateFieldTensor.from_shares(shares0, shares1)
        raise TypeError("%s does not support %s" % (type(x), type(y)))

    def __mul__(x, y):
        return x.mul(y)

    def dot(x, y):
        if isinstance(y, PublicFieldTensor):
            return PublicFieldTensor.from_elements((x.elements.dot(y.elements)) % Q)
        if isinstance(y, PrivateFieldTensor):
            shares0 = (x.elements.dot(y.shares0)) % Q
            shares1 = (x.elements.dot(y.shares1)) % Q
            return PrivateFieldTensor.from_shares(shares0, shares1)
        raise TypeError("%s does not support %s" % (type(x), type(y)))


    def transpose(x, *axes):
        if axes == ():
            return PublicFieldTensor.from_elements(x.elements.transpose())
        else:
            return PublicFieldTensor.from_elements(x.elements.transpose(axes))

    def reshape(self, *shape):
        # ugly hack to unwrap shape if the shape is given as a tuple
        if isinstance(shape[0], tuple):
            shape = shape[0]
        return PublicFieldTensor.from_elements(self.elements.reshape(shape))


    def im2col(x, h_filter, w_filter, padding, strides):
        if use_cython:
            return PublicFieldTensor.from_elements(im2col_cython_object(x.elements, h_filter, w_filter, padding,
                                    strides))
        else:
            return PublicFieldTensor.from_elements(im2col_indices(x.elements.astype('float'), field_height=h_filter,
                                                                  field_width=w_filter,padding=padding,stride=strides).astype('int').astype(DTYPE))


    def repeat(self, repeats, axis=None):
        self.elements = np.repeat(self.elements, repeats, axis=axis)
        return self


def share(elements):
    shares0 = np.array([random.randrange(Q) for _ in range(elements.size)]).astype(DTYPE).reshape(elements.shape)
    shares1 = ((elements - shares0) % Q).astype(DTYPE)
    return shares0, shares1

def reconstruct(shares0, shares1):
    return (shares0 + shares1) % Q


class PrivateFieldTensor:

    def __init__(self, elements, shares0=None, shares1=None):
        if not elements is None:
            shares0, shares1 = share(elements)
        assert isinstance(shares0, np.ndarray), "%s, %s, %s" % (values, shares0, type(shares0))
        assert isinstance(shares1, np.ndarray), "%s, %s, %s" % (values, shares1, type(shares1))
        assert shares0.shape == shares1.shape
        self.shares0 = shares0
        self.shares1 = shares1

    def from_elements(elements):
        return PrivateFieldTensor(elements)

    def from_shares(shares0, shares1):
        return PrivateFieldTensor(None, shares0, shares1)

    def reveal(self):
        global COMMUNICATION_ROUNDS, COMMUNICATED_VALUES
        COMMUNICATION_ROUNDS += 1
        COMMUNICATED_VALUES += np.prod(self.shape)
        return PublicFieldTensor.from_elements(reconstruct(self.shares0, self.shares1))

    def __repr__(self):
        return "PrivateFieldTensor(%s)" % self.reveal().elements

    def __getitem__(self, index):
        return PrivateFieldTensor.from_shares(self.shares0[index], self.shares1[index])

    @property
    def size(self):
        return self.shares0.size

    @property
    def shape(self):
        return self.shares0.shape

    def add(x, y):
        if isinstance(y, PrivateFieldTensor):
            shares0 = (x.shares0 + y.shares0) % Q
            shares1 = (x.shares1 + y.shares1) % Q
            return PrivateFieldTensor.from_shares(shares0, shares1)
        if isinstance(y, PublicFieldTensor):
            shares0 = (x.shares0 + y.elements) % Q
            shares1 = x.shares1
            return PrivateFieldTensor.from_shares(shares0, shares1)
        if isinstance(y, PrivateEncodedTensor):
            shares0 = (x.shares0 + y.shares0) % Q
            shares1 = (x.shares1 + y.shares1) % Q
            return PrivateFieldTensor.from_shares(shares0, shares1)
        raise TypeError("%s does not support %s" % (type(x), type(y)))

    def __add__(x, y):
        return x.add(y)

    def mul(x, y):
        if isinstance(y, PublicFieldTensor):
            shares0 = (x.shares0 * y.elements) % Q
            shares1 = (x.shares1 * y.elements) % Q
            return PrivateFieldTensor.from_shares(shares0, shares1)
        raise TypeError("%s does not support %s" % (type(x), type(y)))

    def __mul__(x, y):
        return x.mul(y)

    def dot(x, y):
        if isinstance(y, PublicFieldTensor):
            shares0 = (x.shares0.dot(y.elements)) % Q
            shares1 = (x.shares1.dot(y.elements)) % Q
            return PrivateFieldTensor.from_shares(shares0, shares1)
        if isinstance(y, PrivateFieldTensor):
            shares0 = (x.shares0.dot(y.shares0)) % Q
            shares1 = (x.shares1.dot(y.shares1)) % Q
            return PrivateFieldTensor.from_shares(shares0, shares1)
        raise TypeError("%s does not support %s" % (type(x), type(y)))

    def transpose(x, *axes):
        if axes == ():
            return PrivateFieldTensor.from_shares(x.shares0.transpose(), x.shares1.transpose())
        else:
            return PrivateFieldTensor.from_shares(x.shares0.transpose(axes), x.shares1.transpose(axes))

    def reshape(self, *shape):
        # ugly hack to unwrap shape if the shape is given as a tuple
        if isinstance(shape[0], tuple):
            shape = shape[0]
        return PrivateFieldTensor.from_shares(self.shares0.reshape(shape), self.shares1.reshape(shape))

    def conv2d(x, y, strides, padding):
        if isinstance(y, PublicFieldTensor):

            # shapes, assuming NCHW
            h_filter, w_filter, d_filters, n_filters = y.shape
            n_x, d_x, h_x, w_x = x.shape
            h_out = int((h_x - h_filter + 2 * padding) / strides + 1)
            w_out = int((w_x - w_filter + 2 * padding) / strides + 1)

            # x to col
            X_col = x.im2col(h_filter, w_filter, padding, strides)
            W_col = y.transpose(3, 2, 0, 1).reshape(n_filters, -1)

            out = W_col.dot(X_col)
            out = out.reshape(n_filters, h_out, w_out, n_x)
            out = out.transpose(3, 0, 1, 2)
            return out, X_col

        raise TypeError("%s does not support %s" % (type(x), type(y)))

    def im2col(x, h_filter, w_filter, padding, strides):
        if use_cython:
            shares0 = im2col_cython_object(x.shares0, h_filter, w_filter, padding, strides)
            shares1 = im2col_cython_object(x.shares1, h_filter, w_filter, padding, strides)
            return PrivateFieldTensor.from_shares(shares0, shares1)
        else:
            shares0 = im2col_indices(x.shares0.astype('float'), field_height=h_filter, field_width=w_filter,
                                     padding=padding,stride=strides).astype('int').astype(DTYPE)
            shares1 = im2col_indices(x.shares1.astype('float'), field_height=h_filter, field_width=w_filter,
                                     padding=padding,stride=strides).astype('int').astype(DTYPE)
            return PrivateFieldTensor.from_shares(shares0, shares1)


def generate_mul_triple(shape1, shape2):
    a = np.array([random.randrange(Q) for _ in range(np.prod(shape1))]).astype(DTYPE).reshape(shape1)
    b = np.array([random.randrange(Q) for _ in range(np.prod(shape2))]).astype(DTYPE).reshape(shape2)
    ab = (a * b) % Q
    return PrivateFieldTensor.from_elements(a), \
           PrivateFieldTensor.from_elements(b), \
           PrivateFieldTensor.from_elements(ab)

def generate_dot_triple(m, n, o, a=None, b=None):
    if a is None: a = np.array([random.randrange(Q) for _ in range(m * n)]).astype(DTYPE).reshape((m, n))
    else: a = a.reveal().elements
    if b is None: b = np.array([random.randrange(Q) for _ in range(n * o)]).astype(DTYPE).reshape((n, o))
    else: b = b.reveal().elements

    ab = np.dot(a, b)
    return PrivateFieldTensor.from_elements(a), \
           PrivateFieldTensor.from_elements(b), \
           PrivateFieldTensor.from_elements(ab)

def generate_conv_triple(xshape, yshape, strides, padding):

    h_filter, w_filter, d_filters, n_filters = yshape

    a = np.array([random.randrange(Q) for _ in range(np.prod(xshape))]).astype(DTYPE).reshape(xshape)
    b = np.array([random.randrange(Q) for _ in range(np.prod(yshape))]).astype(DTYPE).reshape(yshape)

    if use_cython:
        a_col = im2col_cython_object(a, h_filter, w_filter, padding, strides)
    else:
        a_col = im2col_indices(a, field_height=h_filter, field_width=w_filter, padding=padding, stride=strides)

    b_col = b.transpose(3, 2, 0, 1).reshape(n_filters, -1)
    a_conv_b = np.dot(b_col, a_col)

    return PrivateFieldTensor.from_elements(a), PrivateFieldTensor.from_elements(b), \
           PrivateFieldTensor.from_elements(a_conv_b), PrivateFieldTensor.from_elements(a_col)

def generate_convbw_triple(xshape, yshape, a=None, a_col=None):
    if a is None:
        a = np.array([random.randrange(Q) for _ in range(np.prod(xshape))]).astype(DTYPE).reshape(xshape)
    else:
        a = a.reveal().elements

    if a_col is None:
        a_col = a.im2col()
    else:
        a_col = a_col.reveal().elements

    b = np.array([random.randrange(Q) for _ in range(np.prod(yshape))]).astype(DTYPE).reshape(yshape)

    a_convbw_b = b.dot(a_col.transpose())
    return PrivateFieldTensor.from_elements(a), PrivateFieldTensor.from_elements(b), \
           PrivateFieldTensor.from_elements(a_convbw_b)



def generate_conv_pool_bw_triple(xshape, yshape, pool_size, n_filter, a=None, a_col=None):
    if a is None:
        a = np.array([random.randrange(Q) for _ in range(np.prod(xshape))]).astype(DTYPE).reshape(xshape)
    else:
        a = a.reveal().elements

    if a_col is None:
        a_col = a.im2col()
    else:
        a_col = a_col.reveal().elements

    b = np.array([random.randrange(Q) for _ in range(np.prod(yshape))]).astype(DTYPE).reshape(yshape)
    b_expanded = b.repeat(pool_size[0], axis=2).repeat(pool_size[1], axis=3).transpose(1, 2, 3, 0).reshape(n_filter, -1)
    a_conv_pool_bw_b = b_expanded.dot(a_col.transpose())

    return PrivateFieldTensor.from_elements(a), PrivateFieldTensor.from_elements(b),\
           PrivateFieldTensor.from_elements(a_conv_pool_bw_b), PrivateFieldTensor.from_elements(b_expanded)


class PrivateEncodedTensor:

    def __init__(self, values, shares0=None, shares1=None):
        if not values is None:
            if not isinstance(values, np.ndarray):
                values = np.array([values])
            shares0, shares1 = share(encode(values))
        assert isinstance(shares0, np.ndarray), "%s, %s, %s" % (values, shares0, type(shares0))
        assert isinstance(shares1, np.ndarray), "%s, %s, %s" % (values, shares1, type(shares1))
        assert shares0.dtype == shares1.dtype
        assert shares0.shape == shares1.shape
        self.shares0 = shares0
        self.shares1 = shares1
        self.mask = None
        self.masked_transformed = None
        self.masked = None
        self.masked_transformed = None

    def from_values(values):
        return PrivateEncodedTensor(values)

    def from_elements(elements):
        shares0, shares1 = share(elements)
        return PrivateEncodedTensor(None, shares0, shares1)

    def from_shares(shares0, shares1):
        return PrivateEncodedTensor(None, shares0, shares1)

    def copy(self):
        return PrivateEncodedTensor(None, self.shares0, self.shares1)

    def __repr__(self):
        elements = (self.shares0 + self.shares1) % Q
        return "PrivateEncodedTensor(%s)" % decode(elements)

    def __getitem__(self, index):
        return PrivateEncodedTensor.from_shares(self.shares0[index], self.shares1[index])

    def __setitem__(self, idx, other):
        assert isinstance(other, PrivateEncodedTensor)
        self.shares0[idx] = other.shares0
        self.shares1[idx] = other.shares1

    def concatenate(self, other):
        assert isinstance(other, PrivateEncodedTensor), type(other)
        shares0 = np.concatenate([self.shares0, other.shares0])
        shares1 = np.concatenate([self.shares1, other.shares1])
        return PrivateEncodedTensor.from_shares(shares0, shares1)

    @property
    def shape(self):
        return self.shares0.shape

    @property
    def size(self):
        return self.shares0.size

    def unwrap(self):
        return decode((self.shares0 + self.shares1) % Q)

    def reveal(self):
        return NativeTensor.from_values(decode((self.shares0 + self.shares1) % Q))

    def truncate(self, amount=PRECISION_FRACTIONAL):
        shares0 = np.floor_divide(self.shares0, BASE ** amount) % Q
        shares1 = (Q - (np.floor_divide(Q - self.shares1, BASE ** amount))) % Q
        return PrivateEncodedTensor.from_shares(shares0, shares1)

    def add(x, y):
        y = wrap_if_needed(y)
        if isinstance(y, PublicEncodedTensor):
            shares0 = (x.shares0 + y.elements) % Q
            shares1 = x.shares1 + np.zeros(y.elements.shape, dtype=DTYPE) # hack to fix broadcasting
            return PrivateEncodedTensor.from_shares(shares0, shares1)
        if isinstance(y, PrivateEncodedTensor):
            shares0 = (x.shares0 + y.shares0) % Q
            shares1 = (x.shares1 + y.shares1) % Q
            return PrivateEncodedTensor.from_shares(shares0, shares1)
        raise TypeError("%s does not support %s" % (type(x), type(y)))

    def __add__(x, y):
        return x.add(y)

    def add_at(x, indices, y):
        y = wrap_if_needed(y)
        if isinstance(y, PublicEncodedTensor):
            np.add.at(x.shares0, indices, y.elements)
            x.shares0 = x.shares0 % Q
        elif isinstance(y, PrivateEncodedTensor):
            np.add.at(x.shares0, indices, y.shares0)
            np.add.at(x.shares1, indices, y.shares1)
            x.shares0 = x.shares0 % Q
            x.shares1 = x.shares1 % Q
        else:
            raise TypeError("%s does not support %s" % (type(x), type(y)))

    def sub(x, y):
        y = wrap_if_needed(y)
        if isinstance(y, PublicEncodedTensor):
            shares0 = (x.shares0 - y.elements) % Q
            shares1 = x.shares1
            return PrivateEncodedTensor.from_shares(shares0, shares1)
        if isinstance(y, PrivateEncodedTensor):
            shares0 = (x.shares0 - y.shares0) % Q
            shares1 = (x.shares1 - y.shares1) % Q
            return PrivateEncodedTensor.from_shares(shares0, shares1)
        if isinstance(y, PrivateFieldTensor):
            shares0 = (x.shares0 - y.shares0) % Q
            shares1 = (x.shares1 - y.shares1) % Q
            return PrivateFieldTensor.from_shares(shares0, shares1)
        raise TypeError("%s does not support %s" % (type(x), type(y)))

    def __sub__(x, y):
        return x.sub(y)

    def mul(x, y, precomputed=None, use_specialized_triple=USE_SPECIALIZED_TRIPLE):
        y = wrap_if_needed(y)
        if isinstance(y, PublicEncodedTensor):
            shares0 = (x.shares0 * y.elements) % Q
            shares1 = (x.shares1 * y.elements) % Q
            return PrivateEncodedTensor.from_shares(shares0, shares1).truncate()
        if isinstance(y, PrivateEncodedTensor):
            if use_specialized_triple:
                if precomputed is None: precomputed = generate_mul_triple(x.shape, y.shape)
                a, b, ab = precomputed
                alpha = (x - a).reveal()
                beta = (y - b).reveal()
                z = alpha.mul(beta) + \
                    alpha.mul(b) + \
                    a.mul(beta) + \
                    ab
            else:
                x_broadcasted0, y_broadcasted0 = np.broadcast_arrays(x.shares0, y.shares0)
                x_broadcasted1, y_broadcasted1 = np.broadcast_arrays(x.shares1, y.shares1)
                x_broadcasted = PrivateEncodedTensor.from_shares(x_broadcasted0, x_broadcasted1)
                y_broadcasted = PrivateEncodedTensor.from_shares(y_broadcasted0, y_broadcasted1)

                if precomputed is None: precomputed = generate_mul_triple(x_broadcasted.shape, y_broadcasted.shape)
                a, b, ab = precomputed
                assert x_broadcasted.shape == y_broadcasted.shape
                assert x_broadcasted.shape == a.shape
                assert y_broadcasted.shape == b.shape
                alpha = (x_broadcasted - a).reveal()
                beta = (y_broadcasted - b).reveal()
                z = alpha.mul(beta) + \
                    alpha.mul(b) + \
                    a.mul(beta) + \
                    ab
            return PrivateEncodedTensor.from_shares(z.shares0, z.shares1).truncate()
        if isinstance(y, PrivateFieldTensor):
            shares0 = (x.shares0 * y.shares0) % Q
            shares1 = (x.shares1 * y.shares1) % Q
            return PrivateFieldTensor.from_shares(shares0, shares1)
        if isinstance(y, PublicFieldTensor):
            shares0 = (x.shares0 * y.elements) % Q
            shares1 = (x.shares1 * y.elements) % Q
            return PrivateFieldTensor.from_shares(shares0, shares1)
        raise TypeError("%s does not support %s" % (type(x), type(y)))

    def __mul__(x, y):
        return x.mul(y)

    def dot(x, y, precomputed=None, reuse_mask=REUSE_MASK):
        y = wrap_if_needed(y)
        if isinstance(y, PublicEncodedTensor):
            assert x.shape[-1] == y.shape[0]
            shares0 = x.shares0.dot(y.elements) % Q
            shares1 = x.shares1.dot(y.elements) % Q
            return PrivateEncodedTensor.from_shares(shares0, shares1).truncate()
        if isinstance(y, PrivateEncodedTensor):
            m = x.shape[0]
            n = x.shape[1]
            o = y.shape[1]
            assert n == y.shape[0]
            a, b, alpha, beta = None, None, None, None
            if reuse_mask:
                if x.mask is not None:
                    a = x.mask
                    alpha = x.masked
                if y.mask is not None:
                    b = y.mask
                    beta = y.masked

            if precomputed is None: precomputed = generate_dot_triple(m, n, o, a, b)
            a, b, ab = precomputed

            if alpha is None:
                alpha = (x - a).reveal() # (PrivateEncodedTensor - PrivateFieldTensor).reveal() = PublicFieldTensor
            if beta is None:
                beta = (y - b).reveal()  # (PrivateEncodedTensor - PrivateFieldTensor).reveal() = PublicFieldTensor

            z = alpha.dot(beta) + alpha.dot(b) + a.dot(beta) + ab
            # PublicFieldTensor.dot(PublicFieldTensor) = PublicFieldTensor
            # PublicFieldTensor.dot(PrivateFieldTensor) = PrivateFieldTensor
            # PrivateFieldTensor.dot(PublicFieldTensor) = PrivateFieldTensor
            # PrivateFieldTensor = PrivateFieldTensor
            # PublicFieldTensor + PrivateFieldTensor + PrivateFieldTensor + PrivateFieldTensor = PrivateFieldTensor

            # cache masks
            if reuse_mask:
                x.mask = a
                x.masked = alpha
                if isinstance(y, PrivateEncodedTensor):
                    y.mask = b
                    y.masked = beta
            return PrivateEncodedTensor.from_shares(z.shares0, z.shares1).truncate()
        raise TypeError("%s does not support %s" % (type(x), type(y)))

    def div(x, y):
        y = wrap_if_needed(y)
        if isinstance(y, NativeTensor): return x.mul(y.inv())
        if isinstance(y, PublicEncodedTensor): return x.mul(y.inv())
        raise TypeError("%s does not support %s" % (type(x), type(y)))


    def __truediv__(x, y):
        return x.div(y)

    def neg(self):
        minus_one = PublicFieldTensor.from_elements(np.array([Q - 1]))
        z = self.mul(minus_one)
        return PrivateEncodedTensor.from_shares(z.shares0, z.shares1)

    def transpose(self, *axes):
        if axes == ():
            return PrivateEncodedTensor.from_shares(self.shares0.transpose(), self.shares1.transpose())
        else:
            return PrivateEncodedTensor.from_shares(self.shares0.transpose(axes), self.shares1.transpose(axes))

    def expand_dims(self, axis=0):
        self.shares0 = np.expand_dims(self.shares0, axis=axis)
        self.shares1 = np.expand_dims(self.shares1, axis=axis)
        return self

    def sum(self, axis, keepdims=False):
        shares0 = self.shares0.sum(axis=axis, keepdims=keepdims) % Q
        shares1 = self.shares1.sum(axis=axis, keepdims=keepdims) % Q
        return PrivateEncodedTensor.from_shares(shares0, shares1)

    def repeat(self, repeats, axis=None):
        self.shares0 = np.repeat(self.shares0, repeats, axis=axis)
        self.shares1 = np.repeat(self.shares1, repeats, axis=axis)
        return self

    def reshape(self, *shape):
        # ugly hack to unwrap shape if the shape is given as a tuple
        if isinstance(shape[0], tuple):
            shape = shape[0]
        return PrivateEncodedTensor.from_shares(self.shares0.reshape(shape), self.shares1.reshape(shape))

    def pad(self, pad_width, mode='constant'):
        return PrivateEncodedTensor.from_shares(np.pad(self.shares0, pad_width=pad_width, mode=mode),
                                                np.pad(self.shares1, pad_width=pad_width, mode=mode))


    def im2col(x, h_filter, w_filter, padding, strides):
        if use_cython:
            shares0 = im2col_cython_object(x.shares0, h_filter, w_filter, padding, strides)
            shares1 = im2col_cython_object(x.shares1, h_filter, w_filter, padding, strides)
            return PrivateEncodedTensor.from_shares(shares0, shares1)
        else:
            shares0 = im2col_indices(x.shares0.astype('float'), field_height=h_filter, field_width=w_filter,
                                     padding=padding,stride=strides).astype('int').astype(DTYPE)
            shares1 = im2col_indices(x.shares1.astype('float'), field_height=h_filter, field_width=w_filter,
                                     padding=padding,stride=strides).astype('int').astype(DTYPE)
            return PrivateEncodedTensor.from_shares(shares0, shares1)


    def col2im(x, imshape, field_height, field_width, padding, stride):
        if use_cython:
            shares0 =col2im_cython(x.shares0, imshape[0], imshape[1], imshape[2], imshape[3],
                                   field_height, field_width, padding, stride)
            shares1 =col2im_cython(x.shares1, imshape[0], imshape[1], imshape[2], imshape[3],
                                   field_height, field_width, padding, stride)

            return PrivateEncodedTensor.from_shares(shares0, shares1)
        else:
            shares0 = col2im_indices(x.shares0.astype('float'), imshape, field_height, field_width, padding,
                                     stride).astype('int').astype(DTYPE)
            shares1 = col2im_indices(x.shares1.astype('float'), imshape, field_height, field_width, padding,
                                     stride).astype('int').astype(DTYPE)
            return PrivateEncodedTensor.from_shares(shares0, shares1)


    def conv2d(x, y, strides, padding, use_specialized_triple=USE_SPECIALIZED_TRIPLE, precomputed=None, save_mask=True):
        h_filter, w_filter, d_y, n_filters = y.shape
        n_x, d_x, h_x, w_x = x.shape
        h_out = int((h_x - h_filter + 2 * padding) / strides + 1)
        w_out = int((w_x - w_filter + 2 * padding) / strides + 1)

        if isinstance(y, PublicEncodedTensor):
            X_col = x.im2col(h_filter, w_filter, padding, strides)
            y_col = y.transpose(3, 2, 0, 1).reshape(n_filters, -1)
            out = y_col.dot(X_col).reshape(n_filters, h_out, w_out, n_x).transpose(3, 0, 1, 2)
            return out, X_col

        if isinstance(y, PrivateEncodedTensor):
            if use_specialized_triple:
                if precomputed is None:
                    precomputed = generate_conv_triple(x.shape, y.shape, strides, padding)

                # this part of code creates the masks and masked values. a and b are PrivateFieldTensors.
                # alpha and beta are PublicFieldTensors. The final result is a PrivateFieldTensor

                a, b, a_conv_b, a_col = precomputed          # PrivateFieldTensors
                alpha = (x - a).reveal()
                beta = (y - b).reveal()

                alpha_col = alpha.im2col(h_filter, w_filter, padding, strides)
                beta_col = beta.transpose(3, 2, 0, 1).reshape(n_filters, -1)
                b_col = b.transpose(3, 2, 0, 1).reshape(n_filters, -1)

                alpha_conv_beta = beta_col.dot(alpha_col)
                alpha_conv_b = b_col.dot(alpha_col)
                a_conv_beta = beta_col.dot(a_col)

                z = (alpha_conv_beta + alpha_conv_b + a_conv_beta + a_conv_b).reshape(n_filters, h_out,
                                                                                      w_out, n_x).transpose(3, 0, 1, 2)
                # cache
                if save_mask:
                    x.mask, x.mask_transformed, x.masked_transformed = a, a_col, alpha_col
                    y.mask, y.mask_transformed, y.masked_transformed = b, b_col, beta_col

                return PrivateEncodedTensor.from_shares(z.shares0, z.shares1).truncate(), None

            else:
                X_col = x.im2col(h_filter, w_filter, padding, strides)
                W_col = y.transpose(3, 2, 0, 1).reshape(n_filters, -1)
                out = W_col.dot(X_col).reshape(n_filters, h_out, w_out, n_x).transpose(3, 0, 1, 2)
                return out, X_col

        raise TypeError("%s does not support %s" % (type(x), type(y)))



    def conv2d_bw(x, d_y, cache, filter_shape, padding=None, strides=None, use_specialized_triple=USE_SPECIALIZED_TRIPLE,
                  reuse_mask=REUSE_MASK, precomputed=None):

        h_filter, w_filter, d_filter, n_filter = filter_shape
        d_y_reshaped = d_y.transpose(1, 2, 3, 0).reshape(n_filter, -1)

        if isinstance(d_y, PublicEncodedTensor) or isinstance(d_y, NativeTensor):
            X_col = cache
            dw = d_y_reshaped.dot(X_col.transpose())
            dw = dw.reshape(filter_shape)
            return dw
        if isinstance(d_y, PrivateEncodedTensor):
            if use_specialized_triple:
                # we need: x, a, a_col, alpha_col
                if reuse_mask:
                    a, a_col, alpha_col = x.mask, x.mask_transformed, x.masked_transformed
                    a, b, a_convbw_b = generate_convbw_triple(a.shape, d_y_reshaped.shape, a=a, a_col=a_col)
                    beta = (d_y_reshaped - b).reveal()

                    alpha_convbw_beta = beta.dot(alpha_col.transpose())
                    alpha_convbw_b = b.dot(alpha_col.transpose())
                    a_convbw_beta = beta.dot(a_col.transpose())

                    z = (alpha_convbw_beta + alpha_convbw_b + a_convbw_beta + a_convbw_b).reshape(filter_shape)
                    return PrivateEncodedTensor.from_shares(z.shares0, z.shares1).truncate()

                else:
                    a, b, a_convbw_b = generate_convbw_triple(x.shape, d_y_reshaped.shape)
                    alpha = (x - a).reveal()
                    beta = (d_y_reshaped - b).reveal()

                    alpha_col = alpha.im2col(h_filter, w_filter, padding, strides)
                    a_col = a.im2col(h_filter, w_filter, padding, strides)

                    alpha_convbw_beta = beta.dot(alpha_col.transpose())
                    alpha_convbw_b = b.dot(alpha_col.transpose())
                    a_convbw_beta = beta.dot(a_col.transpose())

                    z = (alpha_convbw_beta + alpha_convbw_b + a_convbw_beta + a_convbw_b).reshape(filter_shape)
                    return PrivateEncodedTensor.from_shares(z.shares0, z.shares1).truncate()
            else:
                X_col = cache
                dw = d_y_reshaped.dot(X_col.transpose())
                dw = dw.reshape(filter_shape)
                return dw


    def convavgpool_bw(x, d_y, cache, filter_shape, padding=None, strides=None, pool_size=None, pool_strides=None,
                       use_specialized_triple=USE_SPECIALIZED_TRIPLE, reuse_mask=REUSE_MASK, precomputed=None):
        h_filter, w_filter, d_filter, n_filter = filter_shape
        pool_area = pool_size[0] * pool_size[1]

        if isinstance(d_y, PublicEncodedTensor) or isinstance(d_y, NativeTensor):
            d_y_expanded = d_y.repeat(pool_size[0], axis=2)
            d_y_expanded = d_y_expanded.repeat(pool_size[1], axis=3)
            d_y_conv = d_y_expanded / pool_area
            X_col = cache
            d_y_conv_reshaped = d_y_conv.transpose(1, 2, 3, 0).reshape(n_filter, -1)
            dw = d_y_conv_reshaped.dot(X_col.transpose())
            dw = dw.reshape(filter_shape)
            return dw
        if isinstance(d_y, PrivateEncodedTensor):
            # this layer is used to optimize communication performance
            assert use_specialized_triple and reuse_mask
            assert pool_size[0] == pool_strides and pool_size[1] == pool_strides

            a, a_col, alpha_col = x.mask, x.mask_transformed, x.masked_transformed
            a, b, a_conv_pool_bw_b, b_expanded = generate_conv_pool_bw_triple(a.shape, d_y.shape, pool_size=pool_size,
                                                                              n_filter=n_filter, a=a, a_col=a_col)
            beta = ((d_y / pool_area) - b).reveal() # divide by pool area before specialized triplet
            beta_expanded = beta.repeat(pool_size[0], axis=2).repeat(pool_size[1], axis=3).transpose(1, 2, 3, 0).reshape(n_filter, -1)

            alpha_conv_pool_bw_beta = beta_expanded.dot(alpha_col.transpose())
            alpha_conv_pool_bw_b = b_expanded.dot(alpha_col.transpose())
            a_conv_pool_bw_beta = beta_expanded.dot(a_col.transpose())

            z = (alpha_conv_pool_bw_beta + alpha_conv_pool_bw_b + a_conv_pool_bw_beta + a_conv_pool_bw_b
                 ).reshape(filter_shape)
            return PrivateEncodedTensor.from_shares(z.shares0, z.shares1).truncate()



ANALYTIC_STORE = []
NEXT_ID = 0


class AnalyticTensor:

    def __init__(self, values, shape=None, ident=None):
        if not values is None:
            if not isinstance(values, np.ndarray):
                values = np.array([values])
            shape = values.shape
        if ident is None:
            global NEXT_ID
            ident = "tensor_%d" % NEXT_ID
            NEXT_ID += 1
        self.shape = shape
        self.ident = ident

    def from_shape(shape, ident=None):
        return AnalyticTensor(None, shape, ident)

    def __repr__(self):
        return "AnalyticTensor(%s, %s)" % (self.shape, self.ident)

    def __getitem__(self, index):
        start, stop, _ = index.indices(self.shape[0])
        shape = list(self.shape)
        shape[0] = stop - start
        ident = "%s_%d,%d" % (self.ident, start, stop)
        return AnalyticTensor.from_shape(tuple(shape), ident)

    def reset():
        global ANALYTIC_STORE
        ANALYTIC_STORE = []

    def store():
        global ANALYTIC_STORE
        return ANALYTIC_STORE

    @property
    def size(self):
        return np.prod(self.shape)

    def reveal(self):
        return self

    def wrap_if_needed(y):
        if isinstance(y, int) or isinstance(y, float): return AnalyticTensor.from_shape((1,))
        if isinstance(y, np.ndarray): return AnalyticTensor.from_shape(y.shape)
        return y

    def add(x, y):
        y = AnalyticTensor.wrap_if_needed(y)
        ANALYTIC_STORE.append(('add', x, y))
        return AnalyticTensor.from_shape(x.shape)

    def __add__(x, y):
        return x.add(y)

    def sub(x, y):
        y = AnalyticTensor.wrap_if_needed(y)
        ANALYTIC_STORE.append(('sub', x, y))
        return AnalyticTensor.from_shape(x.shape)

    def __sub__(x, y):
        return x.sub(y)

    def mul(x, y):
        y = AnalyticTensor.wrap_if_needed(y)
        ANALYTIC_STORE.append(('mul', x, y))
        return AnalyticTensor.from_shape(x.shape)

    def __mul__(x, y):
        return x.mul(y)

    def dot(x, y):
        y = AnalyticTensor.wrap_if_needed(y)
        ANALYTIC_STORE.append(('dot', x, y))
        return AnalyticTensor.from_shape(x.shape)

    def div(x, y):
        y = AnalyticTensor.wrap_if_needed(y)
        ANALYTIC_STORE.append(('div', x, y))
        return AnalyticTensor.from_shape(x.shape)

    def neg(self):
        ANALYTIC_STORE.append(('neg', self))
        return AnalyticTensor.from_shape(self.shape)

    def transpose(self):
        ANALYTIC_STORE.append(('transpose', self))
        return self

    def sum(self, axis):
        ANALYTIC_STORE.append(('sum', self))
        return AnalyticTensor.from_shape(self.shape)
