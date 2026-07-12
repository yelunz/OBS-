import os
paths = {}
for i in range(1, 51):
    paths[f"live/player{i}"] = {"source": "publisher"}
yml = "rtmpAddress: :1935\nhlsAddress: :8888\nhlsSegmentDuration: 1s\nhlsSegmentCount: 7\npaths:\n"
for k, v in paths.items():
    yml += f'  "{k}": {{ source: publisher }}\n'
with open(os.path.join(os.path.dirname(__file__), "mediamtx.yml"), "w", encoding="utf-8") as f:
    f.write(yml)
print("YML generated: player1-50")