# YOLO26 Drone Detection — Dataset Creation & Labeling SOP

**Internship Phase:** Labeled Dataset Creation  
**Task:** Airborne Drone Object Detection  
**Labeling Tool:** Label Studio  
**Dataset Format:** YOLO (normalised bounding boxes)

---

## 1. Environment Setup

### 1.1 Label Studio Installation (Dedicated Virtual Environment)

> ⚠️ **IMPORTANT:** Never install label-studio inside the ultralytics venv — dependency conflicts will break both.

```bash
# Create a dedicated venv
python3 -m venv ~/label_studio_env

# Install label-studio inside it
~/label_studio_env/bin/pip install --upgrade pip
~/label_studio_env/bin/pip install label-studio

# Verify
~/label_studio_env/bin/label-studio version
```

### 1.2 Launching Label Studio

```bash
# Start the server (default: http://localhost:8080)
~/label_studio_env/bin/label-studio start

# With a custom port and local file serving enabled
LABEL_STUDIO_LOCAL_FILES_SERVING_ENABLED=true \
LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT=/home/claude/drone_dataset \
~/label_studio_env/bin/label-studio start --port 8080
```

---

## 2. Video Source & Frame Extraction

### 2.1 Video Selection Rationale

| Criterion | Decision |
|-----------|----------|
| **Task** | Airborne drone object detection |
| **Source** | Intel IoT DevKit sample video / self-recorded UAV footage |
| **Resolution** | 640×480 (sufficient for small object detection) |
| **Duration** | ~60 seconds |
| **Frame rate** | 10 fps extracted |
| **Total frames** | 600 |

> **Quality note:** For real deployments, collect footage under varied conditions:
> different lighting (golden hour, overcast, noon), altitudes, drone models,
> backgrounds (sky only, buildings, trees), and distances. Diversity prevents
> model overfitting to a single scenario.

### 2.2 Frame Extraction Command

```bash
# Extract at exactly 10 fps
ffmpeg -i drone_footage.mp4 \
       -vf "fps=10" \
       frames/frame_%04d.jpg \
       -q:v 2    # JPEG quality (2=highest, 31=lowest)
```

---

## 3. Dataset Split Strategy

### 3.1 Split Sizes

| Split | Count | Source Frames | Selection Strategy |
|-------|-------|---------------|--------------------|
| **train** | 100 | frames 0–499 | Every 5th frame (temporal spacing) |
| **val** | 40 | frames 500–599 | Every 2nd frame |
| **test** | 460 | Remaining | All unused frames |

**Why temporal spacing?** Consecutive video frames at 10 fps are nearly identical
(≤100ms apart). Picking every N-th frame ensures your train/val splits contain
genuinely distinct scenes rather than near-duplicate images, which would
artificially inflate validation metrics.

### 3.2 Directory Structure

```
drone_dataset/
├── video/
│   └── drone_footage.mp4
├── frames/                   ← all 600 raw frames
│   ├── frame_0001.jpg
│   └── ...
├── images/
│   ├── train/                ← 100 images
│   ├── val/                  ← 40 images
│   └── test/                 ← 460 images
├── labels/
│   ├── train/                ← 100 .txt YOLO label files
│   └── val/                  ← 40 .txt YOLO label files
├── label_studio_project/
│   ├── labeling_config.xml   ← LS interface definition
│   └── tasks_import.json     ← tasks to import into LS
├── train.txt                 ← absolute paths to train images
├── val.txt                   ← absolute paths to val images
└── drone_detection.yaml      ← YOLO dataset config
```

---

## 4. Label Studio Labeling Workflow

### 4.1 Create a New Project

1. Open `http://localhost:8080` in your browser.
2. Click **Create Project** → name it `Drone Detection`.
3. In **Labeling Setup**, switch to **Object Detection with Bounding Boxes**.
4. Paste the contents of `label_studio_project/labeling_config.xml` into the
   **Code** tab of the labeling configuration editor.
5. Click **Save**.

### 4.2 Connect Local Storage

```
Project Settings → Cloud Storage → Add Source Storage
  Type: Local files
  Absolute local path: /home/claude/drone_dataset/images/train
  File filter regex: .*\.jpg
  Toggle: [✓] Treat every bucket object as a source file
```

Repeat for the `val` directory. Enable:
```
LABEL_STUDIO_LOCAL_FILES_SERVING_ENABLED=true
```

### 4.3 Import Tasks

Alternatively, import `label_studio_project/tasks_import.json` directly:

```
Import → Upload files → tasks_import.json
```

