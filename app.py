import requests
import qrcode
from PIL import Image, ImageDraw, ImageFont
import os
import html

# ================= 配置区 =================
DOMAIN = "https://2159windriverln.com"
CATEGORY_ID = 10
API_URL = f"{DOMAIN}/wp-json/wp/v2/posts?categories={CATEGORY_ID}&per_page=100"

# 名片物理尺寸 (86mm x 54mm, 竖向排版, 300 DPI)
DPI = 300
WIDTH_PX = int((54 / 25.4) * DPI)  # 约 638 像素
HEIGHT_PX = int((86 / 25.4) * DPI)  # 约 1016 像素

OUTPUT_DIR = "tree_tags_balanced"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ================= 抓取与生成 =================
def fetch_tree_data():
    """从 WordPress API 抓取果树数据"""
    print(f"正在从 {DOMAIN} 获取数据...")
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(API_URL, headers=headers)
        response.raise_for_status()
        posts = response.json()

        tree_data = []
        for index, post in enumerate(posts):
            raw_title = post.get("title", {}).get("rendered", "Unknown Tree")
            clean_title = html.unescape(raw_title)
            link = post.get("link", "")
            safe_filename = "".join([c if c.isalnum() else "_" for c in clean_title])
            filename = f"{index + 1:02d}_{safe_filename}.png"

            tree_data.append(
                {
                    "filename": filename,
                    "title": clean_title,
                    "subtitle": "2159 Wind River",
                    "url": link,
                }
            )
        return tree_data
    except requests.exceptions.RequestException as e:
        print(f"抓取失败: {e}")
        return []


def generate_tags(tree_data):
    if not tree_data:
        return

    for tree in tree_data:
        # 画布
        img = Image.new("RGB", (WIDTH_PX, HEIGHT_PX), color="white")
        draw = ImageDraw.Draw(img)

        # ==========================================
        # 🌟 新增：绘制顶部打孔定位十字
        # ==========================================
        cross_center_x = WIDTH_PX // 2
        cross_center_y = 65  # 定位在离顶部 65 像素的位置 (130px留白的中心)
        cross_size = 15  # 十字的一半长度，即十字总宽高为 30px
        line_width = 3  # 十字线的粗细

        # 画横线
        draw.line(
            [
                (cross_center_x - cross_size, cross_center_y),
                (cross_center_x + cross_size, cross_center_y),
            ],
            fill="black",
            width=line_width,
        )
        # 画竖线
        draw.line(
            [
                (cross_center_x, cross_center_y - cross_size),
                (cross_center_x, cross_center_y + cross_size),
            ],
            fill="black",
            width=line_width,
        )
        # ==========================================

        # 顶部预留 130px 开始画文字
        text_y = 130

        # --- 智能自适应标题字号 ---
        title_font_size = 76
        try:
            font_title = ImageFont.truetype("msyhbd.ttc", title_font_size)
        except IOError:
            font_title = ImageFont.load_default()

        # 防止标题超宽
        title_bbox = draw.textbbox((0, 0), tree["title"], font=font_title)
        title_w = title_bbox[2] - title_bbox[0]
        while title_w > (WIDTH_PX - 60) and title_font_size > 20:
            title_font_size -= 2
            font_title = ImageFont.truetype("msyhbd.ttc", title_font_size)
            title_bbox = draw.textbbox((0, 0), tree["title"], font=font_title)
            title_w = title_bbox[2] - title_bbox[0]

        title_h = title_bbox[3] - title_bbox[1]
        draw.text(
            ((WIDTH_PX - title_w) / 2, text_y),
            tree["title"],
            font=font_title,
            fill="black",
        )

        # --- 绘制副标题 ---
        text_y += title_h + 40
        try:
            font_subtitle = ImageFont.truetype("msyhbd.ttc", 42)
        except IOError:
            font_subtitle = ImageFont.load_default()

        sub_bbox = draw.textbbox((0, 0), tree["subtitle"], font=font_subtitle)
        sub_w = sub_bbox[2] - sub_bbox[0]
        draw.text(
            ((WIDTH_PX - sub_w) / 2, text_y),
            tree["subtitle"],
            font=font_subtitle,
            fill="black",
        )

        # ==========================================
        # ⚠️ 核心修复区：二维码动态生成与强力尺寸锁定
        # ==========================================
        qr = qrcode.QRCode(
            version=None,  # 让程序根据网址长度自动调整密集度
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,  # 基础生成大小
            border=1,
        )
        qr.add_data(tree["url"])
        qr.make(fit=True)

        # 生成初始黑白图像
        qr_img = (
            qr.make_image(fill_color="black", back_color="white")
            .get_image()
            .convert("1", dither=Image.NONE)
        )

        # 强制缩放：设定二维码的绝对物理大小 (占据卡片宽度的 90%)
        target_qr_size = int(WIDTH_PX * 0.9)

        # 极其关键：必须使用 Image.NEAREST (最近邻插值)，否则缩放会让边缘变灰变糊！
        qr_img = qr_img.resize((target_qr_size, target_qr_size), resample=Image.NEAREST)

        # 计算粘贴坐标并贴图
        qr_w, qr_h = qr_img.size
        qr_x = int((WIDTH_PX - qr_w) / 2)
        qr_y = HEIGHT_PX - qr_h - 90  # 距离底部固定 90px

        img.paste(qr_img, (qr_x, qr_y))

        # 最终转为完全二值化并保存
        img_binary = img.convert("1", dither=Image.NONE)
        save_path = os.path.join(OUTPUT_DIR, tree["filename"])
        img_binary.save(save_path)
        print(f"✅ 已完美生成: {save_path}")


if __name__ == "__main__":
    trees = fetch_tree_data()
    generate_tags(trees)
    print("\n🎉 全部铭牌生成完毕！")
