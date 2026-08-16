import io
import re
from datetime import date
from html import escape

from django.http import HttpResponse
from django.utils.text import slugify

from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image as PDFImage,
    KeepInFrame,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)


# =========================================================
# TEXT HELPERS
# =========================================================

def clean_pdf_text(value):
    if not value:
        return ""

    value = str(value)

    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u00a0": " ",
        "\u2022": "-",
        "\u2026": "...",
    }

    for old, new in replacements.items():
        value = value.replace(
            old,
            new,
        )

    value = re.sub(
        r"[\x00-\x08\x0b\x0c\x0e-\x1f]",
        "",
        value,
    )

    return value.strip()


def get_person_name(
    profile,
    user,
):
    profile_name = clean_pdf_text(
        getattr(
            profile,
            "full_name",
            "",
        )
    )

    if profile_name:
        return profile_name

    full_name = clean_pdf_text(
        user.get_full_name()
    )

    if full_name:
        return full_name

    return clean_pdf_text(
        user.username
    )


def get_letter_date(language):
    today = date.today()

    if language == "de":
        return today.strftime(
            "%d.%m.%Y"
        )

    months = [
        "",
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]

    return (
        f"{months[today.month]} "
        f"{today.day}, "
        f"{today.year}"
    )


def get_closing(language):
    if language == "de":
        return "Mit freundlichen Grüßen"

    return "Kind regards,"


# =========================================================
# SIGNATURE
# =========================================================

def build_uploaded_signature(letter):
    if (
        letter.signature_type != "uploaded"
        or not letter.signature_image
    ):
        return None

    try:
        letter.signature_image.open(
            "rb"
        )

        image_bytes = (
            letter.signature_image.read()
        )

        letter.signature_image.close()

        stream = io.BytesIO(
            image_bytes
        )

        image = PDFImage(
            stream
        )

        # Smaller signature so one-page layout stays clean
        max_width = 40 * mm
        max_height = 14 * mm

        original_width = float(
            image.imageWidth
        )

        original_height = float(
            image.imageHeight
        )

        if (
            original_width <= 0
            or original_height <= 0
        ):
            return None

        scale = min(
            max_width / original_width,
            max_height / original_height,
            1.0,
        )

        image.drawWidth = (
            original_width * scale
        )

        image.drawHeight = (
            original_height * scale
        )

        image._jobcopilot_stream = stream

        return image

    except Exception as exc:
        print(
            "SIGNATURE PDF ERROR:",
            repr(exc),
        )

        return None


# =========================================================
# PDF
# =========================================================

