"""Full fingerprint pipeline: enhancement → minutiae → matching.

Implements the standard academic approach used by Windows Biometric Framework:
  Normalize → Orientation field → Gabor filter bank → Binarize → Skeletonize → Minutiae → Hough match
"""
import cv2
import numpy as np
from . import tool


# ─── Stage 1: Normalize ──────────────────────────────────────────────────────

def normalize(img, target_mean=128, target_var=128):
    img_f = np.float32(img)
    m = np.mean(img_f)
    v = np.var(img_f) + 1e-6
    out = np.where(img_f > m,
                   target_mean + np.sqrt(target_var * (img_f - m) ** 2 / v),
                   target_mean - np.sqrt(target_var * (img_f - m) ** 2 / v))
    return np.clip(out, 0, 255).astype(np.uint8)


# ─── Stage 2: Orientation field ──────────────────────────────────────────────

def orientation_field(img, block_size=7, smooth_sigma=2.0):
    h, w = img.shape
    dy = cv2.Sobel(img, cv2.CV_32F, 0, 1, ksize=3)
    dx = cv2.Sobel(img, cv2.CV_32F, 1, 0, ksize=3)

    Gxx = dx * dx
    Gyy = dy * dy
    Gxy = dx * dy

    Gxx = cv2.GaussianBlur(Gxx, (block_size, block_size), smooth_sigma)
    Gyy = cv2.GaussianBlur(Gyy, (block_size, block_size), smooth_sigma)
    Gxy = cv2.GaussianBlur(Gxy, (block_size, block_size), smooth_sigma)

    theta = 0.5 * np.arctan2(2 * Gxy, Gxx - Gyy)
    coherency = np.sqrt((Gxx - Gyy) ** 2 + 4 * Gxy ** 2) / (Gxx + Gyy + 1e-6)

    return theta, coherency


# ─── Stage 3: Gabor filter bank ──────────────────────────────────────────────

_N_GABOR = 8
_gabor_kernels = None


def _get_gabor_kernels(k_size=11, sigma=3.5, gamma=0.8, freq=0.09):
    global _gabor_kernels
    if _gabor_kernels is not None:
        return _gabor_kernels
    _gabor_kernels = [
        cv2.getGaborKernel((k_size, k_size), sigma, i * np.pi / _N_GABOR,
                           1.0 / freq, gamma, 0, ktype=cv2.CV_32F)
        for i in range(_N_GABOR)
    ]
    return _gabor_kernels


def gabor_enhance(img, orient, coherency=None):
    """Apply oriented Gabor filter bank and blend per-pixel.

    Pre-computes N_GABOR kernels, applies each as full-image convolution,
    then per-pixel blends the two nearest orientations based on the
    orientation field.
    """
    kernels = _get_gabor_kernels()
    img_f = np.float32(img)

    responses = np.zeros((img.shape[0], img.shape[1], _N_GABOR), dtype=np.float32)
    for i, k in enumerate(kernels):
        responses[:, :, i] = cv2.filter2D(img_f, cv2.CV_32F, k)

    theta = np.mod(orient, np.pi)
    idx_f = theta / np.pi * _N_GABOR
    i0 = idx_f.astype(np.int32) % _N_GABOR
    i1 = (i0 + 1) % _N_GABOR
    frac = idx_f - i0.astype(np.float32)

    h, w = img.shape
    r0 = responses[np.arange(h)[:, None], np.arange(w)[None, :], i0]
    r1 = responses[np.arange(h)[:, None], np.arange(w)[None, :], i1]
    enhanced = r0 * (1 - frac) + r1 * frac

    if coherency is not None:
        enhanced = np.where(coherency > 0.1, enhanced, img_f)

    lo, hi = enhanced.min(), enhanced.max()
    if hi > lo:
        enhanced = (enhanced - lo) / (hi - lo) * 255.0
    return np.clip(enhanced, 0, 255).astype(np.uint8)


# ─── Stage 4: Binarize ───────────────────────────────────────────────────────

def binarize(img, block_size=17, c=4):
    return cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 cv2.THRESH_BINARY, block_size, c)


# ─── Stage 5: Skeletonize ────────────────────────────────────────────────────

