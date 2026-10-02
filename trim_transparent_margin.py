from __future__ import annotations

import argparse
from pathlib import Path
from PIL import Image


SUPPORTED_EXTS = {".png", ".webp", ".tif", ".tiff"}


def crop_transparent_margin(
    image: Image.Image,
    alpha_threshold: int = 1,
    padding: int = 0,
) -> Image.Image:
    """
    画像の外周にある透過余白だけをトリミングする。
    内部の透過部分（穴）はそのまま残す。

    alpha_threshold:
        この値以上のアルファを「中身あり」とみなす。
        1なら、完全透明(0)だけを余白として扱う。
    padding:
        トリミング後に四辺へ戻す余白(px)。
    """
    if image.mode != "RGBA":
        image = image.convert("RGBA")

    alpha = image.getchannel("A")

    # alpha > 0 を「内容あり」にしたいので、threshold以上だけ残す
    mask = alpha.point(lambda a: 255 if a >= alpha_threshold else 0)
    bbox = mask.getbbox()

    if bbox is None:
        # 全部透明画像ならそのまま返す
        return image.copy()

    left, upper, right, lower = bbox

    if padding > 0:
        left = max(0, left - padding)
        upper = max(0, upper - padding)
        right = min(image.width, right + padding)
        lower = min(image.height, lower + padding)

    return image.crop((left, upper, right, lower))


def process_file(
    input_path: Path,
    output_path: Path,
    alpha_threshold: int = 1,
    padding: int = 0,
) -> None:
    with Image.open(input_path) as img:
        cropped = crop_transparent_margin(
            img,
            alpha_threshold=alpha_threshold,
            padding=padding,
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)

        save_kwargs = {}
        ext = output_path.suffix.lower()

        if ext == ".png":
            save_kwargs["optimize"] = True
        elif ext == ".webp":
            save_kwargs["lossless"] = True
            save_kwargs["quality"] = 100

        cropped.save(output_path, **save_kwargs)

        print(
            f"[OK] {input_path.name}: "
            f"{img.width}x{img.height} -> {cropped.width}x{cropped.height}"
        )


def iter_image_files(path: Path):
    if path.is_file():
        if path.suffix.lower() in SUPPORTED_EXTS:
            yield path
        return

    for p in path.rglob("*"):
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS:
            yield p


def main():
    parser = argparse.ArgumentParser(
        description="画像の外周にある透過余白だけをトリミングします。"
    )
    parser.add_argument(
        "input",
        help="入力画像ファイル or 入力フォルダ",
    )
    parser.add_argument(
        "output",
        help="出力画像ファイル or 出力フォルダ",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=1,
        help="アルファ閾値。これ以上を内容ありとみなす（既定: 1）",
    )
    parser.add_argument(
        "--padding",
        type=int,
        default=0,
        help="トリミング後に残す余白(px)（既定: 0）",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(f"入力パスが存在しません: {input_path}")

    # 単一ファイル処理
    if input_path.is_file():
        if output_path.exists() and output_path.is_dir():
            out_file = output_path / input_path.name
        else:
            out_file = output_path

        process_file(
            input_path,
            out_file,
            alpha_threshold=args.threshold,
            padding=args.padding,
        )
        return

    # フォルダ処理
    if input_path.is_dir():
        output_path.mkdir(parents=True, exist_ok=True)

        count = 0
        for src in iter_image_files(input_path):
            rel = src.relative_to(input_path)
            dst = output_path / rel
            process_file(
                src,
                dst,
                alpha_threshold=args.threshold,
                padding=args.padding,
            )
            count += 1

        print(f"\n完了: {count} ファイル処理しました。")
        return


if __name__ == "__main__":
    main()
