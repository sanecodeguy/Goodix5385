import os
import cv2
import numpy as np
from . import tool


def read_pgm_as_cv(path: str):
    width, height, depth, pixels = tool.read_pgm(path)
    img = np.array(pixels, dtype=np.uint16).reshape(height, width)
    img_8u = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    return img_8u


def show_fingerprint(path: str, title: str = "Fingerprint"):
    win = f"Goodix5385 - {title}"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    img = read_pgm_as_cv(path)
    cv2.imshow(win, img)
    cv2.waitKey(0)
    cv2.destroyWindow(win)


class FingerprintViewer:

    def __init__(self, base_dir: str = "fingerprints/"):
        self.base_dir = base_dir
        self.clear_img = None
        self.clear_path = os.path.join(base_dir, "clear.pgm")

        if os.path.exists(self.clear_path):
            self.clear_img = read_pgm_as_cv(self.clear_path)

    def _load_finger(self, finger_idx: int, img_idx: int):
        path = os.path.join(self.base_dir, f"finger-{finger_idx}", f"{img_idx}.pgm")
        if not os.path.exists(path):
            return None
        img = read_pgm_as_cv(path)
        if self.clear_img is not None:
            img = cv2.subtract(255 - self.clear_img, img)
            img = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX)
        return img

    def compare(self, f1: int, n1: int, f2: int, n2: int):
        img1 = self._load_finger(f1, n1)
        img2 = self._load_finger(f2, n2)
        if img1 is None or img2 is None:
            return

        sift = cv2.SIFT_create()
        kp1, des1 = sift.detectAndCompute(img1, None)
        kp2, des2 = sift.detectAndCompute(img2, None)

        bf = cv2.BFMatcher()
        matches = bf.knnMatch(des1, des2, k=2)

        good = []
        for m, n in matches:
            if m.distance < 0.75 * n.distance:
                good.append(m)

        result = cv2.drawMatches(img1, kp1, img2, kp2, good, None,
                                 flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)

        result_rgb = cv2.cvtColor(result, cv2.COLOR_GRAY2RGB)

        status = f"Matches: {len(good)}/{(len(matches))}" if matches else "No matches"
        cv2.putText(result_rgb, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, (0, 255, 0), 2)

        cv2.namedWindow("Match Result", cv2.WINDOW_NORMAL)
        cv2.imshow("Match Result", result_rgb)
        cv2.waitKey(0)
        cv2.destroyWindow("Match Result")
        return len(good)


def run_gui():
    print("Fingerprint GUI Viewer")
    print("=====================")
    print("Functions:")
    print("  1. Show a fingerprint image")
    print("  2. Compare two fingerprints with SIFT matching")
    print()

    while True:
        choice = input("Choice (1=show, 2=compare, q=quit): ").strip()
        if choice == "q":
            break
        elif choice == "1":
            path = input("PGM file path: ").strip()
            if os.path.exists(path):
                show_fingerprint(path)
        elif choice == "2":
            p1 = input("Fingerprint 1 path: ").strip()
            p2 = input("Fingerprint 2 path: ").strip()
            if os.path.exists(p1) and os.path.exists(p2):
                fv = FingerprintViewer()
                fv.compare(0, 0, 0, 0)  # simplified
                print("Use FingerprintViewer class in code for comparison")
        else:
            print("Invalid choice")


if __name__ == "__main__":
    run_gui()
