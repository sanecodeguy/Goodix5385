"""Fingerprint enrollment and authentication.

Two-stage matching:
  1. Primary: Phase correlation alignment + Normalized Cross-Correlation
  2. Secondary: Minutiae-based Hough matching (rejects false positives)

Enhancement: CLAHE only (no Gabor, to avoid session-dependent artifacts)
"""
import os
import pickle
import cv2
import numpy as np
from . import tool
from . import fingerprint as fp


# ─── Image enhancement ───────────────────────────────────────────────────────

def enhance_raw(pgm_path: str):
    """Read raw PGM, crop border, normalize, CLAHE, return 8-bit."""
    width, height, depth, pixels = tool.read_pgm(pgm_path)
    img = np.array(pixels, dtype=np.uint16).reshape(height, width)
    img = img[1:height - 1, 1:width - 1]
    img_8u = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(img_8u)
    blurred = cv2.GaussianBlur(enhanced, (3, 3), 0.5)
    return blurred


# ─── Phase correlation alignment ────────────────────────────────────────────

def phase_align(template, query):
    """Find best translation between query and template using phase correlation.

    Returns (dx, dy, ncc_score) where dx,dy is the translation to apply
    to query to align with template, and ncc_score is the best NCC after
    alignment.
    """
    th, tw = template.shape
    qh, qw = query.shape
    if th == 0 or tw == 0 or qh == 0 or qw == 0:
        return 0, 0, 0.0

    max_h, max_w = max(th, qh), max(tw, qw)
    size = 1
    while size < max(max_h, max_w):
        size *= 2

    tf = np.float32(template)
    qf = np.float32(query)
    tf_pad = np.zeros((size, size), dtype=np.float32)
    qf_pad = np.zeros((size, size), dtype=np.float32)
    tf_pad[:th, :tw] = tf
    qf_pad[:qh, :qw] = qf

    tf_pad -= np.mean(tf_pad)
    qf_pad -= np.mean(qf_pad)

    Tf = np.fft.fft2(tf_pad)
    Qf = np.fft.fft2(qf_pad)
    cross = Tf * np.conj(Qf)
    cross_norm = cross / (np.abs(cross) + 1e-10)
    phase = np.fft.ifft2(cross_norm)
    phase = np.fft.fftshift(phase)
    phase_real = np.real(phase)

    max_idx = np.unravel_index(np.argmax(phase_real), phase_real.shape)
    dy = max_idx[0] - size // 2
    dx = max_idx[1] - size // 2

    m = np.array([[1, 0, dx], [0, 1, dy]], dtype=np.float32)
    aligned = cv2.warpAffine(query, m, (tw, th))

    tn = cv2.normalize(template.astype(np.float32), None, 0, 1, cv2.NORM_MINMAX)
    an = cv2.normalize(aligned.astype(np.float32), None, 0, 1, cv2.NORM_MINMAX)
    tm = tn - np.mean(tn)
    am = an - np.mean(an)
    num = np.sum(tm * am)
    den = np.sqrt(np.sum(tm ** 2) * np.sum(am ** 2))
    ncc = float(num / den) if den > 1e-6 else 0.0

    return dx, dy, ncc


# ─── Rotation-tolerant alignment ────────────────────────────────────────────

def best_alignment(template, query):
    """Search over rotations and translations for best NCC alignment.

    Brute-force over [-20, 20]° in 5° steps, with phase correlation for
    translation at each rotation.
    """
    best = {'ncc': -1, 'angle': 0, 'dx': 0, 'dy': 0}
    th, tw = template.shape
    center = (tw / 2, th / 2)

    for angle in range(-20, 21, 5):
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(query, M, (tw, th),
                                 flags=cv2.INTER_CUBIC,
                                 borderMode=cv2.BORDER_REFLECT)

        dx, dy, ncc = phase_align(template, rotated)
        if ncc > best['ncc']:
            best = {'ncc': ncc, 'angle': angle, 'dx': dx, 'dy': dy}

    return best['ncc'], best['angle'], best['dx'], best['dy']


