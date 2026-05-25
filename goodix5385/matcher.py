import os
import pickle
import cv2
import numpy as np
from . import tool


def _normalize_8u(pgm_path: str):
    width, height, depth, pixels = tool.read_pgm(pgm_path)
    img = np.array(pixels, dtype=np.uint16).reshape(height, width)
    img_8u = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    return img_8u


class FingerprintMatcher:

    def __init__(self):
        self.orb = cv2.ORB_create(nfeatures=500, scaleFactor=1.2, nlevels=8,
                                  edgeThreshold=5, firstLevel=0, WTA_K=2,
                                  scoreType=cv2.ORB_HARRIS_SCORE, patchSize=15,
                                  fastThreshold=10)
        self.bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        self.min_inliers = 22
        self.min_image_std = 20

    def extract_orb(self, img_8u):
        kp, des = self.orb.detectAndCompute(img_8u, None)
        return kp, des

    def count_inliers(self, qkp, tkp, matches):
        if len(matches) < 4:
            return 0
        src_pts = np.float32([qkp[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([tkp[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
        try:
            _, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        except cv2.error:
            return 0
        if mask is None:
            return 0
        return int(np.sum(mask))

    def best_match(self, query_8u, enrolled):
        best = {'name': None, 'inliers': 0, 'matches': 0}

        qkp, qdes = self.extract_orb(query_8u)
        print(f"  Query: {len(qkp)} ORB keypoints")

        for name, data in enrolled.items():
            orb_data = data.get('orb', (None, None))
            tkp = [cv2.KeyPoint(x, y, size, angle, response, octave, class_id)
                   for (x, y), size, angle, response, octave, class_id in orb_data[0]] if orb_data[0] else []
            tdes = orb_data[1]

            if tdes is None or qdes is None or len(tkp) < 5:
                continue

            matches = self.bf.match(qdes, tdes)
            matches = sorted(matches, key=lambda x: x.distance)[:100]
            inliers = self.count_inliers(qkp, tkp, matches)

            if inliers > best['inliers']:
                best = {'name': name, 'inliers': inliers, 'matches': len(matches)}

        return best

    def save_template(self, img_8u, kp, des, path: str):
        data = {
            'image': img_8u,
            'orb': (
                [(p.pt, p.size, p.angle, p.response, p.octave, p.class_id) for p in kp],
                des,
            ),
        }
        with open(path, 'wb') as f:
            pickle.dump(data, f)


def enroll_fingerprints(processed_dir: str, output_template: str = "templates.pkl"):
    matcher = FingerprintMatcher()
    templates = {}

    for fname in sorted(os.listdir(processed_dir)):
        if not fname.startswith("processed_") or not fname.endswith(".pgm"):
            continue
        path = os.path.join(processed_dir, fname)
        print(f"  Processing {fname}...")
        img_8u = _normalize_8u(path)
        kp, des = matcher.extract_orb(img_8u)

        if len(kp) < 30:
            print(f"    Only {len(kp)} ORB features, skipping (probably blank)")
            continue

        templates[fname] = (img_8u, kp, des)
        print(f"    {len(kp)} ORB keypoints")

    if not templates:
        print("ERROR: No valid templates found!")
        return None

    template_path = os.path.join(processed_dir, output_template)
    data = {}
    for name, (img, kp, des) in templates.items():
        data[name] = {
            'image': img,
            'orb': (
                [(p.pt, p.size, p.angle, p.response, p.octave, p.class_id) for p in kp],
                des,
            ),
        }
    with open(template_path, 'wb') as f:
        pickle.dump(data, f)
    print(f"Saved {len(templates)} templates to {template_path}")
    return template_path


def authenticate_fingerprint(query_pgm: str, template_path: str, _clear_pgm: str = None):
    matcher = FingerprintMatcher()
    query_8u = _normalize_8u(query_pgm)

    query_std = float(np.std(query_8u))
    if query_std < matcher.min_image_std:
        print(f"  Query image too flat (std={query_std:.1f} < {matcher.min_image_std}), rejecting")
        return False

    with open(template_path, 'rb') as f:
        enrolled = pickle.load(f)

    result = matcher.best_match(query_8u, enrolled)
    print(f"  Best match: {result['name']} "
          f"(inliers={result['inliers']}, matches={result['matches']})")

    if result['inliers'] >= matcher.min_inliers:
        return True

    return False
