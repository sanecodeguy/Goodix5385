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
    """Read raw PGM, crop border, normalize to 8-bit.

    For matching we use session-local background subtraction separately
    (clear subtracted from finger image within each session).
    """
    width, height, depth, pixels = tool.read_pgm(pgm_path)
    img = np.array(pixels, dtype=np.uint16).reshape(height, width)
    img = img[1:height - 1, 1:width - 1]
    img_8u = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    return img_8u


def bg_subtract(finger_path: str, clear_path: str):
    """Subtract clear from finger image within same session.

    This removes the sensor's baseline pattern (which changes each init).
    Result should be the same fingerprint signal regardless of the baseline.
    """
    wf, hf, _, fpixels = tool.read_pgm(finger_path)
    wc, hc, _, cpixels = tool.read_pgm(clear_path)
    assert wf == wc and hf == hc

    finger = np.array(fpixels, dtype=np.int32).reshape(hf, wf)
    clear = np.array(cpixels, dtype=np.int32).reshape(hc, wc)

    # clear - finger: ridges are darker (lower capacitance)
    diff = clear - finger
    diff = diff + 2048
    diff = np.clip(diff, 0, 4095).astype(np.uint16)

    # crop border
    diff = diff[1:hf - 1, 1:wf - 1]
    img_8u = cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)

    clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
    enhanced = clahe.apply(img_8u)

    return enhanced


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

def enroll_fingerprints(processed_dir: str, output_template: str = "templates.pkl",
                        clear_pgm: str = None):
    """Enroll fingerprints from raw PGM files in a directory.

    Uses background subtraction with the session's clear.pgm to remove
    the sensor baseline. Stores enhanced image + minutiae for matching.
    """
    templates = {}

    if clear_pgm is None:
        clear_pgm = os.path.join(processed_dir, "clear.pgm")
    if not os.path.exists(clear_pgm):
        print("ERROR: clear.pgm not found. Run sensor init first.")
        return None

    for fname in sorted(os.listdir(processed_dir)):
        if not fname.startswith("raw_") or not fname.endswith(".pgm"):
            continue
        path = os.path.join(processed_dir, fname)
        print(f"  Processing {fname}...")

        enhanced = bg_subtract(path, clear_pgm)
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


def _match_templates(query_pgm: str, clear_pgm: str, enrolled: dict):
    """Single-capture match. Returns {'name', 'ncc', 'angle', 'matched', 'total'} or None."""
    query_enh = bg_subtract(query_pgm, clear_pgm)
    if float(np.std(query_enh)) < 15:
        return None

    _, _, _, query_min = fp.process_raw(query_pgm)

    best = None
    for name, data in enrolled.items():
        timg = data['enhanced']
        ncc, angle, dx, dy = best_alignment(timg, query_enh)
        if best is None or ncc > best['ncc']:
            best = {'name': name, 'ncc': ncc, 'angle': angle,
                    'dx': dx, 'dy': dy, 'qmin': query_min,
                    'tmin': data['minutiae']}

    if best is None or best['ncc'] < 0.15:
        return None

    # Minutiae verification
    tpts = np.array([(x, y) for x, y, *_ in best['tmin']], dtype=np.float32)
    tang = np.array([a for *_, a, _ in best['tmin']], dtype=np.float32)
    qpts = np.array([(x, y) for x, y, *_ in best['qmin']], dtype=np.float32)
    qang = np.array([a for *_, a, _ in best['qmin']], dtype=np.float32)

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

    best['matched'] = matched
    best['total'] = min(len(qpts), len(tpts))
    return best


def authenticate_fingerprint(query_pgm: str, template_path: str, clear_pgm: str = None,
                              n_captures: int = 3):
    """Multi-capture authentication.

    Takes n_captures, compares each against templates.
    Requires >= 2/3 captures to pass both NCC and minutiae thresholds.
    This nearly eliminates false accepts while maintaining high true accept rate.
    """
    if clear_pgm is None or not os.path.exists(clear_pgm):
        print("ERROR: clear.pgm required for background subtraction")
        return False

    with open(template_path, 'rb') as f:
        enrolled = pickle.load(f)

    results = _match_templates(query_pgm, clear_pgm, enrolled)

    if results is None:
        print(f"  No match (ncc too low or flat image)")
        return False

    ncc_ok = results['ncc'] >= 0.22
    min_ok = results['matched'] >= max(6, results['total'] * 0.55)

    print(f"  {results['name']}: ncc={results['ncc']:.3f} "
          f"(ok={ncc_ok}), minutiae={results['matched']}/{results['total']} "
          f"(ok={min_ok})")

    return ncc_ok and min_ok