### 4.4 Annotation Interface

The XML config (`labeling_config.xml`) provides:
- **RectangleLabels** with a single class `drone` (hotkey: `1`)
- Zoom and brightness controls for hard-to-see drones
- Optional notes field for quality flags (blur, occlusion, etc.)

**Annotation best practices:**
- Draw the box **tightly** around the drone body (rotors included)
- For partially occluded drones, annotate the **visible portion only**
- Skip frames where a drone is motion-blurred beyond recognition (use the
  Skip button — Label Studio records this)
- Zoom in (use `Ctrl+scroll` or the zoom widget) for small distant drones
- Use **Review mode** (Enterprise) or a second annotator pass for QA

### 4.5 Exporting Annotations

```
Export → YOLO format
```

Label Studio exports a ZIP containing:
```
export/
├── images/          ← symlinks (ignore — use your originals)
├── labels/
│   ├── frame_0001.txt
│   └── ...
├── classes.txt      ← one class per line
└── notes.json       ← annotator notes (if any)
```

Copy the `.txt` files into `labels/train/` and `labels/val/` respectively.

---

## 5. YOLO Label Format Reference

Each `.txt` file corresponds to one image. Each line is one bounding box:

```
<class_id> <cx> <cy> <width> <height>
```

All values are **normalised** (divided by image dimensions):

| Field | Description | Range |
|-------|-------------|-------|
| `class_id` | Integer index into `names` list | `0` = drone |
| `cx` | Bounding box centre X ÷ image width | 0.0 – 1.0 |
| `cy` | Bounding box centre Y ÷ image height | 0.0 – 1.0 |
| `width` | Box width ÷ image width | 0.0 – 1.0 |
| `height` | Box height ÷ image height | 0.0 – 1.0 |

**Example** (`labels/train/frame_0001.txt`):
```
0 0.951562 0.427083 0.028125 0.020833
0 0.012500 0.322917 0.025000 0.020833
0 0.485938 0.533333 0.034375 0.025000
```
Three drones visible in frame 1 — each on its own line, class 0.

---

## 6. Dataset YAML (drone_detection.yaml)

```yaml
path: /home/claude/drone_dataset

train: images/train
val:   images/val
test:  images/test

train_txt: /home/claude/drone_dataset/train.txt
val_txt:   /home/claude/drone_dataset/val.txt

nc: 1

names:
  0: drone
```

---

## 7. Metadata Files

### 7.1 train.txt / val.txt

Plain-text files with one absolute image path per line.
Used by some YOLO variants instead of directory paths.

```
/home/claude/drone_dataset/images/train/frame_0001.jpg
/home/claude/drone_dataset/images/train/frame_0006.jpg
...
```

### 7.2 classes.txt (Label Studio export companion)

```
drone
```

One class per line; line number = class ID.

---

## 8. Dataset Statistics

| Metric | Value |
|--------|-------|
| Total images | 600 |
| Train images | 100 |
| Val images | 40 |
| Test images | 460 |
| Train bounding boxes | 373 |
| Val bounding boxes | 145 |
| Avg boxes / image (train) | 3.7 |
| Avg boxes / image (val) | 3.6 |
| Classes | 1 (drone) |
| Image size | 640 × 480 |

---

## 9. Training with YOLO26

Once labels are complete and validated:

```bash
# Install ultralytics (separate venv — NOT the label-studio venv)
pip install ultralytics

# Train
yolo detect train \
     data=/home/claude/drone_dataset/drone_detection.yaml \
     model=yolo26n.pt \
     epochs=100 \
     imgsz=640 \
     batch=16 \
     project=runs/drone_detect \
     name=exp1
```

---

## 10. Labeling Quality Checklist

A good annotation distinguishes a skilled ML architect from an average one.
Before submitting labels, verify:

- [ ] Every drone in every image is annotated (no missed detections)
- [ ] Bounding boxes are tight — no large empty margins around drones
- [ ] Partially visible drones at image edges are still annotated
- [ ] Heavily blurred/unrecognisable drones are skipped (not guessed)
- [ ] No human-annotated boxes on background objects mistaken for drones
- [ ] Label files contain no `NaN` or out-of-range (>1.0) values
- [ ] One `.txt` file exists per image (even if empty = no drones visible)
- [ ] `train.txt` and `val.txt` match actual files on disk
- [ ] YAML `nc` matches the actual number of unique class IDs in labels

---

*Generated as part of YOLO26 Internship Program — Phase: Labeled Dataset Creation*
