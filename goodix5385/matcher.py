"""Fingerprint enrollment and authentication with composite templates.

Uses background subtraction (within session) for calibration invariance,
then builds composite templates from multiple enrollment captures
(fusing minutiae into a single reference frame), matching what Windows does.

Matching: query image → bg_subtract → NCC vs mosaic + minutiae vs composite.
"""
import os
import pickle
import cv2
import numpy as np
from . import tool
from . import fingerprint as fp


# ─── Background subtraction + unified minutiae extraction ───────────────────

def bg_subtract_and_extract(finger_path: str, clear_path: str):
    """Unified pipeline: bg_subtract → enhance → NCC image + minutiae.

    1. Session-local background subtraction (clear - finger)
    2. CLAHE for contrast
    3. Gabor filter for ridge enhancement (same as fingerprint module)
    4. Binarize → skeletonize → minutiae extraction
    5. Returns (ncc_image, minutiae_list)
    """
    wf, hf, _, fpix = tool.read_pgm(finger_path)
    wc, hc, _, cpix = tool.read_pgm(clear_path)
    assert wf == wc and hf == hc

    finger = np.array(fpix, dtype=np.int32).reshape(hf, wf)
    clear = np.array(cpix, dtype=np.int32).reshape(hc, wc)
    diff = clear - finger + 2048
    diff = np.clip(diff, 0, 4095).astype(np.uint16)
    diff = diff[1:hf - 1, 1:wf - 1]
    img_8u = cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    clahe_img = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8)).apply(img_8u)

    ncc_img = clahe_img.copy()

    orient, coh = fp.orientation_field(clahe_img, block_size=7, smooth_sigma=2.0)
    gabor = fp.gabor_enhance(clahe_img, orient, coh)
    binary = fp.binarize(gabor, block_size=17, c=4)
    skeleton = fp.skeletonize(binary)
    minutiae = fp.extract_minutiae(skeleton, min_dist=8, border=5)

    return ncc_img, minutiae


# ─── Alignment ──────────────────────────────────────────────────────────────

def _phase_corr(template, query):
    """Phase correlation to find translation between two equal-sized images."""
    size = 1
    while size < max(*template.shape):
        size *= 2
    tf = np.float32(template) - np.mean(template)
    qf = np.float32(query) - np.mean(query)
    tp = np.zeros((size, size), dtype=np.float32)
    qp = np.zeros((size, size), dtype=np.float32)
    tp[:template.shape[0], :template.shape[1]] = tf
    qp[:query.shape[0], :query.shape[1]] = qf
    cross = np.fft.fft2(tp) * np.conj(np.fft.fft2(qp))
    phase = np.fft.fftshift(np.real(np.fft.ifft2(cross / (np.abs(cross) + 1e-10))))
    idx = np.unravel_index(np.argmax(phase), phase.shape)
    dy = idx[0] - size // 2
    dx = idx[1] - size // 2
    return dx, dy


def best_align(ref, query):
    """Find best rotation+translation to align query to ref. Returns (ncc, angle, dx, dy)."""
    best = {'ncc': -1, 'angle': 0, 'dx': 0, 'dy': 0}
    th, tw = ref.shape
    center = (tw / 2, th / 2)
    for angle in range(-15, 16, 5):
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(query, M, (tw, th),
                                 flags=cv2.INTER_CUBIC,
                                 borderMode=cv2.BORDER_REFLECT)
        dx, dy = _phase_corr(ref, rotated)
        aligned = np.roll(rotated, (-dy, -dx), axis=(0, 1))
        tn = ref.astype(np.float32) - np.mean(ref)
        an = aligned.astype(np.float32) - np.mean(aligned)
        ncc = np.sum(tn * an) / (np.sqrt(np.sum(tn ** 2) * np.sum(an ** 2)) + 1e-10)
        if ncc > best['ncc']:
            best = {'ncc': ncc, 'angle': angle, 'dx': dx, 'dy': dy}
    return best['ncc'], best['angle'], best['dx'], best['dy']


# ─── Composite template building ────────────────────────────────────────────

def _merge_minutiae(minutiae_list, angles, dxs, dys, dist_thresh=5):
    """Merge minutiae from multiple aligned captures into one set."""
    all_pts = []
    for mins, angle, dx, dy in zip(minutiae_list, angles, dxs, dys):
        rad = np.radians(angle)
        ca, sa = np.cos(rad), np.sin(rad)
        for x, y, a, mtype in mins:
            rx = x * ca - y * sa + dx
            ry = x * sa + y * ca + dy
            ra = (a + angle) % 360
            all_pts.append((rx, ry, ra, mtype))

    merged = []
    for pt in all_pts:
        x, y, a, mtype = pt
        dup = False
        for mx, my, *_ in merged:
            if abs(x - mx) + abs(y - my) < dist_thresh:
                dup = True
                break
        if not dup:
            merged.append(pt)
    return merged


