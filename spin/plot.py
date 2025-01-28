from math import ceil

import matplotlib.pyplot as plt


def create_subplots(num_itens: int, nrows: int = 4):
    fig, ax = plt.subplots(nrows, ceil(num_itens / nrows))
    ax = ax.flatten()
    [a.set_axis_off() for a in ax]
    return fig, ax