def skeletonize(binary):
    """Zhang-Suen fast thinning algorithm."""
    temp = (binary > 0).astype(np.uint8)
    h, w = temp.shape
    while True:
        changed = False
        for sub_iter in range(2):
            marked = np.zeros_like(temp, dtype=bool)
            for y in range(1, h - 1):
                row = temp[y]
                row_up = temp[y - 1]
                row_dn = temp[y + 1]
                for x in range(1, w - 1):
                    if row[x] == 0:
                        continue
                    p = [row_up[x], row_up[x+1], row[x+1],
                         row_dn[x+1], row_dn[x], row_dn[x-1],
                         row[x-1], row_up[x-1]]
                    B = sum(p)
                    if B < 2 or B > 6:
                        continue
                    A = sum(1 for i in range(8) if p[i] == 0 and p[(i+1) % 8] == 1)
                    if A != 1:
                        continue
                    if sub_iter == 0:
                        if p[0] * p[2] * p[4] == 0 and p[2] * p[4] * p[6] == 0:
                            marked[y, x] = True
                    else:
                        if p[0] * p[2] * p[6] == 0 and p[0] * p[4] * p[6] == 0:
                            marked[y, x] = True
            if np.any(marked):
                temp[marked] = 0
                changed = True
        if not changed:
            break
    return (temp * 255).astype(np.uint8)


# ─── Stage 6: Minutiae extraction ────────────────────────────────────────────

