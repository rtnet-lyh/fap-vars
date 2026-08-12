from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUT_DIR = Path(__file__).resolve().parent
PAGE1 = OUT_DIR / "page-1-inventory.png"
COMBINED = OUT_DIR / "preventive_inspection_solution_4pages.png"
FONT_DIR = Path("/usr/share/fonts/google-noto-cjk")
FONT_REG = str(FONT_DIR / "NotoSansCJK-Regular.ttc")
FONT_MED = str(FONT_DIR / "NotoSansCJK-Medium.ttc")
FONT_BOLD = str(FONT_DIR / "NotoSansCJK-Bold.ttc")

SCALE = 2
W, H = 1600 * SCALE, 900 * SCALE


def font(size: int, weight: str = "regular") -> ImageFont.FreeTypeFont:
    path = {
        "regular": FONT_REG,
        "medium": FONT_MED,
        "bold": FONT_BOLD,
    }[weight]
    return ImageFont.truetype(path, size * SCALE)


PALETTE = {
    "bg": "#F4F7FB",
    "ink": "#122033",
    "muted": "#65758D",
    "line": "#D4DFEA",
    "white": "#FFFFFF",
    "teal": "#117D72",
    "teal_dark": "#0B625B",
    "blue": "#0B8BCB",
    "orange": "#F59E0B",
    "red": "#EF4444",
    "green": "#22C55E",
    "purple": "#7C3AED",
    "navy": "#132238",
    "soft_teal": "#DDF8F1",
    "soft_blue": "#E5F2FF",
    "soft_orange": "#FFF3DA",
    "soft_red": "#FFE8E8",
}


def rr(draw, xy, radius, fill, outline=None, width=1):
    xy = tuple(int(v) for v in xy)
    draw.rounded_rectangle(
        xy,
        radius=radius * SCALE,
        fill=fill,
        outline=outline,
        width=width * SCALE,
    )


def line(draw, xy, fill=PALETTE["line"], width=2):
    draw.line(tuple(int(v) for v in xy), fill=fill, width=width * SCALE)


def text(draw, xy, value, size=24, fill=PALETTE["ink"], weight="regular", anchor=None):
    draw.text((xy[0] * SCALE, xy[1] * SCALE), value, font=font(size, weight), fill=fill, anchor=anchor)


