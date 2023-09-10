from contextlib import contextmanager


@contextmanager
def safe_import():
    try:
        import os
        import sys
        ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        sys.path.append(ROOT_DIR)
        yield 
    finally:
        del ROOT_DIR, os, sys

