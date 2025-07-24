import os
import logging
from typing import List

import firebase_admin
from firebase_admin import credentials, firestore

from format_types import FormatType
from prompts_engine import PromptsEngine
from formats_generation_engine import FormatsGenerationEngine


def get_supported_format_types() -> List[FormatType]:
    """Return every format supported by prompts_engine / API."""
    return [
        FormatType.X,
        FormatType.LINKEDIN,
        FormatType.INSTAGRAM,
        FormatType.FACEBOOK,
        
        FormatType.SONG,
        FormatType.POEM,
        FormatType.REEL,
        
        FormatType.ARTICLE,
        FormatType.BLOG_POST,
        FormatType.PRESENTATION,
        FormatType.NEWSLETTER,
        FormatType.PODCAST,
        FormatType.LETTER,
        
        FormatType.INSIGHTS,
        FormatType.REFLECTION,
        FormatType.GROWTH_SUMMARY,
        FormatType.JOURNAL_ENTRY,
    ]


def main():
    logging.basicConfig(level=logging.INFO)

    # Initialise Firebase
    cred_path = os.getenv("FIREBASE_CREDENTIALS", "firebase-credentials.json")
    if not firebase_admin._apps:  # type: ignore
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    db = firestore.client()

    prompts_engine = PromptsEngine()
    formats_engine = FormatsGenerationEngine(db=db)
    # Dynamically inject prompts_engine (used internally)
    formats_engine.prompts_engine = prompts_engine  # type: ignore

    supported_formats = get_supported_format_types()

    stories_ref = db.collection("stories")
    stories = list(stories_ref.stream())
    logging.info("Found %s stories", len(stories))

    for story_doc in stories:
        story_data = story_doc.to_dict()
        story_id = story_doc.id
        story_content = story_data.get("content", "")
        if not story_content:
            logging.warning("Story %s has no content, skipping", story_id)
            continue

        existing_formats = story_data.get("formats", {})

        def needs_generation(fmt):
            if fmt.value not in existing_formats:
                return True
            data = existing_formats[fmt.value]
            # Regenerate if the stored value is an error object or wraps one
            if isinstance(data, dict):
                if not data.get("success", True):
                    return True
                if isinstance(data.get("content"), dict) and not data["content"].get("success", True):
                    return True
            return False

        formats_to_create = [fmt for fmt in supported_formats if needs_generation(fmt)]
        if not formats_to_create:
            logging.info("Story %s already has all formats", story_id)
            continue

        logging.info(
            "Generating %s missing formats for story %s (title=%s)",
            len(formats_to_create),
            story_id,
            story_data.get("title", "Untitled"),
        )

        for fmt in formats_to_create:
            try:
                result = formats_engine.generate_format(
                    story_content=story_content,
                    format_type=fmt,
                )
                if result.get("success"):
                    content = result["content"]
                    # Preserve dict structure for SONG to keep title field etc.
                    if fmt == FormatType.SONG:
                        existing_formats[fmt.value] = {
                            "content": content,
                            "title": result.get("title", "Generated Song"),
                            "created_at": firestore.SERVER_TIMESTAMP,
                        }
                    else:
                        existing_formats[fmt.value] = content
                    logging.info("✓ %s generated for story %s", fmt.value, story_id)
                else:
                    logging.error(
                        "✗ Failed to generate %s for story %s: %s",
                        fmt.value,
                        story_id,
                        result.get("error"),
                    )
            except Exception as e:
                logging.exception("Error generating %s for story %s: %s", fmt.value, story_id, e)

        # Update Firestore document
        created_formats_list = list(existing_formats.keys())
        story_doc.reference.update(
            {
                "formats": existing_formats,
                "createdFormats": created_formats_list,
                "updated_at": firestore.SERVER_TIMESTAMP,
            }
        )

    logging.info("Bulk generation completed ✅")


if __name__ == "__main__":
    main() 