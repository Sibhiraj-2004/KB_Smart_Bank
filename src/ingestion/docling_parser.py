import base64
import io
import os

from google import genai

from google.genai import types as genai_types

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from dotenv import load_dotenv

load_dotenv()

_genai_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))




def _generate_image_description(pil_img, caption: str = "", page_no: int = None) -> str:
    """Call Gemini Vision to generate a rich, searchable description of an image.

    Uses the new google.genai SDK (google.generativeai is deprecated).
    Falls back gracefully: Gemini fails → caption → placeholder.

    Args:
        pil_img:  PIL Image extracted by Docling.
        caption:  Original caption from the PDF document, if any.
        page_no:  Page number used in the fallback placeholder string.

    Returns:
        A concise, information-rich text description suitable for embedding.
    """
    try:
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        image_bytes = buf.getvalue()

        prompt = f"""You are analyzing an image extracted from a financial or regulatory document.

Provide a concise description (max 150 words) covering:
1. Image type (chart / table / diagram / figure / photo / logo)
2. What it shows — key data points, labels, trends, entities mentioned
3. Any numbers, percentages, or important values clearly visible
4. Relevance to financial, regulatory, or business content if applicable

Original caption from the document: "{caption}"

Be specific — this description will be used for semantic search retrieval.
Do not include phrases like "This image shows" — go straight to the content."""

        response = _genai_client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[
                genai_types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                genai_types.Part.from_text(text=prompt),
            ],
        )
        description = response.text.strip()
        if description:
            return description

    except Exception as e:
        print(f"[docling_parser] Vision description failed (page {page_no}): {e}")

    return caption.strip() or f"[Image on page {page_no}]"


def parse_document(file_path: str) -> list[dict]:
    """Parse a PDF into a flat list of typed content chunks using Docling.

    Uses direct accessors (doc.texts, doc.tables, doc.pictures) instead of
    iterate_items() — version-safe and returns ALL elements (not a subset).

    Each chunk is a dict with three keys:
      content      — text, markdown, or AI-generated image description
      content_type — one of: "text", "table", "image"
      metadata     — dict with: content_type, element_type, section,
                     page_number, source_file, image_base64, position
    """

    pipeline_options = PdfPipelineOptions(
        do_ocr=True,
        do_table_structure=True,
        generate_picture_images=True,
    )

    converter = DocumentConverter(
        allowed_formats=[InputFormat.PDF],
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        },
    )


    result = converter.convert(file_path)
    doc = result.document

    parsed_chunks: list[dict] = []
    current_section: str | None = None
    source_file = os.path.basename(file_path)

    print(f"[docling_parser] texts={len(list(doc.texts))}  "
          f"tables={len(list(doc.tables))}  "
          f"pictures={len(list(doc.pictures))}")

    def _get_prov(node):
        """Extract page number and bounding box from a Docling node."""
        prov = getattr(node, "prov", None)
        page_no = prov[0].page_no if prov else None
        position = None
        if prov and hasattr(prov[0], "bbox") and prov[0].bbox is not None:
            b = prov[0].bbox
            position = {"l": b.l, "t": b.t, "r": b.r, "b": b.b}
        return page_no, position

    def _make_metadata(content_type, element_type, page_no, position,
                       section, img_b64=None):
        return {
            "content_type": content_type,
            "element_type": element_type,
            "section":      section,
            "page_number":  page_no,
            "source_file":  source_file,
            "position":     position,
            "image_base64": img_b64,
        }
  
    for text_item in doc.texts:
        label = str(getattr(text_item, "label", "")).lower()

       
        if label in ("page_header", "page_footer"):
            continue

        page_no, position = _get_prov(text_item)
        text = getattr(text_item, "text", "").strip()

        if not text:
            continue

        if "section_header" in label or label == "title":
            current_section = text

        parsed_chunks.append({
            "content":      text,
            "content_type": "text",
            "metadata":     _make_metadata("text", label, page_no,
                                           position, current_section),
        })

   
    for table_item in doc.tables:
        page_no, position = _get_prov(table_item)
        table_text = ""

        if hasattr(table_item, "export_to_dataframe"):
            try:
                df = table_item.export_to_dataframe(doc)  
                if df is not None and not df.empty:
                    rows_text: list[str] = []
                    headers = [str(c).strip() for c in df.columns]
                    for _, row in df.iterrows():
                        pairs = [
                            f"{h}: {str(v).strip()}"
                            for h, v in zip(headers, row)
                            if str(v).strip() not in ("", "nan", "None")
                        ]
                        if pairs:
                            rows_text.append("  |  ".join(pairs))
                    table_text = "\n".join(rows_text)
            except Exception as e:
                print(f"[docling_parser] DataFrame export failed (page {page_no}): {e}")

        if not table_text and hasattr(table_item, "export_to_html"):
            try:
                import re as _re
                raw_html = table_item.export_to_html(doc)
                table_text = _re.sub(r"<[^>]+>", " ", raw_html or "")
                table_text = _re.sub(r"\s+", " ", table_text).strip()
            except Exception:
                pass

        if not table_text:
            table_text = getattr(table_item, "text", "")

        if table_text and table_text.strip():
            parsed_chunks.append({
                "content":      table_text.strip(),
                "content_type": "table",
                "metadata":     _make_metadata("table", "table", page_no,
                                               position, current_section),
            })

    for pic_item in doc.pictures:
        page_no, position = _get_prov(pic_item)
        img_b64 = None
        pil_img = None                         
        caption = getattr(pic_item, "text", "") or ""

       
        if not caption and hasattr(pic_item, "captions"):
            for cap_ref in pic_item.captions:
                cap_text = getattr(cap_ref, "text", "")
                if cap_text:
                    caption = cap_text
                    break

        try:
           
            if hasattr(pic_item, "get_image"):
                pil_img = pic_item.get_image(doc)
                if pil_img:
                    buf = io.BytesIO()
                    pil_img.save(buf, format="PNG")
                    img_b64 = base64.b64encode(buf.getvalue()).decode()

           
            if img_b64 is None and hasattr(pic_item, "image") and pic_item.image:
                pil_img = getattr(pic_item.image, "pil_image", None)
                if pil_img:
                    buf = io.BytesIO()
                    pil_img.save(buf, format="PNG")
                    img_b64 = base64.b64encode(buf.getvalue()).decode()

        except Exception:
            pass

        if img_b64 and pil_img:
            content = _generate_image_description(pil_img, caption, page_no)
            print(f"[docling_parser] Image described (page {page_no}): {content[:80]}...")
        else:
            content = caption.strip() or f"[Image on page {page_no}]"

        parsed_chunks.append({
            "content":      content,
            "content_type": "image",
            "metadata":     _make_metadata("image", "picture", page_no,
                                           position, current_section, img_b64),
        })

    print(f"[docling_parser] Total chunks produced: {len(parsed_chunks)}")
    return parsed_chunks
