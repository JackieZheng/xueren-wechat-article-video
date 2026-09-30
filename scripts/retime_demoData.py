#!/usr/bin/env python3
"""用新 srt 时间轴更新 demoData.ts（captions/scenes/items/sfx/chapters 全部重新映射）。

适用场景：修改口播稿（加标点/改数字）后重新生成配音，srt 时间轴微变时，
无需手工重写 demoData，自动按"最近字幕"映射所有时间。

用法：python3 retime_demoData.py <旧srt> <新srt> <旧demoData.ts> <新demoData.ts>
"""
import re, sys

def parse_srt(path):
    txt = open(path, encoding="utf-8").read()
    blocks = re.split(r"\n\s*\n", txt.strip())
    cues = []
    for b in blocks:
        lines = b.strip().splitlines()
        if len(lines) >= 2 and "-->" in lines[1]:
            m = re.match(r"(\d+):(\d+):(\d+),(\d+) --> (\d+):(\d+):(\d+),(\d+)", lines[1])
            if m:
                def ts(a, b, c, d):
                    return int(a)*3600 + int(b)*60 + int(c) + int(d)/1000
                cues.append((ts(*m.groups()[:4]), ts(*m.groups()[4:])))
    return cues

def nearest_idx(times, t):
    best, bd = 0, 1e9
    for i, (s, e) in enumerate(times):
        d = abs(s - t)
        if d < bd:
            bd, best = d, i
    return best

def main():
    old_srt, new_srt, old_demo, new_demo = sys.argv[1:5]
    old_t = parse_srt(old_srt)
    new_t = parse_srt(new_srt)
    print(f"旧 srt {len(old_t)} 条, 新 srt {len(new_t)} 条")
    if len(old_t) != len(new_t):
        raise SystemExit(f"条数不一致 {len(old_t)} vs {len(new_t)}")

    src = open(old_demo, encoding="utf-8").read()

    # ---- 1) 场景块处理（scenes 数组内）----
    scenes_part = src.split("scenes: [", 1)[1].split("],\n  captions:", 1)[0]
    blocks = re.split(r"(?=\n    \{\n      kind:)", scenes_part)
    new_blocks = []
    for blk in blocks:
        m = re.search(r"start: ([\d.]+)", blk)
        if m:
            old_s = float(m.group(1))
            idx = nearest_idx(old_t, old_s)
            new_s = new_t[idx][0]
            blk = blk.replace(f"start: {old_s}", f"start: {new_s:.3f}", 1)
            def repl(mm):
                abs_t = old_s + float(mm.group(2))
                i2 = nearest_idx(old_t, abs_t)
                return f"{mm.group(1)}{new_t[i2][0] - new_s:.3f}"
            blk = re.sub(r"(appearAt: )([\d.]+)", repl, blk)
            print(f"  场景 {old_s} -> {new_s:.3f} (字幕#{idx+1})")
        new_blocks.append(blk)
    src = src.replace(scenes_part, "".join(new_blocks), 1)

    # ---- 2) captions：按顺序替换 ----
    cap_pat = re.compile(r"(\{start: )([\d.]+)(, end: )([\d.]+)(, parts:)")
    def cap_repl(m):
        i = cap_repl.count
        cap_repl.count += 1
        s, e = new_t[i]
        return f"{m.group(1)}{s:.3f}{m.group(3)}{e:.3f}{m.group(5)}"
    cap_repl.count = 0
    src = cap_pat.sub(cap_repl, src)

    # ---- 3) chapters ----
    chap_pat = re.compile(r"(\{label: \"[^\"]+\", start: )([\d.]+)(\})")
    def chap_repl(m):
        idx = nearest_idx(old_t, float(m.group(2)))
        return f"{m.group(1)}{new_t[idx][0]:.3f}{m.group(3)}"
    src = chap_pat.sub(chap_repl, src)

    # ---- 4) durationSeconds ----
    src = re.sub(r"durationSeconds: [\d.]+", f"durationSeconds: {new_t[-1][1] + 1:.2f}", src, count=1)

    # ---- 5) sfxCues ----
    sfx_pat = re.compile(r"(\{id: \"s\d+\", start: )([\d.]+)(, duration:)")
    def sfx_repl(m):
        idx = nearest_idx(old_t, float(m.group(2)))
        return f"{m.group(1)}{new_t[idx][0] - 0.05:.3f}{m.group(3)}"
    src = sfx_pat.sub(sfx_repl, src)

    open(new_demo, "w", encoding="utf-8").write(src)
    print(f"✓ 已写出 {new_demo}")

if __name__ == "__main__":
    main()
