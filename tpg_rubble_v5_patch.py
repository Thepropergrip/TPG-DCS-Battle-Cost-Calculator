import importlib.util
import os
import sys

_REPO = os.path.dirname(os.path.abspath(__file__))
_EDM_JOBS = os.path.join(_REPO, 'edm-jobs')
if _EDM_JOBS not in sys.path:
    sys.path.insert(0, _EDM_JOBS)

_IMPL = os.path.join(_EDM_JOBS, 'tpg_rubble_v5_patch.py')
_spec = importlib.util.spec_from_file_location('_tpg_rubble_v5_patch_impl', _IMPL)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

for _name, _value in _mod.__dict__.items():
    if not _name.startswith('__'):
        globals()[_name] = _value