def apply_transform(query, angle, dx, dy, size):
    """Apply rotation + translation to align query with template."""
    center = (size[1] / 2, size[0] / 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    M[0, 2] += dx
    M[1, 2] += dy
    return cv2.warpAffine(query, M, (size[1], size[0]),
                          flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REFLECT)


# ─── Template management ────────────────────────────────────────────────────

def enroll_fingerprints(processed_dir: str, output_template: str = "templates.pkl"):
    """Enroll fingerprints from raw PGM files in a directory.

    Stores both enhanced image and minutiae for two-stage matching.
    """
    templates = {}

    for fname in sorted(os.listdir(processed_dir)):
        if not fname.startswith("raw_") or not fname.endswith(".pgm"):
            continue
        path = os.path.join(processed_dir, fname)
        print(f"  Processing {fname}...")

        enhanced = enhance_raw(path)
        _, _, _, minutiae = fp.process_raw(path)

        if len(minutiae) < 5:
            print(f"    Only {len(minutiae)} minutiae, skipping")
            continue

        templates[fname] = {
            'enhanced': enhanced,
            'minutiae': minutiae,
        }
        print(f"    enhanced={enhanced.shape}, minutiae={len(minutiae)}")

    if not templates:
        print("ERROR: No valid templates found!")
        return None

    template_path = os.path.join(processed_dir, output_template)
    with open(template_path, 'wb') as f:
        pickle.dump(templates, f)
    print(f"Saved {len(templates)} templates to {template_path}")
    return template_path


def authenticate_fingerprint(query_pgm: str, template_path: str, _clear_pgm: str = None):
    """Two-stage authentication with brute-force rotation search + NCC + minutiae."""
    query_enh = enhance_raw(query_pgm)
    if float(np.std(query_enh)) < 15:
        print(f"  Query too flat, rejecting")
        return False

    _, _, _, query_min = fp.process_raw(query_pgm)
    print(f"  Query: {query_enh.shape}, {len(query_min)} minutiae")

    with open(template_path, 'rb') as f:
        enrolled = pickle.load(f)

    best = {'name': None, 'ncc': -1, 'angle': 0, 'dx': 0, 'dy': 0}

    for name, data in enrolled.items():
        timg = data['enhanced']
        ncc, angle, dx, dy = best_alignment(timg, query_enh)
        if ncc > best['ncc']:
            best = {'name': name, 'ncc': ncc, 'angle': angle,
                    'dx': dx, 'dy': dy}

    print(f"  Best: {best['name']} "
          f"(ncc={best['ncc']:.3f}, rot={best['angle']}°, "
          f"dx={best['dx']}, dy={best['dy']})")

    ncc_threshold = 0.20
    if best['ncc'] < ncc_threshold:
        print(f"  NCC too low (< {ncc_threshold}), rejecting")
        return False

    # Stage 2: Minutiae verification (apply same rotation/translation)
    best_data = enrolled[best['name']]
    tpts = np.array([(x, y) for x, y, *_ in best_data['minutiae']], dtype=np.float32)
    tang = np.array([a for *_, a, _ in best_data['minutiae']], dtype=np.float32)
    qpts = np.array([(x, y) for x, y, *_ in query_min], dtype=np.float32)
    qang = np.array([a for *_, a, _ in query_min], dtype=np.float32)

    rad = np.radians(best['angle'])
    ca, sa = np.cos(rad), np.sin(rad)
    q_aligned = np.column_stack([
        qpts[:, 0] * ca - qpts[:, 1] * sa + best['dx'],
        qpts[:, 0] * sa + qpts[:, 1] * ca + best['dy']
    ])
    q_ang_aligned = qang + best['angle']

    matched = 0
    for qi in range(len(q_aligned)):
        for ti in range(len(tpts)):
            d = np.linalg.norm(q_aligned[qi] - tpts[ti])
            if d < 8:
                da = abs(q_ang_aligned[qi] - tang[ti])
                da = min(da, 360 - da)
                if da < 30:
                    matched += 1
                    break

    print(f"  Minutiae matched: {matched}/{min(len(query_min), len(tpts))}")

    min_minutiae = max(4, len(tpts) // 6)
    if matched < min_minutiae:
        print(f"  Too few minutiae (< {min_minutiae}), rejecting")
        return False

    return True
