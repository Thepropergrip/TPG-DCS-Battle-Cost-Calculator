import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import tpg_rubble_v5_patch as V5
V5.apply()
from tpg_rubble_common import build
from tpg_rubble_quality_pass import quality_pass
build('intact',0)
quality_pass('intact',0)
V5.post_quality_pass('intact',0)
