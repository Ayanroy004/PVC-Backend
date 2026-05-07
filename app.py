from flask import Flask, request, send_file, jsonify
from flask_cors import CORS

import fitz
import cv2
import numpy as np
import base64
import uuid

from io import BytesIO

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

app = Flask(__name__)

CORS(app)

# =========================
# LIMIT
# =========================
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

# =========================
# MEMORY STORAGE
# =========================
TEMP_DATA = {}

# =========================
# UTIL
# =========================
def mm_to_pt(mm):
    return mm * 2.83465

# =========================
# GRADIENT
# =========================
def create_gradient(w, h):

    gradient = np.zeros((h, w, 3), dtype=np.uint8)

    colors = [
        (214,154,110),
        (250,232,207),
        (249,249,244),
        (161,204,166)
    ]

    sections = len(colors) - 1

    section_h = h // sections

    for i in range(sections):

        c1 = np.array(colors[i])

        c2 = np.array(colors[i + 1])

        for y in range(section_h):

            ratio = y / section_h

            color = (1 - ratio) * c1 + ratio * c2

            gradient[i * section_h + y, :] = color

    return gradient

def apply_gradient_background(img):

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    _, mask = cv2.threshold(
        gray,
        240,
        255,
        cv2.THRESH_BINARY_INV
    )

    h, w = img.shape[:2]

    gradient = create_gradient(w, h)

    mask_inv = cv2.bitwise_not(mask)

    bg = cv2.bitwise_and(
        gradient,
        gradient,
        mask=mask_inv
    )

    fg = cv2.bitwise_and(
        img,
        img,
        mask=mask
    )

    final = cv2.add(bg, fg)

    return final

# =========================
# STYLING
# =========================
def apply_styling(img, ui_radius, ui_border):

    img = cv2.resize(
        img,
        (1000, 630),
        interpolation=cv2.INTER_LANCZOS4
    )

    h, w = img.shape[:2]

    scale_factor = 1000 / 350

    r = int(ui_radius * scale_factor)

    thick = int(ui_border * scale_factor)

    img_bgra = cv2.cvtColor(
        img,
        cv2.COLOR_BGR2BGRA
    )

    mask = np.zeros((h, w), dtype=np.uint8)

    cv2.rectangle(mask, (r, 0), (w - r, h), 255, -1)

    cv2.rectangle(mask, (0, r), (w, h - r), 255, -1)

    cv2.circle(mask, (r, r), r, 255, -1)

    cv2.circle(mask, (w - r, r), r, 255, -1)

    cv2.circle(mask, (r, h - r), r, 255, -1)

    cv2.circle(mask, (w - r, h - r), r, 255, -1)

    img_bgra[:, :, 3] = mask

    if thick > 0:

        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        cv2.drawContours(
            img_bgra,
            contours,
            -1,
            (0, 0, 0, 255),
            thick
        )

    return img_bgra

# =========================
# BASE64
# =========================
def img_to_base64(img):

    _, buffer = cv2.imencode(".png", img)

    return base64.b64encode(buffer).decode("utf-8")

# =========================
# INIT
# =========================
@app.route("/init", methods=["POST"])
def init():

    try:

        if "file" not in request.files:

            return jsonify({
                "error": "No file uploaded"
            }), 400

        file = request.files["file"]

        card_type = request.form.get(
            "type",
            "aadhaar"
        )

        session_id = str(uuid.uuid4())

        pdf_bytes = file.read()

        doc = fitz.open(
            stream=pdf_bytes,
            filetype="pdf"
        )

        pix = doc[0].get_pixmap(
            matrix=fitz.Matrix(3, 3)
        )

        img = cv2.imdecode(
            np.frombuffer(
                pix.tobytes(),
                np.uint8
            ),
            cv2.IMREAD_COLOR
        )

        if img is None:

            return jsonify({
                "error": "Invalid PDF"
            }), 400

        # =========================
        # COORDS
        # =========================

        if card_type == "voter":

            front_coords = (
                97,
                284,
                832,
                748
            )

            back_coords = (
                981,
                284,
                1714,
                748
            )

        else:

            front_coords = (
                146,
                1724,
                904,
                2204
            )

            back_coords = (
                935,
                1724,
                1693,
                2204
            )

        fx1, fy1, fx2, fy2 = front_coords

        bx1, by1, bx2, by2 = back_coords

        front = img[fy1:fy2, fx1:fx2]

        back = img[by1:by2, bx1:bx2]

        TEMP_DATA[session_id] = {
            "front": front,
            "back": back
        }

        return jsonify({

            "session_id": session_id,

            "front": img_to_base64(front),

            "back": img_to_base64(back)
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

# =========================
# GENERATE
# =========================
@app.route("/generate", methods=["POST"])
def generate():

    try:

        data = request.json

        session_id = data.get("session_id")

        if session_id not in TEMP_DATA:

            return jsonify({
                "error": "Session expired"
            }), 400

        radius = data["radius"]

        border = data["border"]

        card_type = data.get(
            "type",
            "normal"
        )

        front = TEMP_DATA[session_id]["front"]

        back = TEMP_DATA[session_id]["back"]

        if card_type == "aadhaar_pvc":

            front = apply_gradient_background(front)

            back = apply_gradient_background(back)

        front = apply_styling(
            front,
            radius,
            border
        )

        back = apply_styling(
            back,
            radius,
            border
        )

        _, front_png = cv2.imencode(".png", front)

        _, back_png = cv2.imencode(".png", back)

        front_buffer = BytesIO(
            front_png.tobytes()
        )

        back_buffer = BytesIO(
            back_png.tobytes()
        )

        pdf_buffer = BytesIO()

        c = canvas.Canvas(
            pdf_buffer,
            pagesize=A4
        )

        cw = mm_to_pt(86)

        ch = mm_to_pt(54)

        page_w, page_h = A4

        margin = 30

        start_x = (
            page_w - ((cw * 2) + margin)
        ) / 2

        y_pos = page_h - ch - 100

        ui_px_to_mm = 350 / 86

        final_radius_pt = mm_to_pt(
            radius / ui_px_to_mm
        )

        final_border_pt = border * 0.3

        def draw_card(
            canv,
            img_buffer,
            x,
            y,
            w,
            h,
            r,
            b_width
        ):

            from reportlab.lib.utils import ImageReader

            canv.saveState()

            path = canv.beginPath()

            path.roundRect(x, y, w, h, r)

            canv.clipPath(
                path,
                stroke=0,
                fill=0
            )

            canv.drawImage(
                ImageReader(img_buffer),
                x,
                y,
                width=w,
                height=h,
                mask='auto'
            )

            canv.restoreState()

            if b_width > 0:

                canv.setLineWidth(b_width)

                canv.setStrokeColorRGB(0, 0, 0)

                canv.roundRect(
                    x,
                    y,
                    w,
                    h,
                    r,
                    stroke=1,
                    fill=0
                )

        draw_card(
            c,
            front_buffer,
            start_x,
            y_pos,
            cw,
            ch,
            final_radius_pt,
            final_border_pt
        )

        draw_card(
            c,
            back_buffer,
            start_x + cw + margin,
            y_pos,
            cw,
            ch,
            final_radius_pt,
            final_border_pt
        )

        c.save()

        pdf_buffer.seek(0)

        # =========================
        # CLEANUP
        # =========================
        TEMP_DATA.pop(
            session_id,
            None
        )

        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name="card.pdf",
            mimetype="application/pdf"
        )

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500