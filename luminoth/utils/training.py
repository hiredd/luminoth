import tensorflow as tf

from luminoth.utils.vars import variable_summaries
from luminoth.utils.config import REPLACE_KEY


OPTIMIZERS = {
    'adam': tf.train.AdamOptimizer,
    'momentum': tf.train.MomentumOptimizer,
    'gradient_descent': tf.train.GradientDescentOptimizer,
    'rmsprop': tf.train.RMSPropOptimizer,
}

LEARNING_RATE_DECAY_METHODS = {
    'polynomial_decay': tf.train.polynomial_decay,
    'piecewise_constant': tf.train.piecewise_constant,
    'exponential_decay': tf.train.exponential_decay,
}


def get_learning_rate(train_config, global_step=None):
    """
    Get learning rate from train config.

    TODO: Better config usage.

    Returns:
        learning_rate: TensorFlow variable.

    Raises:
        ValueError: When the method used is not available.
    """
    lr_config = train_config.learning_rate.copy()
    decay_method = lr_config.pop('decay_method', None)

    if not decay_method or decay_method == 'none':
        return lr_config.get('value') or lr_config.get('learning_rate')

    if decay_method not in LEARNING_RATE_DECAY_METHODS:
        raise ValueError('Invalid learning_rate method "{}"'.format(
            decay_method
        ))

    if decay_method == 'piecewise_constant':
        lr_config['x'] = global_step
    else:
        lr_config['global_step'] = global_step

    # boundaries, when used, must be the same type as global_step (int64).
    if 'boundaries' in lr_config:
        lr_config['boundaries'] = [
            tf.cast(b, tf.int64) for b in lr_config['boundaries']
        ]

    decay_function = LEARNING_RATE_DECAY_METHODS[decay_method]

    # Delete the '_replace' key if it exists.
    lr_config.pop(REPLACE_KEY, None)
    learning_rate = decay_function(
        **lr_config
    )

    # if decay_method == 'piecewise_constant':
    #     learning_rate = tf.train.piecewise_constant(
    #         global_step, boundaries=[
    #             tf.cast(train_config.learning_rate_decay, tf.int64), ],
    #         values=[
    #             train_config.initial_learning_rate,
    #             train_config.initial_learning_rate * 0.1
    #         ], name='learning_rate_piecewise_constant'
    #     )

    # elif decay_method == 'exponential_decay':
    #     learning_rate = tf.train.exponential_decay(
    #         learning_rate=train_config.initial_learning_rate,
    #         global_step=global_step,
    #         decay_steps=train_config.learning_rate_decay, decay_rate=0.96,
    #         staircase=True, name='learning_rate_with_decay'
    #     )

    tf.summary.scalar('losses/learning_rate', learning_rate)

    return learning_rate


def get_optimizer(train_config, global_step=None):
    """
    Get optimizer from train config.

    Raises:
        ValueError: When the optimizer type or learning_rate method are not
            valid.
    """
    learning_rate = get_learning_rate(train_config, global_step)
    optimizer_config = train_config.optimizer.copy()
    optimizer_type = optimizer_config.pop('type')
    if optimizer_type not in OPTIMIZERS:
        raise ValueError(
            'Invalid optimizer type "{}"'.format(optimizer_type)
        )

    optimizer_cls = OPTIMIZERS[optimizer_type]
    # Delete the '_replace' key if it exists.
    optimizer_config.pop(REPLACE_KEY, None)
    return optimizer_cls(learning_rate, **optimizer_config)


def clip_gradients_by_norm(grads_and_vars, add_to_summary=True):
    if add_to_summary:
        for grad, var in grads_and_vars:
            if grad is not None:
                variable_summaries(grad, 'grad/{}'.format(var.name[:-2]))

    # Clip by norm. Grad can be null when not training some modules.
    with tf.name_scope('clip_gradients_by_norm'):
        grads_and_vars = [
            (
                tf.check_numerics(
                    tf.clip_by_norm(gv[0], 10.),
                    'Invalid gradient'
                ), gv[1]
            )
            if gv[0] is not None else gv
            for gv in grads_and_vars
        ]

    if add_to_summary:
        for grad, var in grads_and_vars:
            if grad is not None:
                variable_summaries(
                    grad, 'clipped_grad/{}'.format(var.name[:-2]))

    return grads_and_vars
