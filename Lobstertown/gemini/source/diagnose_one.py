from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from bake_r12 import asset
from rebake_specs import make
a=next(a for a in make("Z2B") if a["name"]=="NA_PdDRapportTourelleAngleBLeftCorner_L1_2x5")
asset(Path(__file__).resolve().parent,a,True)
