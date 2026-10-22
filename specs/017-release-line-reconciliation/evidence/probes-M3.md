# Probes (T017), 2026-10-21T17:44:49Z, Python 3.11.9

Run as `env -u CUEMS_CONF_PATH PYTHONPATH=<arm>/src $PY -P tools/probes.py --fixtures tests/data/rc17`. Use `-P`, not `-I`: `-I` ignores `PYTHONPATH`, so it measures whichever library is installed, not the arm. The `# arm` line proves which library each run loaded.

## arm 5e4c637 (/tmp/claude-1000/-disk-Projects-StageLab-cuems-utils/5ed4cc43-5e7a-4f7f-b4f5-bd626a72db7f/scratchpad/wt-a)
```
# arm: cuemsutils 0.1.1 at /tmp/claude-1000/-disk-Projects-StageLab-cuems-utils/5ed4cc43-5e7a-4f7f-b4f5-bd626a72db7f/scratchpad/wt-a/src/cuemsutils
  (stop_project.xml: reshape exit 1, convert exit 1)
S-1': REFUSED SchemaError: /tmp/tmp9xvijjgz/stop_project.xml is not a valid script document: script document /tmp/tmp9xvijjgz/stop_project.xml is in the pre-013 device shape (<AudioCue>/<
  (stop_control.xml: reshape exit 0, convert exit 0)
control: CLEAN
  (stop_control.xml: reshape exit 0, convert exit 0)
S-1: REFUSED SchemaError: [T1] XsdEnumerationFacets at action_type: value must be one of ['play', 'pause', 'stop', 'load', 'unload', 'enable', 'disable', 'fade_action', 'wait', 'go_to', 
S-2: REFUSED ValueError: action_target is required
  (stop_control.xml: reshape exit 0, convert exit 0)
X-4: VideoCue: get={'pixel_width': 1920, 'pixel_height': 1080, 'file_size': 107374182400, 'file_md5': 'd41d8cd98f00b204e9800998ecf8427e'} attr==get:True in=['pixel_width', 'pixel_height', 'file_size', 'file_md5'] wire_has=['pixel_width', 'pixel_height', 'file_size', 'file_md5'] | AudioCue: get={'pixel_width': None, 'pixel_height': None, 'file_size': None, 'file_md5': None} attr==get:True in=[] wire_has=[]
```

## arm 97ee1f9 (/disk/Projects/StageLab/cuems-utils)
```
# arm: cuemsutils 0.1.1 at /disk/Projects/StageLab/cuems-utils/src/cuemsutils
  (stop_project.xml: reshape exit 0, convert exit 0)
S-1': REFUSED ValidationError: [T2] action_target_required at 3d8c6b3a-4e5f-4071-8c1d-2e3f4a5b6c72/action_target: action_target is required
  (stop_control.xml: reshape exit 0, convert exit 0)
control: CLEAN
  (stop_control.xml: reshape exit 0, convert exit 0)
S-1: REFUSED ValidationError: [T2] action_target_required at 3d8c6b3a-4e5f-4071-8c1d-2e3f4a5b6c72/action_target: action_target is required
S-2: REFUSED ValueError: action_target is required
  (stop_control.xml: reshape exit 0, convert exit 0)
X-4: VideoCue: get={'pixel_width': 1920, 'pixel_height': 1080, 'file_size': 107374182400, 'file_md5': 'd41d8cd98f00b204e9800998ecf8427e'} attr==get:True in=['pixel_width', 'pixel_height', 'file_size', 'file_md5'] wire_has=['pixel_width', 'pixel_height', 'file_size', 'file_md5'] | AudioCue: get={'pixel_width': None, 'pixel_height': None, 'file_size': None, 'file_md5': None} attr==get:True in=[] wire_has=[]
```
