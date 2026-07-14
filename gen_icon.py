"""生成 OBS多视角切换器 应用图标 (操纵杆风格)
参考 OBS 风扇的多视角感, 用操纵杆表示控制元素
"""
from PIL import Image, ImageDraw, ImageFilter
import os

def create_icon(size=256):
    """生成操纵杆风格图标"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 圆角矩形背景 (深色, 类似OBS的深色调)
    margin = size // 16
    bg_radius = size // 8
    bg_box = [margin, margin, size - margin, size - margin]
    # 使用渐变深色背景
    draw.rounded_rectangle(bg_box, radius=bg_radius, fill=(30, 30, 40, 255))

    cx, cy = size // 2, size // 2

    # 多视角扇形 (参考OBS风扇: 3个扇形代表多视角)
    fan_radius = int(size * 0.35)
    fan_colors = [(80, 140, 220, 255), (140, 100, 200, 255), (220, 100, 140, 255)]  # 蓝/紫/红
    import math
    for i, color in enumerate(fan_colors):
        start_angle = -90 + i * 120 - 40  # 三扇形分布
        end_angle = start_angle + 80
        # 扇形 (从中心向外)
        bbox = [cx - fan_radius, cy - fan_radius, cx + fan_radius, cy + fan_radius]
        draw.pieslice(bbox, start_angle, end_angle, fill=color, outline=None)

    # 中心圆 (扇形汇合处, 深色覆盖)
    center_r = int(size * 0.12)
    draw.ellipse([cx - center_r, cy - center_r, cx + center_r, cy + center_r],
                 fill=(30, 30, 40, 255))

    # 操纵杆 (从中心向上的杆)
    stick_w = max(3, size // 40)
    stick_h = int(size * 0.28)
    stick_x1 = cx - stick_w // 2
    stick_y1 = cy - stick_h
    stick_x2 = cx + stick_w // 2
    stick_y2 = cy
    # 杆身 (渐变银色)
    draw.rectangle([stick_x1, stick_y1, stick_x2, stick_y2], fill=(180, 180, 190, 255))

    # 操纵杆顶部球 (红色, 经典操纵杆头)
    ball_r = int(size * 0.08)
    ball_cx = cx
    ball_cy = cy - stick_h
    # 球的高光渐变
    for r in range(ball_r, 0, -1):
        ratio = r / ball_r
        red = int(220 + 35 * (1 - ratio))
        green = int(60 + 40 * (1 - ratio))
        blue = int(60 + 40 * (1 - ratio))
        draw.ellipse([ball_cx - r, ball_cy - r, ball_cx + r, ball_cy + r],
                     fill=(red, green, blue, 255))
    # 高光点
    hl_r = max(2, ball_r // 3)
    hl_offset = ball_r // 3
    draw.ellipse([ball_cx - hl_offset - hl_r, ball_cy - hl_offset - hl_r,
                  ball_cx - hl_offset + hl_r, ball_cy - hl_offset + hl_r],
                 fill=(255, 200, 200, 200))

    # 底座圆 (操纵杆底座, 银色环)
    base_r = int(size * 0.18)
    draw.ellipse([cx - base_r, cy - base_r, cx + base_r, cy + base_r],
                 fill=(60, 60, 70, 255), outline=(160, 160, 170, 255), width=max(2, size // 80))

    return img

def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))
    icon_256 = create_icon(256)

    # 保存 .ico (多尺寸)
    ico_path = os.path.join(out_dir, "app_icon.ico")
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icons = [create_icon(s[0]).resize(s, Image.LANCZOS) for s in sizes]
    icon_256.save(ico_path, format="ICO", sizes=sizes, append_images=icons[1:])
    print(f"图标已生成: {ico_path}")

    # 保存 .png 预览
    png_path = os.path.join(out_dir, "app_icon.png")
    icon_256.save(png_path, format="PNG")
    print(f"预览图已生成: {png_path}")

if __name__ == "__main__":
    main()
