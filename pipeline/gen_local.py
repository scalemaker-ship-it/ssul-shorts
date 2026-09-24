#!/usr/bin/env python3
"""로컬 SDXL(RealVisXL) 이미지 배치 생성 — codex gen.sh 무료·무제한 대체.

모델을 한 번만 로드하고 joblist(out<TAB>prompt) 전체를 순차 생성한다.
출력은 1280x800 PNG (SDXL 친화 해상도로 생성 후 크롭·리사이즈).

사용:
  python pipeline/gen_local.py --joblist /tmp/joblist.nul          # NUL 구분
  python pipeline/gen_local.py --joblist jobs.tsv --sep newline    # 줄 구분
  python pipeline/gen_local.py --prompt "..." --out /abs/x.png     # 단건

MPS(Apple Silicon) 자동 사용. 실패 이미지는 건너뛰고 마지막에 FAIL 목록을 찍는다.
"""
import argparse, os, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL = os.environ.get(
    "SDXL_MODEL",
    str(ROOT / "models" / "RealVisXL_V5.0_fp16.safetensors"),
)
# SDXL 친화 landscape 해상도(생성) → 최종 크롭 목표
# 16GB MPS 메모리 압박 완화 위해 축소(1024x640, 1.6:1)
GEN_W = int(os.environ.get("SDXL_GEN_W", 1024))
GEN_H = int(os.environ.get("SDXL_GEN_H", 640))
OUT_W, OUT_H = 1280, 800

NEG = ("text, letters, words, watermark, logo, signature, caption, subtitle, "
       "lowres, blurry, deformed, bad anatomy, extra fingers, mutated hands, "
       "disfigured, ugly, cartoon, anime, illustration, 3d render, cgi, painting")

# 채널 공통 꼬리(실사)
STYLE_TAIL = ("photorealistic, DSLR photo, 35mm, natural light, "
              "shallow depth of field, high detail, Korean")


def parse_jobs(path, sep):
    raw = Path(path).read_bytes()
    if sep == "nul":
        chunks = raw.split(b"\0")
    else:
        chunks = raw.split(b"\n")
    jobs = []
    for c in chunks:
        s = c.decode("utf-8", "ignore").strip()
        if not s or "\t" not in s:
            continue
        out, prompt = s.split("\t", 1)
        jobs.append((out.strip(), prompt.strip()))
    return jobs


def to_out(img):
    from PIL import Image
    # 생성물(1216x832)을 1280x800(1.6:1)로 center-crop-fill
    tw, th = OUT_W, OUT_H
    w, h = img.size
    scale = max(tw / w, th / h)
    nw, nh = int(round(w * scale)), int(round(h * scale))
    img = img.resize((nw, nh), Image.LANCZOS)
    left = (nw - tw) // 2
    top = (nh - th) // 2
    return img.crop((left, top, left + tw, top + th))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--joblist")
    ap.add_argument("--sep", choices=["nul", "newline"], default="nul")
    ap.add_argument("--prompt")
    ap.add_argument("--out")
    ap.add_argument("--steps", type=int, default=30)
    ap.add_argument("--cfg", type=float, default=5.5)
    ap.add_argument("--fast", action="store_true",
                    help="SDXL-Lightning 8스텝(장당 ~30초). 품질 약간↓, 속도 6배↑")
    args = ap.parse_args()
    LORA = str(ROOT / "models" / "lora" / "sdxl_lightning_8step_lora.safetensors")
    if args.fast:
        args.steps, args.cfg = 8, 1.0

    if args.joblist:
        jobs = parse_jobs(args.joblist, args.sep)
    elif args.prompt and args.out:
        jobs = [(args.out, args.prompt)]
    else:
        sys.exit("--joblist 또는 (--prompt & --out) 필요")
    if not jobs:
        sys.exit("작업 없음")

    if not Path(MODEL).exists():
        sys.exit(f"모델 없음: {MODEL}")

    import torch
    from diffusers import (StableDiffusionXLPipeline, DPMSolverMultistepScheduler,
                           EulerDiscreteScheduler)

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    mode = "fast(Lightning 8step)" if args.fast else "quality(30step)"
    print(f"[gen_local] device={device} model={Path(MODEL).name} jobs={len(jobs)} mode={mode}")
    t0 = time.time()
    pipe = StableDiffusionXLPipeline.from_single_file(
        MODEL, torch_dtype=torch.float16, use_safetensors=True, add_watermarker=False,
    )
    if args.fast:
        pipe.load_lora_weights(LORA)
        pipe.fuse_lora()
        pipe.scheduler = EulerDiscreteScheduler.from_config(
            pipe.scheduler.config, timestep_spacing="trailing")
    else:
        pipe.scheduler = DPMSolverMultistepScheduler.from_config(
            pipe.scheduler.config, use_karras_sigmas=True, algorithm_type="sde-dpmsolver++")
    pipe = pipe.to(device)
    pipe.set_progress_bar_config(disable=True)
    # 16GB 메모리 절감
    try:
        pipe.enable_attention_slicing()
        pipe.enable_vae_slicing()
    except Exception:
        pass
    print(f"[gen_local] 모델 로드 {time.time()-t0:.0f}s")

    fails = []
    for i, (out, prompt) in enumerate(jobs, 1):
        p = prompt if STYLE_TAIL.split(",")[0] in prompt else f"{prompt}, {STYLE_TAIL}"
        try:
            os.makedirs(os.path.dirname(out), exist_ok=True)
            img = pipe(prompt=p, negative_prompt=NEG, width=GEN_W, height=GEN_H,
                       num_inference_steps=args.steps, guidance_scale=args.cfg).images[0]
            to_out(img).save(out)
            print(f"OK [{i}/{len(jobs)}] {out}", flush=True)
        except Exception as e:
            print(f"FAIL [{i}/{len(jobs)}] {out} :: {str(e)[:120]}", flush=True)
            fails.append(out)
        finally:
            try:
                if device == "mps":
                    torch.mps.empty_cache()
            except Exception:
                pass
    print(f"=== done OK={len(jobs)-len(fails)} FAIL={len(fails)} in {time.time()-t0:.0f}s ===")
    for f in fails:
        print("FAIL", f)


if __name__ == "__main__":
    main()