def _mosaic_image(images, angles, dxs, dys):
    """Blend multiple aligned images into a mosaic."""
    ref = images[0].astype(np.float32)
    th, tw = ref.shape
    center = (tw / 2, th / 2)
    acc = ref.copy()
    count = np.ones((th, tw), dtype=np.float32)

    for img, angle, dx, dy in zip(images[1:], angles[1:], dxs[1:], dys[1:]):
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(img.astype(np.float32), M, (tw, th),
                                 flags=cv2.INTER_CUBIC,
                                 borderMode=cv2.BORDER_REFLECT)
        aligned = np.roll(rotated, (-dy, -dx), axis=(0, 1))
        mask = np.ones((th, tw), dtype=np.float32)
        acc += aligned
        count += mask

    mosaic = acc / count
    lo, hi = mosaic.min(), mosaic.max()
    if hi > lo:
        mosaic = (mosaic - lo) / (hi - lo) * 255
    return np.clip(mosaic, 0, 255).astype(np.uint8)


# ─── Template management ────────────────────────────────────────────────────

def enroll_fingerprints(processed_dir: str, output_template: str = "templates.pkl",
                        clear_pgm: str = None):
    """Build a composite template from all raw captures in the directory."""
    if clear_pgm is None:
        clear_pgm = os.path.join(processed_dir, "clear.pgm")
    if not os.path.exists(clear_pgm):
        print("ERROR: clear.pgm not found")
        return None

    raws = sorted([f for f in os.listdir(processed_dir)
                   if f.startswith("raw_") and f.endswith(".pgm")])
    if len(raws) < 2:
        print("ERROR: need at least 2 raw captures")
        return None

    images, minutiae_list, angles_list, dxs_list, dys_list = [], [], [], [], []

    for fname in raws:
        path = os.path.join(processed_dir, fname)
        enhanced, mins = bg_subtract_and_extract(path, clear_pgm)
        images.append(enhanced)
        minutiae_list.append(mins)
        print(f"  {fname}: enhanced={enhanced.shape}, {len(mins)} minutiae")

    # Align all to the first image
    angles_list = [0.0]
    dxs_list = [0.0]
    dys_list = [0.0]
    for i in range(1, len(images)):
        ncc, angle, dx, dy = best_align(images[0], images[i])
        angles_list.append(float(angle))
        dxs_list.append(float(dx))
        dys_list.append(float(dy))
        print(f"  Aligned {raws[i]} → {raws[0]}: ncc={ncc:.3f}, "
              f"rot={angle}°, dx={dx}, dy={dy}")

    # Merge
    merged = _merge_minutiae(minutiae_list, angles_list, dxs_list, dys_list)
    mosaic = _mosaic_image(images, angles_list, dxs_list, dys_list)
    print(f"  Composite: {len(merged)} minutiae (from {sum(len(m) for m in minutiae_list)} total)")

    template = {
        'mosaic': mosaic,
        'minutiae': merged,
        'individual': images,
    }

    template_path = os.path.join(processed_dir, output_template)
    with open(template_path, 'wb') as f:
        pickle.dump(template, f)
    print(f"Saved composite template ({len(merged)} merged minutiae) to {template_path}")
    return template_path


def authenticate_fingerprint(query_pgm: str, template_path: str, clear_pgm: str = None):
    """Match a query against a composite template (NCC + minutiae)."""
    if not clear_pgm or not os.path.exists(clear_pgm):
        print("ERROR: clear.pgm required")
        return False

    with open(template_path, 'rb') as f:
        template = pickle.load(f)

    query_enh, query_mins = bg_subtract_and_extract(query_pgm, clear_pgm)
    if float(np.std(query_enh)) < 15:
        print("  Query too flat, rejecting")
        return False

    print(f"  Query: {query_enh.shape}, {len(query_mins)} minutiae")

    # NCC against mosaic
    ncc, angle, dx, dy = best_align(template['mosaic'], query_enh)
    print(f"  vs mosaic: ncc={ncc:.3f}, rot={angle}°, dx={dx}, dy={dy}")

    # Minutiae matching
    tmins = template['minutiae']
    tpts = np.array([(x, y) for x, y, *_ in tmins], dtype=np.float32)
    tang = np.array([a for *_, a, _ in tmins], dtype=np.float32)
    qpts = np.array([(x, y) for x, y, *_ in query_mins], dtype=np.float32)
    qang = np.array([a for *_, a, _ in query_mins], dtype=np.float32)

    rad = np.radians(angle)
    ca, sa = np.cos(rad), np.sin(rad)
    q_aligned = qpts @ np.array([[ca, -sa], [sa, ca]]) + np.array([dx, dy])
    q_ang_aligned = qang + angle

    matched = 0
    for qi in range(len(q_aligned)):
        for ti in range(len(tpts)):
            if np.linalg.norm(q_aligned[qi] - tpts[ti]) < 8:
                da = abs(q_ang_aligned[qi] - tang[ti])
                if min(da, 360 - da) < 30:
                    matched += 1
                    break

    ncc_ok = ncc >= 0.20
    min_ok = matched >= max(6, len(tpts) * 0.12)

    print(f"  Matched minutiae: {matched}/{len(tpts)} (need >= {max(6, len(tpts) * 0.12):.0f})")
    print(f"  NCC ok={ncc_ok}, Minutiae ok={min_ok}")

    return ncc_ok and min_ok
