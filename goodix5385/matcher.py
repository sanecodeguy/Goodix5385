"""Fingerprint enrollment and authentication using minutiae matching."""
import os
import pickle
import numpy as np
from . import fingerprint as fp


def enroll_fingerprints(processed_dir: str, output_template: str = "templates.pkl"):
    matcher = FingerprintTemplate()
    templates = {}

    for fname in sorted(os.listdir(processed_dir)):
        if not fname.startswith("raw_") or not fname.endswith(".pgm"):
            continue
        path = os.path.join(processed_dir, fname)
        print(f"  Processing {fname}...")
        enhanced, minutiae = matcher.process(path)
        if len(minutiae) < 10:
            print(f"    Only {len(minutiae)} minutiae, skipping")
            continue
        templates[fname] = {'enhanced': enhanced, 'minutiae': minutiae}
        print(f"    {len(minutiae)} minutiae")

    if not templates:
        print("ERROR: No valid templates found!")
        return None

    template_path = os.path.join(processed_dir, output_template)
    with open(template_path, 'wb') as f:
        pickle.dump(templates, f)
    print(f"Saved {len(templates)} templates to {template_path}")
    return template_path


class FingerprintTemplate:

    def process(self, pgm_path: str):
        *_, enhanced, skeleton, minutiae = fp.process_raw(pgm_path)
        return enhanced, minutiae

    def match(self, query_minutiae, template_minutiae):
        score, matched, dtheta, (dx, dy) = fp.match_minutiae(
            query_minutiae, template_minutiae,
            rot_range=(-30, 30), rot_step=2,
            trans_range=(-20, 20), trans_step=2,
            dist_thresh=6, angle_thresh=30
        )
        return score, matched, dtheta, dx, dy


def authenticate_fingerprint(query_pgm: str, template_path: str, _clear_pgm: str = None):
    matcher = FingerprintTemplate()

    query_enhanced, query_minutiae = matcher.process(query_pgm)
    if len(query_minutiae) < 5:
        print(f"  Only {len(query_minutiae)} minutiae in query, rejecting")
        return False

    print(f"  Query: {len(query_minutiae)} minutiae")

    with open(template_path, 'rb') as f:
        enrolled = pickle.load(f)

    best = {'name': None, 'score': -1, 'matched': 0, 'dtheta': 0}

    for name, data in enrolled.items():
        score, matched, dtheta, dx, dy = matcher.match(
            query_minutiae, data['minutiae'])
        if score > best['score']:
            best = {'name': name, 'score': score, 'matched': matched,
                    'dtheta': dtheta, 'dx': dx, 'dy': dy}

    min_score = 0.15
    print(f"  Best match: {best['name']} "
          f"(score={best['score']:.3f}, matched={best['matched']}, "
          f"rot={best['dtheta']:.0f}°)")

    if best['score'] >= min_score:
        return True

    return False
