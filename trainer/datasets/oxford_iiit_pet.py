import tensorflow as tf
import tensorflow_datasets as tfds
from trainer.datasets.data_utils import random_jitter, normalize, get_LR


def oxford_iiit_pet_dataset(train_type='train',
                            size=(224, 224, 3),
                            downsampling_factor=4,
                            batch_size=32):
    """Returns a `tf.data.Dataset:(lr, hr)` and the number of elements
    """
    count = {
        'test': 3669,
        'train': 3680,
    }

    data = tfds.load('oxford_iiit_pet')
    dataset = data[train_type]

    if train_type == 'train':
        dataset = dataset.map(lambda x: random_jitter(x['image'], size),
                              num_parallel_calls=tf.data.experimental.AUTOTUNE)
        dataset = dataset.map(normalize,
                              num_parallel_calls=tf.data.experimental.AUTOTUNE)
    elif train_type == 'test':
        dataset = dataset.map(
            lambda x: tf.image.resize(x['image'], [size[0], size[1]]),
            num_parallel_calls=tf.data.experimental.AUTOTUNE)
        dataset = dataset.map(normalize,
                              num_parallel_calls=tf.data.experimental.AUTOTUNE)

    dataset = dataset.repeat().batch(batch_size).prefetch(16)
    dataset = dataset.map(lambda x:
                          (get_LR(x, downsampling_factor), normalize(x)),
                          num_parallel_calls=tf.data.experimental.AUTOTUNE)
    dataset = dataset.apply(tf.data.experimental.prefetch_to_device('/gpu:0'))
    return dataset, count[train_type]


def oxford_iiit_pet_dataset_D(train_type='train',
                              size=(224, 224, 3),
                              downsampling_factor=4,
                              batch_size=32):
    """Returns a `tf.data.Dataset:(image, label)` and the number of elements"""
    count = {
        'test': 3669,
        'train': 3680,
    }

    # load data
    data = tfds.load('oxford_iiit_pet')
    dataset = data[train_type]

    # augment/resize, normalize
    if train_type == 'train':
        dataset = dataset.map(lambda x: random_jitter(x['image'], size),
                              num_parallel_calls=tf.data.experimental.AUTOTUNE)
        dataset = dataset.map(normalize,
                              num_parallel_calls=tf.data.experimental.AUTOTUNE)
    elif train_type == 'test':
        dataset = dataset.map(
            lambda x: tf.image.resize(x['image'], [size[0], size[1]]),
            num_parallel_calls=tf.data.experimental.AUTOTUNE)
        dataset = dataset.map(normalize,
                              num_parallel_calls=tf.data.experimental.AUTOTUNE)

    # downsampling
    dataset_lr = dataset.map(lambda x: get_LR(x, downsampling_factor),
                             num_parallel_calls=tf.data.experimental.AUTOTUNE)
    # label bicubic data
    dataset_bicubic = dataset_lr.map(lambda x: (tf.image.resize(
        x, [size[0], size[1]], method=tf.image.ResizeMethod.BICUBIC), 0))
    # label hr data
    dataset = dataset.map(lambda x: (x, 1))

    # interleaves elements from datasets at random
    dataset = tf.data.experimental.sample_from_datasets(
        [dataset, dataset_bicubic])
    dataset = dataset.repeat().batch(batch_size).prefetch(8)

    dataset = dataset.apply(tf.data.experimental.prefetch_to_device('/gpu:0'))
    return dataset, count[train_type] * 2
