'''
`tasks` package are collection of useful scripts.
`dataset` module are script for dataset management
'''
from glob import glob

import os
import cv2
import numpy as np
from bidict import bidict
import tensorflow as tf
from tqdm import tqdm

from nnlab.utils import fp
from nnlab.data import image as im #image util

def rgb_tup(hex_int):
    assert 0 < hex_int < 0xFFFFFF, hex_int
    return (
        (hex_int & 0xFF0000) >> (8 * 2),
        (hex_int & 0x00FF00) >> (8 * 1),
        (hex_int & 0x0000FF) >> (8 * 0))

def one_hot_tup(num_class, bin_int):
    assert 0 < bin_int <= 2**(num_class - 1), \
        'assert fail: 0 < {} <= {}'.format(
            bin_int, 2**(num_class - 1))
    assert (bin_int % 2 == 0 or bin_int == 1), \
        'assert fail: {} % 2 == 0 or {} == 1'.format(bin_int)

    ret = [0] * num_class
    for i in range(num_class + 1):
        if bin_int >> i == 0:
            ret[-i] = 1
            return tuple(ret)

def _bytes_feature(value):
    """Returns a bytes_list from a string / byte."""
    if isinstance(value, type(tf.constant(0))):
        value = value.numpy() # BytesList won't unpack a string from an EagerTensor.
    return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))
def _float_feature(value):
    """Returns a float_list from a float / double."""
    return tf.train.Feature(float_list=tf.train.FloatList(value=[value]))
def _int64_feature(value):
    """Returns an int64_list from a bool / enum / int / uint."""
    return tf.train.Feature(int64_list=tf.train.Int64List(value=[value]))

def generate(train_path_pairs, valid_path_pairs, test_path_pairs,
        src_dst_colormap, out_path, look_and_feel_check=False):
    '''
    Generate dataset using image, mask path pairs 
    from `train_path_pairs`, `valid_path_pairs`, `test_path_pairs`.
    Masks are mapped by src_dst_colormap. Finally, dataset is saved to `out_path`.

    `src_dst_colormap` is encoded and saved in src_rgbs and dst_1hots.
    imag, mask pairs are saved in [train-pairs, valid-pairs, test-pairs] sequence.

    output dataset is 
    [
        {num_train: TR,
         num_valid: VA,
         num_test:  TE,
         num_class:  N}
        {src_rgbs:  [ 0x??, 0x??, .. ]
         dst_1hots: [ 1, 2, 4, 8.. ]}
        {h:, w:, c:, mc:, img:, mask:}
        {h:, w:, c:, mc:, img:, mask:}
        ...
    ]

    If look_and_feel_check == True, load and display 
    image and masks in generated dataset.

    Image, mask paths are must be paired, and exists.
    '''
    # Preconditions
    num_train = len(train_path_pairs)
    num_valid = len(valid_path_pairs)
    num_test  = len(test_path_pairs)
    img_paths, mask_paths = fp.unzip(
        train_path_pairs + valid_path_pairs + test_path_pairs)
    assert all(map(lambda p: os.path.exists(p), img_paths)), \
        'some image file path are not exist'
    assert all(map(lambda p: os.path.exists(p), mask_paths)), \
        'some mask file path are not exist'

    # Load images and masks.
    imgseq = fp.map(cv2.imread, img_paths)
    maskseq = fp.map(
        fp.pipe(cv2.imread, im.map_colors(src_dst_colormap)), mask_paths)

    # Create and save tfrecords dataset.
    def datum_example(img_bin, mask_bin):
        h,w,c   = img_bin.shape
        mh,mw,_ = mask_bin.shape
        assert h == mh and w == mw, 'img.h,w = {} != {} mask.h,w'.format(
            img_bin.shape[:2], mask_bin.shape[:2])

        feature = {
            'h': _int64_feature(h),
            'w': _int64_feature(w),
            'c': _int64_feature(c),
            'mc': _int64_feature(len(src_dst_colormap)), # mask channels
            'img': _bytes_feature(img_bin.tobytes()),
            'mask': _bytes_feature(mask_bin.tobytes()),
        }

        return tf.train.Example(features=tf.train.Features(feature=feature))

    
    with tf.io.TFRecordWriter(out_path) as writer:
        #for img_bin, mask_bin in tqdm(fp.take(4,zip(imgseq, maskseq)), total=4):
        for img_bin, mask_bin in tqdm(zip(imgseq, maskseq), total=len(img_paths)):
            tf_example = datum_example(img_bin, mask_bin)
            writer.write(tf_example.SerializeToString())

    if look_and_feel_check:
        def parse_single_example(example):
            return tf.io.parse_single_example(
                example,
                {'h': tf.io.FixedLenFeature([], tf.int64),
                 'w': tf.io.FixedLenFeature([], tf.int64),
                 'c': tf.io.FixedLenFeature([], tf.int64),
                 'mc': tf.io.FixedLenFeature([], tf.int64),
                 'img': tf.io.FixedLenFeature([], tf.string),
                 'mask': tf.io.FixedLenFeature([], tf.string)})
        # Load saved tfrecords dataset
        snet_dset = tf.data.TFRecordDataset(out_path)
        parsed_snet_dset = snet_dset.map(parse_single_example)

        # Display image, maskss
        for no, datum in enumerate(parsed_snet_dset): 
            h = datum['h'].numpy()
            w = datum['w'].numpy()
            c = datum['c'].numpy()
            mc = datum['mc'].numpy()
            img_raw = datum['img'].numpy()
            mask_raw = datum['mask'].numpy()

            #img = Image.open(io.BytesIO(img_raw))
            img  = np.frombuffer(img_raw, dtype=np.uint8).reshape((h,w,c))
            mask = np.frombuffer(mask_raw, dtype=np.uint8).reshape((h,w,mc))

            cv2.imshow('im', img)
            #cv2.imshow('mask', im.map_colors(src_dst_colormap.inverse, mask).astype(np.float64))
            cv2.waitKey(0)


if __name__ == '__main__':
    src_dst_colormap = bidict({
        (255,  0,  0): (0,0,1),
        (  0,  0,255): (0,1,0),
        (  0,  0,  0): (1,0,0)})
    dataset.generate(
        './dataset/snet285/image',
        './dataset/snet285/clean_rbk',
        './dataset/test.tfrecords',
        rbk_src_dst)
