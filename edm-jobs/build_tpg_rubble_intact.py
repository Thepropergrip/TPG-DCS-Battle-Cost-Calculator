import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from tpg_rubble_common import build
from tpg_rubble_quality_pass import quality_pass
build('intact',2)
quality_pass('intact',2)
