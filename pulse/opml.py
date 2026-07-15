"""Import et export OPML des sources."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from sqlmodel import Session, select

from .models import Category, Source


def export_opml(session: Session) -> str:
    opml = ET.Element("opml", version="2.0")
    head = ET.SubElement(opml, "head")
    ET.SubElement(head, "title").text = "Pulse — Sources"
    body = ET.SubElement(opml, "body")

    categories = {c.id: c for c in session.exec(select(Category)).all()}
    sources = session.exec(select(Source)).all()

    grouped: dict[int | None, list[Source]] = {}
    for source in sources:
        grouped.setdefault(source.category_id, []).append(source)

    for category_id, srcs in grouped.items():
        if category_id and category_id in categories:
            name = categories[category_id].name
            parent = ET.SubElement(body, "outline", text=name, title=name)
        else:
            parent = body
        for source in srcs:
            ET.SubElement(
                parent,
                "outline",
                type="rss",
                text=source.title,
                title=source.title,
                xmlUrl=source.feed_url,
                htmlUrl=source.site_url or "",
            )

    return ET.tostring(opml, encoding="unicode", xml_declaration=True)


def import_opml(session: Session, content: str) -> int:
    """Importe les flux d'un OPML. Retourne le nombre de sources ajoutées."""
    root = ET.fromstring(content)
    body = root.find("body")
    if body is None:
        return 0

    added = 0

    def handle(node: ET.Element, category_id: int | None) -> None:
        nonlocal added
        for outline in node.findall("outline"):
            xml_url = outline.get("xmlUrl")
            if xml_url:
                existing = session.exec(
                    select(Source).where(Source.feed_url == xml_url)
                ).first()
                if existing is None:
                    session.add(
                        Source(
                            title=outline.get("text") or outline.get("title") or xml_url,
                            feed_url=xml_url,
                            site_url=outline.get("htmlUrl") or None,
                            category_id=category_id,
                        )
                    )
                    added += 1
            else:
                # Dossier = catégorie.
                name = outline.get("text") or outline.get("title")
                child_category_id = category_id
                if name:
                    category = session.exec(
                        select(Category).where(Category.name == name)
                    ).first()
                    if category is None:
                        category = Category(name=name)
                        session.add(category)
                        session.commit()
                        session.refresh(category)
                    child_category_id = category.id
                handle(outline, child_category_id)

    handle(body, None)
    session.commit()
    return added