def extract_minutiae(skeleton, min_dist=6, border=4):
    """Crossing-number minutiae extraction with post-processing."""
    h, w = skeleton.shape
    cn_map = np.zeros((h, w), dtype=np.int32)

    for y in range(1, h - 1):
        for x in range(1, w - 1):
            if skeleton[y, x] == 0:
                continue
            p = [skeleton[y-1, x], skeleton[y-1, x+1], skeleton[y, x+1],
                 skeleton[y+1, x+1], skeleton[y+1, x], skeleton[y+1, x-1],
                 skeleton[y, x-1], skeleton[y-1, x-1]]
            p = [int(v) // 255 for v in p]
            cn = sum(abs(p[i] - p[(i + 1) % 8]) for i in range(8)) // 2
            cn_map[y, x] = cn

    minutiae = []
    for y in range(border, h - border):
        for x in range(border, w - border):
            cn = cn_map[y, x]
            if cn not in (1, 3):
                continue

            mtype = 'ending' if cn == 1 else 'bifurcation'

            angle = 0.0
            if cn == 1:
                p2 = [int(skeleton[y-1, x]) // 255,
                      int(skeleton[y-1, x+1]) // 255,
                      int(skeleton[y, x+1]) // 255,
                      int(skeleton[y+1, x+1]) // 255,
                      int(skeleton[y+1, x]) // 255,
                      int(skeleton[y+1, x-1]) // 255,
                      int(skeleton[y, x-1]) // 255,
                      int(skeleton[y-1, x-1]) // 255]
                for i in range(8):
                    if p2[i] != p2[(i + 1) % 8]:
                        angle = i * 45
                        break

            too_close = False
            for mx, my, *_ in minutiae:
                if abs(x - mx) + abs(y - my) < min_dist:
                    too_close = True
                    break
            if not too_close:
                minutiae.append((x, y, angle, mtype))

    return minutiae


# ─── Stage 7: Hough-based matching ──────────────────────────────────────────

def match_minutiae(query_min, template_min, rot_range=(-20, 20),
                   trans_range=(-15, 15), rot_step=2, trans_step=2,
                   dist_thresh=6, angle_thresh=20):
    """Hough-transform based minutiae matching.

    Votes for alignment parameters (dx, dy, dtheta) in a 3D accumulator,
    then counts paired minutiae after applying the best alignment.
    """
    if not query_min or not template_min:
        return 0, 0, 0, 0

    qpts = np.array([(x, y) for x, y, *_ in query_min], dtype=np.float32)
    qang = np.array([a for *_, a, _ in query_min], dtype=np.float32)
    tpts = np.array([(x, y) for x, y, *_ in template_min], dtype=np.float32)
    tang = np.array([a for *_, a, _ in template_min], dtype=np.float32)

    n_rot = int((rot_range[1] - rot_range[0]) / rot_step) + 1
    n_trans_x = int((trans_range[1] - trans_range[0]) / trans_step) + 1
    n_trans_y = int((trans_range[1] - trans_range[0]) / trans_step) + 1

    accumulator = np.zeros((n_rot, n_trans_x, n_trans_x), dtype=np.int32)

    def quantize(val, start, step, n):
        idx = int(round((val - start) / step))
        return max(0, min(n - 1, idx))

    for qi, (qx, qy) in enumerate(qpts):
        qa = qang[qi]
        for ti, (tx, ty) in enumerate(tpts):
            ta = tang[ti]
            dtheta = qa - ta
            dr = rot_range[0] <= dtheta <= rot_range[1]
            if not dr:
                continue

            rad = np.radians(dtheta)
            dx = qx - (tx * np.cos(rad) - ty * np.sin(rad))
            dy = qy - (tx * np.sin(rad) + ty * np.cos(rad))

            in_range = (trans_range[0] <= dx <= trans_range[1] and
                        trans_range[0] <= dy <= trans_range[1])
            if not in_range:
                continue

            ri = quantize(dtheta, rot_range[0], rot_step, n_rot)
            xi = quantize(dx, trans_range[0], trans_step, n_trans_x)
            yi = quantize(dy, trans_range[0], trans_step, n_trans_y)
            accumulator[ri, xi, yi] += 1

    if np.max(accumulator) == 0:
        return 0, 0, 0, 0

    best_idx = np.unravel_index(np.argmax(accumulator), accumulator.shape)
    best_dtheta = rot_range[0] + best_idx[0] * rot_step
    best_dx = trans_range[0] + best_idx[1] * trans_step
    best_dy = trans_range[0] + best_idx[2] * trans_step

    rad = np.radians(best_dtheta)
    ca, sa = np.cos(rad), np.sin(rad)
    q_aligned = np.column_stack([
        qpts[:, 0] * ca - qpts[:, 1] * sa,
        qpts[:, 0] * sa + qpts[:, 1] * ca
    ]) + np.array([best_dx, best_dy])

    matched = 0
    for qi in range(len(q_aligned)):
        for ti in range(len(tpts)):
            dist = np.linalg.norm(q_aligned[qi] - tpts[ti])
            ang_diff = abs(qang[qi] - tang[ti])
            ang_diff = min(ang_diff, 360 - ang_diff)
            if dist < dist_thresh and ang_diff < angle_thresh:
                matched += 1
                break

    total = max(len(query_min), len(template_min))
    score = (matched * matched) / (total * total) if total > 0 else 0

    return score, matched, best_dtheta, (best_dx, best_dy)


# ─── High-level pipeline ─────────────────────────────────────────────────────

def process_raw(pgm_path: str):
    """Full pipeline: raw PGM → enhanced image → minutiae."""
    width, height, depth, pixels = tool.read_pgm(pgm_path)
    img = np.array(pixels, dtype=np.uint16).reshape(height, width)

    img = img[1:height - 1, 1:width - 1]

    img_8u = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    norm = normalize(img_8u)
    orient, coherency = orientation_field(norm, block_size=7, smooth_sigma=2.0)
    enhanced = gabor_enhance(norm, orient, coherency)
    enhanced = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8)).apply(enhanced)
    binary = binarize(enhanced)
    skeleton = skeletonize(binary)
    minutiae = extract_minutiae(skeleton, min_dist=6, border=4)

    return norm, enhanced, skeleton, minutiae


def render_minutiae(img, minutiae, path=None):
    color = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    for x, y, angle, mtype in minutiae:
        if mtype == 'ending':
            cv2.circle(color, (x, y), 2, (0, 0, 255), -1)
        else:
            cv2.circle(color, (x, y), 3, (0, 255, 0), -1)
        dx = int(8 * np.cos(np.radians(angle)))
        dy = int(8 * np.sin(np.radians(angle)))
        cv2.arrowedLine(color, (x, y), (x + dx, y + dy), (255, 0, 0), 1)
    if path:
        cv2.imwrite(path, color)
    return color
