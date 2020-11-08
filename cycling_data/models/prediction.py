import numpy as np
import tensorflow as tf
import tensorflow_probability as tfp
tfd = tfp.distributions
from tensorflow import keras
from tensorflow.keras import layers

# Specify the surrogate posterior over `keras.layers.Dense` `kernel` and `bias`.
def posterior_mean_field(kernel_size, bias_size=0, dtype=None):
    n = kernel_size + bias_size
    c = np.log(np.expm1(1.))
    return tf.keras.Sequential([
        tfp.layers.VariableLayer(2 * n, dtype=dtype),
        tfp.layers.DistributionLambda(lambda t: tfd.Independent(
            tfd.Normal(loc=t[..., :n],
                       scale=1e-5 + tf.nn.softplus(c + t[..., n:])),
            reinterpreted_batch_ndims=1)),
    ])

# Specify the prior over `keras.layers.Dense` `kernel` and `bias`.
def prior_trainable(kernel_size, bias_size=0, dtype=None):
    n = kernel_size + bias_size
    return tf.keras.Sequential([
        tfp.layers.VariableLayer(n, dtype=dtype),
        tfp.layers.DistributionLambda(lambda t: tfd.Independent(
            tfd.Normal(loc=t, scale=1),
            reinterpreted_batch_ndims=1)),
    ])

def negloglik(y, p_y):
    return -p_y.log_prob(y)

def build_model(train_set_size):
    c=np.log(np.expm1(1.))

    model = keras.Sequential([
        tfp.layers.DenseVariational(12,
                                    posterior_mean_field, prior_trainable,
                                    kl_weight=train_set_size,
                                    activation='relu'),
        layers.LeakyReLU(alpha=0.3),
        tfp.layers.DenseVariational(1+1,
                                    posterior_mean_field, prior_trainable,
                                    kl_weight=train_set_size),
        tfp.layers.DistributionLambda(lambda t: tfd.Normal(
            loc=t[..., :1],
            scale=1e-5+tf.math.softplus(c * t[...,1:]))),
    ])

    optimizer = tf.optimizers.Adam(learning_rate=0.02,epsilon=0.001)

    model.compile(loss=negloglik,
                  optimizer=optimizer,
                  metrics=['mae', 'mse'])
    return model
