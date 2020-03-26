'''
Convert old snet dset yml -> tf record dataset(src:dst map included)

It is task module: call run() to run (default) task
'''
import yaml
from bidict import bidict
import tensorflow as tf
import numpy as np
import cv2

from time import time
from nnlab.tasks import dataset
from nnlab.utils import file_utils as fu
from nnlab.utils import fp
from nnlab.data import image as im
from nnlab.expr import train

def generate_2dset():
    '''
    Generate two dataset(not 2d set).
    
    One is 285 img-mask  rbk dataset,
    Other is 285 img-mask wk dataset.

    It generate and save. Temporary implementation..
    TODO: refactor or remove it.
    '''
    # Generate dataset from old snet dataset(snet285rbk)
    old_dset_path = "dataset/snet285/indices/rbk/190421rbk200.yml"
    out_dset_path = "./dataset/snet285rbk.tfrecords"

    with open(old_dset_path) as f:
        dset = dataset.distill('old_snet', yaml.safe_load(f))

    dataset.generate(
        dset['train'], dset['valid'], dset['test'],
        dset['cmap'], out_dset_path)

    # Generate dataset from old snet dataset(snet285wk)
    old_dset_path = "dataset/snet285/indices/wk/190421wk200.yml"
    out_dset_path = "./dataset/snet285wk.tfrecords"

    with open(old_dset_path) as f:
        dset = dataset.distill('old_snet', yaml.safe_load(f))

    dataset.generate(
        dset['train'], dset['valid'], dset['test'],
        dset['cmap'], out_dset_path)

def look_and_feel_check():
    '''
    load and look dataset.
    
    TODO: Generalize using function argments
    '''
    # Read dataset
    dset = fp.go(
        "./dataset/snet285rbk.tfrecords",
        tf.data.TFRecordDataset,
        lambda d: dataset.read("old_snet", d))

    # Look and Feel check (how to load dataset)
    src_dst_colormap = dset["cmap"]
    n_train = dset["num_train"]

    s = time()
    for datum in dset["train"].shuffle(n_train).repeat(10):
        h  = datum["h"]
        w  = datum["w"]
        c  = datum["c"]
        mc = datum["mc"]
        img_tf, mask_tf = train.crop(
            tf.reshape(tf.io.decode_raw(datum["img"], tf.float32), (h,w,c)),
            tf.reshape(tf.io.decode_raw(datum["mask"], tf.float32), (h,w,mc)), 
            384)
        img, mask = img_tf.numpy(), mask_tf.numpy()
        from nnlab.utils import image_utils as iu
        print(iu.unique_colors(img))
        print(iu.unique_colors(mask))

        # Look and Feel check!
        mapped_mask = im.map_colors(src_dst_colormap.inverse, mask)
        cv2.imshow("i", img)
        cv2.imshow("m", mapped_mask)
        cv2.waitKey(0)
    t = time()

    print("train time:", t - s)

def run(): generate_2dset(); look_and_feel_check()