def centered(draw, box, value, size=24, fill=PALETTE["ink"], weight="bold"):
    x1, y1, x2, y2 = [v * SCALE for v in box]
    f = font(size, weight)
    bbox = draw.textbbox((0, 0), value, font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((x1 + (x2 - x1 - tw) / 2, y1 + (y2 - y1 - th) / 2 - 2 * SCALE), value, font=f, fill=fill)


def wrap_lines(draw, value, max_width, size=22, weight="regular"):
    f = font(size, weight)
    lines = []
    for para in value.split("\n"):
        current = ""
        for part in para.split(" "):
            candidate = part if not current else f"{current} {part}"
            if draw.textlength(candidate, font=f) <= max_width * SCALE:
                current = candidate
                continue
            if current:
                lines.append(current)
            if draw.textlength(part, font=f) <= max_width * SCALE:
                current = part
                continue
            chunk = ""
            for ch in part:
                candidate = chunk + ch
                if draw.textlength(candidate, font=f) <= max_width * SCALE:
                    chunk = candidate
                else:
                    if chunk:
                        lines.append(chunk)
                    chunk = ch
            current = chunk
        if current:
            lines.append(current)
    return lines


def paragraph(draw, xy, value, max_width, size=22, fill=PALETTE["muted"], weight="regular", line_gap=10):
    x, y = xy
    for ln in wrap_lines(draw, value, max_width, size, weight):
        text(draw, (x, y), ln, size=size, fill=fill, weight=weight)
        y += size + line_gap
    return y


def arrow(draw, start, end, color="#44546A", width=4):
    x1, y1 = start[0] * SCALE, start[1] * SCALE
    x2, y2 = end[0] * SCALE, end[1] * SCALE
    draw.line((x1, y1, x2, y2), fill=color, width=width * SCALE)
    size = 18 * SCALE
    if x2 >= x1:
        pts = [(x2, y2), (x2 - size, y2 - size * 0.65), (x2 - size, y2 + size * 0.65)]
    else:
        pts = [(x2, y2), (x2 + size, y2 - size * 0.65), (x2 + size, y2 + size * 0.65)]
    draw.polygon(pts, fill=color)


def card(draw, xy, title, subtitle=None, title_color=PALETTE["ink"], accent=None):
    x1, y1, x2, y2 = xy
    rr(draw, (x1 * SCALE, y1 * SCALE, x2 * SCALE, y2 * SCALE), 20, PALETTE["white"], PALETTE["line"], 2)
    if accent:
        rr(draw, (x1 * SCALE, y1 * SCALE, (x1 + 8) * SCALE, y2 * SCALE), 20, accent)
    text(draw, (x1 + 26, y1 + 24), title, size=28, fill=title_color, weight="bold")
    if subtitle:
        paragraph(draw, (x1 + 26, y1 + 62), subtitle, x2 - x1 - 52, size=17, fill=PALETTE["muted"], weight="medium", line_gap=5)


def chip(draw, xy, value, fill=PALETTE["white"], outline=PALETTE["line"], txt=PALETTE["ink"], size=20, weight="bold"):
    x1, y1, x2, y2 = xy
    rr(draw, (x1 * SCALE, y1 * SCALE, x2 * SCALE, y2 * SCALE), 12, fill, outline, 2)
    centered(draw, xy, value, size=size, fill=txt, weight=weight)


def field_row(draw, x, y, label, value, required=False, highlight=False):
    rr(draw, (x * SCALE, y * SCALE, (x + 330) * SCALE, (y + 50) * SCALE), 10, "#F8FAFD", PALETTE["line"], 2)
    label_x = x + 18
    if required:
        text(draw, (label_x, y + 14), "*", size=20, fill=PALETTE["red"], weight="bold")
        label_x += 16
    text(draw, (label_x, y + 14), label, size=19, fill=PALETTE["ink"], weight="bold")
    text(draw, (x + 175, y + 14), value, size=18, fill=PALETTE["teal_dark"] if highlight else PALETTE["muted"], weight="bold")


def small_note(draw, xy, value, fill="#F8FAFD", outline=PALETTE["line"], txt=PALETTE["muted"]):
    x1, y1, x2, y2 = xy
    rr(draw, (x1 * SCALE, y1 * SCALE, x2 * SCALE, y2 * SCALE), 10, fill, outline, 2)
    centered(draw, xy, value, size=17, fill=txt, weight="bold")


def app_table(draw, x, y):
    cols = [
        ("*분야", 76, PALETTE["red"]),
        ("*플랫폼", 92, PALETTE["red"]),
        ("*대상", 98, PALETTE["red"]),
        ("제품", 82, PALETTE["muted"]),
        ("버전", 74, PALETTE["muted"]),
        ("점검계정", 102, PALETTE["muted"]),
    ]
    total_w = sum(c[1] for c in cols)
    rr(draw, (x * SCALE, y * SCALE, (x + total_w) * SCALE, (y + 120) * SCALE), 14, "#F8FAFD", PALETTE["line"], 2)
    cursor = x
    for label, w, col in cols:
        rr(draw, (cursor * SCALE, y * SCALE, (cursor + w) * SCALE, (y + 44) * SCALE), 0, "#EDF3F9")
        text(draw, (cursor + 14, y + 12), label, size=16, fill=col, weight="bold")
        line(draw, (cursor * SCALE, y * SCALE, cursor * SCALE, (y + 120) * SCALE), fill=PALETTE["line"], width=1)
        cursor += w
    line(draw, (x * SCALE, (y + 44) * SCALE, (x + total_w) * SCALE, (y + 44) * SCALE), fill=PALETTE["line"], width=1)
    values = ["서버", "LINUX", "RHEL 계열", "Rocky", "8.0", "SSH"]
    cursor = x
    for (_, w, _), value in zip(cols, values):
        centered(draw, (cursor, y + 58, cursor + w, y + 92), value, size=17, fill=PALETTE["ink"], weight="bold")
        cursor += w
    text(draw, (x + 18, y + 98), "앱은 1개 이상 필수 등록", size=14, fill=PALETTE["muted"], weight="medium")
    text(draw, (x + 265, y + 98), "점검 속성 있는 앱만 선택 가능", size=14, fill=PALETTE["teal_dark"], weight="bold")


def account_stack(draw, x, y):
    text(draw, (x, y), "점검계정 세부설정", size=20, fill=PALETTE["ink"], weight="bold")
    y += 36
    protocols = [
        ("USERNAME", "점검 계정 ID", PALETTE["teal"]),
        ("PASSWORD", "점검 계정 비밀번호", PALETTE["blue"]),
        ("SSH 상승", "become_user / become_password", PALETTE["orange"]),
    ]
    for name, desc, color in protocols:
        rr(draw, (x * SCALE, y * SCALE, (x + 310) * SCALE, (y + 46) * SCALE), 12, PALETTE["white"], PALETTE["line"], 2)
        rr(draw, ((x + 12) * SCALE, (y + 10) * SCALE, (x + 108) * SCALE, (y + 36) * SCALE), 8, color)
        centered(draw, (x + 12, y + 10, x + 108, y + 36), name, size=13, fill=PALETTE["white"], weight="bold")
        text(draw, (x + 124, y + 13), desc, size=15, fill=PALETTE["muted"], weight="bold")
        y += 50
    small_note(draw, (x, y + 3, x + 310, y + 40), "스크립트 내 계정값으로 활용", fill=PALETTE["soft_blue"], txt=PALETTE["blue"])


def bottom_step(draw, x, y, title, desc, accent):
    rr(draw, (x * SCALE, y * SCALE, (x + 285) * SCALE, (y + 76) * SCALE), 14, "#F8FAFD", PALETTE["line"], 2)
    rr(draw, (x * SCALE, y * SCALE, (x + 8) * SCALE, (y + 76) * SCALE), 14, accent)
    text(draw, (x + 24, y + 14), title, size=18, fill=PALETTE["ink"], weight="bold")
    paragraph(draw, (x + 24, y + 42), desc, 235, size=13, fill=PALETTE["muted"], weight="bold", line_gap=2)


def excel_feature(draw, x, y):
    rr(draw, (x * SCALE, y * SCALE, (x + 330) * SCALE, (y + 76) * SCALE), 14, PALETTE["soft_orange"], "#FFD991", 2)
    rr(draw, ((x + 18) * SCALE, (y - 13) * SCALE, (x + 118) * SCALE, (y + 13) * SCALE), 8, PALETTE["orange"], PALETTE["orange"], 1)
    centered(draw, (x + 18, y - 13, x + 118, y + 13), "별도 기능", size=13, fill=PALETTE["white"], weight="bold")
    text(draw, (x + 24, y + 16), "호스트 일괄 등록/수정", size=18, fill=PALETTE["ink"], weight="bold")
    text(draw, (x + 24, y + 45), "엑셀 템플릿으로 관리", size=14, fill="#B46900", weight="bold")


def render_page1():
    img = Image.new("RGB", (W, H), PALETTE["bg"])
    draw = ImageDraw.Draw(img)

    # Soft background anchors.
    draw.ellipse((2475, -40, 3005, 490), fill="#C9F4EA")
    draw.ellipse((-70, 1375, 520, 1965), fill="#FFEBCF")

    text(draw, (76, 54), "점검 대상 관리", size=48, fill=PALETTE["ink"], weight="bold")
    text(draw, (77, 122), "호스트 등록 정보와 애플리케이션 속성/계정정보가 점검 실행 매핑의 기준이 됩니다", size=24, fill=PALETTE["muted"], weight="bold")
    text(draw, (1335, 68), "PAGE 01", size=22, fill=PALETTE["teal_dark"], weight="bold")

    card(draw, (72, 210, 455, 690), "호스트 등록", "IP를 고유키로 사용하며 중복 등록을 허용하지 않습니다.", accent=PALETTE["teal"])
    field_row(draw, 105, 305, "관리명", "예: testrocky1", True)
    field_row(draw, 105, 365, "IP", "고유키 / 중복 불가", True, True)
    field_row(draw, 105, 425, "설명", "선택 입력", False)
    field_row(draw, 105, 485, "장비중요도", "상/중/하", True)
    field_row(draw, 105, 545, "인벤토리", "1개 필수", True)
    field_row(draw, 105, 605, "그룹", "0개 이상", False)

    arrow(draw, (485, 452), (555, 452))

    card(draw, (585, 210, 1048, 690), "애플리케이션 추가", "호스트마다 1개 이상의 애플리케이션을 등록해야 실행 대상이 됩니다.", accent=PALETTE["blue"])
    app_table(draw, 618, 318)
    account_stack(draw, 628, 464)

    arrow(draw, (1078, 452), (1148, 452))

    card(draw, (1175, 210, 1528, 690), "스크립트 실행 매핑", "작업 실행 단계에서 호스트의 앱 속성과 점검 스크립트 속성을 비교합니다.", accent=PALETTE["orange"])
    chip(draw, (1213, 325, 1490, 375), "호스트 IP", fill=PALETTE["soft_teal"], outline="#9CE6D9", txt=PALETTE["teal_dark"], size=18)
    chip(draw, (1213, 388, 1490, 438), "앱 속성: 분야 > 플랫폼 > 대상 > 제품 > 버전", fill=PALETTE["soft_blue"], outline="#B7D9F6", txt=PALETTE["blue"], size=16)
    chip(draw, (1213, 451, 1490, 491), "계정정보: USERNAME / PASSWORD", fill=PALETTE["soft_orange"], outline="#FFD991", txt="#B46900", size=14)
    chip(draw, (1213, 502, 1490, 542), "SSH 사용 시: 권한상승 정보", fill=PALETTE["soft_orange"], outline="#FFD991", txt="#B46900", size=14)
    text(draw, (1349, 558), "=", size=30, fill=PALETTE["muted"], weight="bold", anchor="mm")
    chip(draw, (1213, 584, 1490, 636), "실행 가능한 점검 스크립트 선택", fill=PALETTE["navy"], outline=PALETTE["navy"], txt=PALETTE["white"], size=17)
    paragraph(draw, (1218, 650), "매핑된 점검계정 정보는 스크립트의 원격 접속 계정값으로 사용됩니다.", 268, size=14, fill=PALETTE["muted"], weight="bold", line_gap=3)

    card(draw, (72, 710, 1528, 862), "등록 후 활용 흐름", accent=PALETTE["purple"])
    bottom_step(draw, 112, 780, "인벤토리 > 그룹 > 호스트", "호스트는 인벤토리 1개 필수, 그룹 0..N", PALETTE["teal"])
    arrow(draw, (405, 818), (442, 818), color="#7A8797", width=3)
    bottom_step(draw, 462, 780, "호스트 + 앱 정보 저장", "IP 중복 차단, 앱 1개 이상 검증", PALETTE["blue"])
    arrow(draw, (755, 818), (792, 818), color="#7A8797", width=3)
    bottom_step(draw, 812, 780, "실행 매핑 데이터", "선택 가능한 점검대상과 스크립트 연결", PALETTE["purple"])
    line(draw, (1128 * SCALE, 764 * SCALE, 1128 * SCALE, 844 * SCALE), fill=PALETTE["line"], width=2)
    excel_feature(draw, 1160, 780)

    return img.resize((1600, 900), Image.Resampling.LANCZOS)


def rebuild_combined():
    pages = [Image.open(OUT_DIR / f"page-{idx}-{name}.png").convert("RGB") for idx, name in [
        (1, "inventory"),
        (2, "script-mapping"),
        (3, "execution-profile"),
        (4, "results-dashboard"),
    ]]
    gap = 36
    combined = Image.new("RGB", (1600, 900 * 4 + gap * 3), PALETTE["bg"])
    y = 0
    for page in pages:
        combined.paste(page, (0, y))
        y += 900 + gap
    combined.save(COMBINED, quality=95)


if __name__ == "__main__":
    render_page1().save(PAGE1, quality=95)
    rebuild_combined()