def build_cover_letter_pdf_response(
    profile,
    job,
    letter,
    user,
):
    buffer = io.BytesIO()

    # =====================================================
    # DATA
    # =====================================================

    person_name = get_person_name(
        profile,
        user,
    )

    sender_city = clean_pdf_text(
        getattr(
            profile,
            "city",
            "",
        )
    )

    sender_country = clean_pdf_text(
        getattr(
            profile,
            "country",
            "",
        )
    )

    sender_email = clean_pdf_text(
        getattr(
            user,
            "email",
            "",
        )
    )

    recipient_company = clean_pdf_text(
        getattr(
            letter,
            "recipient_company",
            "",
        )
    )

    if not recipient_company:
        recipient_company = clean_pdf_text(
            getattr(
                job,
                "company",
                "",
            )
        )

    recipient_contact = clean_pdf_text(
        getattr(
            letter,
            "recipient_contact",
            "",
        )
    )

    recipient_street = clean_pdf_text(
        getattr(
            letter,
            "recipient_street",
            "",
        )
    )

    recipient_postal_code = clean_pdf_text(
        getattr(
            letter,
            "recipient_postal_code",
            "",
        )
    )

    recipient_city = clean_pdf_text(
        getattr(
            letter,
            "recipient_city",
            "",
        )
    )

    subject = clean_pdf_text(
        letter.subject
    )

    content = clean_pdf_text(
        letter.content
    )

    signature_name = clean_pdf_text(
        letter.signature_name
    )

    if not signature_name:
        signature_name = person_name

    # =====================================================
    # PAGE
    # =====================================================

    left_margin = 20 * mm
    right_margin = 20 * mm
    top_margin = 16 * mm
    bottom_margin = 16 * mm

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,

        leftMargin=left_margin,
        rightMargin=right_margin,

        topMargin=top_margin,
        bottomMargin=bottom_margin,

        title=(
            subject
            or "Cover Letter"
        ),

        author=person_name,
    )

    # =====================================================
    # STYLES
    # =====================================================

    sender_style = ParagraphStyle(
        name="Sender",
        fontName="Helvetica",
        fontSize=8.5,
        leading=10.5,
    )

    recipient_style = ParagraphStyle(
        name="Recipient",
        fontName="Helvetica",
        fontSize=9,
        leading=11.5,
    )

    date_style = ParagraphStyle(
        name="Date",
        fontName="Helvetica",
        fontSize=8.5,
        leading=10,
        alignment=TA_RIGHT,
    )

    subject_style = ParagraphStyle(
        name="Subject",
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=12.5,
    )

    body_style = ParagraphStyle(
        name="Body",
        fontName="Helvetica",
        fontSize=9.5,
        leading=12.5,
        splitLongWords=True,
    )

    closing_style = ParagraphStyle(
        name="Closing",
        fontName="Helvetica",
        fontSize=9.5,
        leading=12,
    )

    printed_name_style = ParagraphStyle(
        name="PrintedName",
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=11.5,
    )

    typed_signature_style = ParagraphStyle(
        name="TypedSignature",
        fontName="Times-Italic",
        fontSize=16,
        leading=17,
    )

    content_elements = []

    # =====================================================
    # SENDER
    # =====================================================

    sender_lines = []

    if person_name:
        sender_lines.append(
            f"<b>{escape(person_name)}</b>"
        )

    if sender_city:
        sender_lines.append(
            escape(sender_city)
        )

    if sender_country:
        sender_lines.append(
            escape(sender_country)
        )

    if sender_email:
        sender_lines.append(
            escape(sender_email)
        )

    if sender_lines:
        content_elements.append(
            Paragraph(
                "<br/>".join(
                    sender_lines
                ),
                sender_style,
            )
        )

    content_elements.append(
        Spacer(
            1,
            7 * mm,
        )
    )

    # =====================================================
    # RECIPIENT
    # =====================================================

    recipient_lines = []

    if recipient_company:
        recipient_lines.append(
            f"<b>{escape(recipient_company)}</b>"
        )

    if recipient_contact:
        recipient_lines.append(
            escape(recipient_contact)
        )

    if recipient_street:
        recipient_lines.append(
            escape(recipient_street)
        )

    city_parts = []

    if recipient_postal_code:
        city_parts.append(
            recipient_postal_code
        )

    if recipient_city:
        city_parts.append(
            recipient_city
        )

    if city_parts:
        recipient_lines.append(
            escape(
                " ".join(
                    city_parts
                )
            )
        )

    if recipient_lines:
        content_elements.append(
            Paragraph(
                "<br/>".join(
                    recipient_lines
                ),
                recipient_style,
            )
        )

    content_elements.append(
        Spacer(
            1,
            4 * mm,
        )
    )

    # =====================================================
    # DATE
    # =====================================================

    date_text = get_letter_date(
        letter.language
    )

    if sender_city:
        date_text = (
            f"{sender_city}, "
            f"{date_text}"
        )

    content_elements.append(
        Paragraph(
            escape(
                date_text
            ),
            date_style,
        )
    )

    content_elements.append(
        Spacer(
            1,
            5 * mm,
        )
    )

    # =====================================================
    # SUBJECT
    # =====================================================

    if subject:
        content_elements.append(
            Paragraph(
                escape(
                    subject
                ),
                subject_style,
            )
        )

        content_elements.append(
            Spacer(
                1,
                4 * mm,
            )
        )

    # =====================================================
    # BODY
    # =====================================================

    if content:
        paragraphs = re.split(
            r"\n\s*\n",
            content,
        )

        for paragraph in paragraphs:
            paragraph = (
                paragraph.strip()
            )

            if not paragraph:
                continue

            safe_paragraph = (
                escape(
                    paragraph
                )
                .replace(
                    "\n",
                    "<br/>",
                )
            )

            content_elements.append(
                Paragraph(
                    safe_paragraph,
                    body_style,
                )
            )

            content_elements.append(
                Spacer(
                    1,
                    2.5 * mm,
                )
            )

    # =====================================================
    # CLOSING
    # =====================================================

    content_elements.append(
        Spacer(
            1,
            2 * mm,
        )
    )

    content_elements.append(
        Paragraph(
            escape(
                get_closing(
                    letter.language
                )
            ),
            closing_style,
        )
    )

    content_elements.append(
        Spacer(
            1,
            3 * mm,
        )
    )

    # =====================================================
    # NAME - ALWAYS VISIBLE
    # =====================================================

    if signature_name:
        content_elements.append(
            Paragraph(
                escape(
                    signature_name
                ),
                printed_name_style,
            )
        )

        content_elements.append(
            Spacer(
                1,
                2 * mm,
            )
        )

    # =====================================================
    # SIGNATURE
    # =====================================================

    uploaded_signature = (
        build_uploaded_signature(
            letter
        )
    )

    if uploaded_signature:
        content_elements.append(
            uploaded_signature
        )

    elif (
        letter.signature_type == "typed"
        and signature_name
    ):
        content_elements.append(
            Paragraph(
                escape(
                    signature_name
                ),
                typed_signature_style,
            )
        )

    # =====================================================
    # FORCE EVERYTHING INTO ONE A4 PAGE
    # =====================================================

    page_width, page_height = A4

    available_width = (
        page_width
        - left_margin
        - right_margin
    )

    available_height = (
        page_height
        - top_margin
        - bottom_margin
    )

    one_page_content = KeepInFrame(
        available_width,
        available_height,
        content_elements,
        mode="shrink",
        hAlign="LEFT",
        vAlign="TOP",
    )

    document.build(
        [
            one_page_content
        ]
    )

    pdf_bytes = (
        buffer.getvalue()
    )

    buffer.close()

    # =====================================================
    # FILE NAME
    # =====================================================

    company_slug = (
        slugify(
            recipient_company
        )
        or "company"
    )

    title_slug = (
        slugify(
            job.job_title
        )
        or "application"
    )

    language_slug = (
        letter.language
        or "de"
    )

    filename = (
        f"cover-letter-"
        f"{company_slug}-"
        f"{title_slug}-"
        f"{language_slug}.pdf"
    )

    # =====================================================
    # RESPONSE
    # =====================================================

    response = HttpResponse(
        pdf_bytes,
        content_type="application/pdf",
    )

    response[
        "Content-Disposition"
    ] = (
        f'attachment; filename="{filename}"'
    )

    return response