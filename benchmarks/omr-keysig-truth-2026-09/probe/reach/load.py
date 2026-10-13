import sys,pickle,os
sys.path.insert(0,'.')
from tools.omr.staged import record_io
def load(path):
    r=record_io.load_record(path); return r['record']
