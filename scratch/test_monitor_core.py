import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import monitor_core

print("Testing fetch_bgg_id for 'Flamecraft'")
bgg_id, conf = monitor_core.fetch_bgg_id("Flamecraft", source='test')
print(f"Result: {bgg_id}, {conf}")
