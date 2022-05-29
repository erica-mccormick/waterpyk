
   
"""Top-level package for waterpyk."""

__author__ = """Erica McCormick"""
__email__ = "erica.elmstead@gmail.com"
__version__ = "1.1.1"

import os

def in_colab_shell():
    """Tests if the code is being executed within Google Colab. Function from geemap by Qiusheng Wu"""
    import sys

    if "google.colab" in sys.modules:
        return True
    else:
        return False

if in_colab_shell():
    default_saving_dir = '/content/drive/MyDrive'
else:
    default_saving_dir = 'data/output'