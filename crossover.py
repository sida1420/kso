import random
import numpy as np
from classes import Layout

class RKPosDecoder:
    def __init__(self, layout: Layout):
        self.layout = layout
        self.n_akb = len(layout.available_keybinds)
        self.idx2akb = list(layout.available_keybinds)
        self.akb2idx = {kb: idx for idx, kb in enumerate(layout.available_keybinds)}

        self.pos = {}
        for idx, key in enumerate(layout.idx2key):
            fpos = layout.keys[key].fpos
            layer = 0.0 if idx < layout.sizes[0] else 2.0 #2.0 is finetunable constant
            self.pos[idx] = (fpos.x, fpos.y, layer)

        self.free_indices = list(layout.available_keys)
        self.fbase_indices = [idx for idx in self.free_indices if idx < layout.sizes[0]]
        self.fshift_indices = [idx for idx in self.free_indices if idx >= layout.sizes[0]]

        self.universal_keybinds_set = layout.universal_keybinds_set
        self.base_keybinds_set = layout.base_keybinds_set
        self.shift_keybinds_set = layout.shift_keybinds_set
        self.counterparts = layout.counterparts

    def encode(self, ind: list, noise=0.05):
        rk = np.zeros((self.n_akb, 3))
        for idx, kb_idx in enumerate(ind):
            if kb_idx is None or kb_idx not in self.akb2idx:
                continue
            akb_idx = self.akb2idx[kb_idx]
            x, y, layer = self.pos[idx]
            rk[akb_idx][0] = x + (random.random() - 0.5) * noise
            rk[akb_idx][1] = y + (random.random() - 0.5) * noise
            rk[akb_idx][2] = layer + (random.random() - 0.5) * noise
        return rk

    def decode(self, rk: np.ndarray):
        ind = [None] * len(self.layout.idx2key)
        for idx, kb in self.layout.fixed_keys.items():
            ind[idx] = kb

        rank = []
        free = list(self.free_indices)
        fbase = list(self.fbase_indices)
        fshift = list(self.fshift_indices)
        used = set(self.layout.fixed_keys.keys())

        for akb_idx, kb_idx in enumerate(self.idx2akb):
            cx, cy, cl = rk[akb_idx]
            best_idx = None
            best_dist = float('inf')
            for k_idx in free:
                px, py, pl = self.pos[k_idx]
                dist = (cx - px)**2 + (cy - py)**2 + (cl - pl)**2
                if dist < best_dist:
                    best_dist = dist
                    best_idx = k_idx
            if best_idx is not None:
                rank.append((akb_idx, kb_idx, best_dist))

        rank.sort(key=lambda x: x[2])

        for akb_idx, kb_idx, _ in rank:
            cx, cy, cl = rk[akb_idx]
            if kb_idx in self.universal_keybinds_set:
                best_i = None
                best_idx = None
                best_dist = float('inf')
                for i, k_idx in enumerate(fbase):
                    if k_idx in used: continue
                    cp = self.counterparts.get(k_idx)
                    if cp is not None and cp in used: continue
                    px, py, pl = self.pos[k_idx]
                    dist = (cx - px)**2 + (cy - py)**2 + (cl - pl)**2
                    if best_dist > dist:
                        best_idx = k_idx
                        best_dist = dist
                        best_i = i
                if best_idx is not None:
                    cp = self.counterparts.get(best_idx)
                    ind[best_idx] = kb_idx
                    used.add(best_idx)
                    if best_i is not None:
                        fbase[best_i], fbase[-1] = fbase[-1], fbase[best_i]
                        fbase.pop()
                    if cp is not None:
                        used.add(cp)
            elif kb_idx in self.base_keybinds_set:
                best_i = None
                best_idx = None
                best_dist = float('inf')
                for i, k_idx in enumerate(fbase):
                    if k_idx in used: continue
                    px, py, pl = self.pos[k_idx]
                    dist = (cx - px)**2 + (cy - py)**2 + (cl - pl)**2
                    if best_dist > dist:
                        best_idx = k_idx
                        best_dist = dist
                        best_i = i
                if best_idx is not None:
                    ind[best_idx] = kb_idx
                    used.add(best_idx)
                    if best_i is not None:
                        fbase[best_i], fbase[-1] = fbase[-1], fbase[best_i]
                        fbase.pop()
            elif kb_idx in self.shift_keybinds_set:
                best_i = None
                best_idx = None
                best_dist = float('inf')
                for i, k_idx in enumerate(fshift):
                    if k_idx in used: continue
                    px, py, pl = self.pos[k_idx]
                    dist = (cx - px)**2 + (cy - py)**2 + (cl - pl)**2
                    if best_dist > dist:
                        best_idx = k_idx
                        best_dist = dist
                        best_i = i
                if best_idx is not None:
                    ind[best_idx] = kb_idx
                    used.add(best_idx)
                    if best_i is not None:
                        fshift[best_i], fshift[-1] = fshift[-1], fshift[best_i]
                        fshift.pop()
            else:
                best_i = None
                best_idx = None
                best_dist = float('inf')
                for i, k_idx in enumerate(free):
                    if k_idx in used: continue
                    px, py, pl = self.pos[k_idx]
                    dist = (cx - px)**2 + (cy - py)**2 + (cl - pl)**2
                    if best_dist > dist:
                        best_idx = k_idx
                        best_dist = dist
                        best_i = i
                if best_idx is not None:
                    ind[best_idx] = kb_idx
                    used.add(best_idx)
                    if best_i is not None:
                        free[best_i], free[-1] = free[-1], free[best_i]
                        free.pop()
        return ind

def uniform_crossover_3d(p1, p2):
    mask = np.random.rand(len(p1)) < 0.5
    return np.where(mask[:, None], p1, p2).copy()

if __name__=="__main__":
    l=Layout()
    decoder=RKPosDecoder(l)
    import init
    p1=init.random_init(l)
    l.display(p1,name='p1')
    # input()
    p2=init.random_init(l)
    l.display(p2,name='p2')
    # input()
    c=decoder.decode(uniform_crossover_3d(decoder.encode(p1),decoder.encode(p2)))
    l.display(c,name='c')

